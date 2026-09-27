#!/usr/bin/env bash
# Run only in a disposable distro container, without host devices or modules.
set -Eeuo pipefail

family=${1:?distro family required}
bundle_dir=${2:?bundle directory required}
evidence_dir=${3:?evidence directory required}
native_dir=${4:-}
upgrade_dir=${5:-}
[[ -f /.dockerenv || -f /run/.containerenv ]] || {
    echo 'This test installs packages and must run inside a disposable container.' >&2
    exit 1
}
mkdir -p "$evidence_dir"
exec > >(tee "$evidence_dir/$family.log") 2>&1

case "$family" in
    ubuntu|debian)
        export DEBIAN_FRONTEND=noninteractive
        apt-get update
        headers=linux-headers-amd64
        if [[ "$family" == ubuntu ]]; then
            headers=linux-headers-generic
        fi
        apt-get install -y --no-install-recommends build-essential dkms kmod \
            "$headers" python3 alsa-utils alsa-ucm-conf wireplumber initramfs-tools ca-certificates
        ;;
    fedora)
        dnf install -y gcc make dkms kernel-devel kernel-headers kmod python3 \
            alsa-utils alsa-ucm alsa-ucm-utils wireplumber dracut findutils diffutils tar gzip
        ;;
    opensuse)
        zypper --non-interactive refresh
        zypper --non-interactive install gcc make dkms kernel-default-devel \
            kmod python3 alsa-utils alsa-ucm-conf wireplumber dracut findutils diffutils tar gzip
        ;;
    arch)
        pacman -Syu --noconfirm --needed base-devel dkms linux-headers kmod python \
            alsa-utils alsa-ucm-conf wireplumber mkinitcpio
        ;;
    *) echo "Unknown distro family: $family" >&2; exit 2 ;;
esac

cd "$bundle_dir"
sha256sum -c SHA256SUMS
work=$(mktemp -d)
tar -xzf quantum-*.tar.gz -C "$work"
package=$(find "$work" -mindepth 1 -maxdepth 1 -type d -name 'quantum-*')
version=$(<"$package/VERSION")

kernel_build=''
if [[ "$family" == fedora ]]; then
    for candidate in /usr/src/kernels/*; do
        [[ -f "$candidate/Makefile" ]] || continue
        mkdir -p "/lib/modules/${candidate##*/}"
        ln -s "$candidate" "/lib/modules/${candidate##*/}/build"
    done
fi
for candidate in /lib/modules/*/build; do
    if [[ -f "$candidate/Makefile" ]]; then
        kernel_build=$candidate
    fi
done
[[ -n "$kernel_build" ]] || { echo 'No packaged kernel build tree found.' >&2; exit 1; }
kernel=${kernel_build%/build}
kernel=${kernel##*/}

for series in 0.4 0.5; do
    WIREPLUMBER_SERIES=$series bash "$package/install.sh" --stage "$work/stage-$series"
    cmp "$package/alsa/ucm2/P2626/HiFi.conf" \
        "$work/stage-$series/usr/share/alsa/ucm2/P2626/HiFi.conf"
    cmp "$package/quantum2626-backend.conf" \
        "$work/stage-$series/etc/modprobe.d/quantum2626-backend.conf"
done
cmp "$package/alsa/wireplumber/51-quantum2626.lua" \
    "$work/stage-0.4/usr/share/wireplumber/main.lua.d/51-quantum2626.lua"
cmp "$package/alsa/wireplumber/51-quantum2626.conf" \
    "$work/stage-0.5/usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf"
bash "$package/host-tools.sh" check
bash "$package/host-tools.sh" wireplumber

# These install only into the disposable container; no module is loaded.
cp -R "$package/module" "/usr/src/quantum-$version"
dkms add -m quantum -v "$version"
dkms build -m quantum -v "$version" -k "$kernel"
dkms install -m quantum -v "$version" -k "$kernel"
depmod -a "$kernel"
modinfo -k "$kernel" snd-quantum
dkms remove -m quantum -v "$version" --all

python3 /workspace/scripts/release/validate-audio.py "$package/alsa"
if [[ -n "$native_dir" ]]; then
    bash /workspace/scripts/release/test-native.sh "$family" "$native_dir" "$upgrade_dir" "$kernel"
fi
cat /etc/os-release
printf 'tested_kernel=%s\npackage_version=%s\n' "$kernel" "$version"
printf 'PASS: DKMS build/install/remove and staged audio policy; no hardware tested.\n'
