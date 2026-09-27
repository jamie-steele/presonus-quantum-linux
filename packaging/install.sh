#!/usr/bin/env bash
set -Eeuo pipefail

package_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
version=$(<"$package_dir/VERSION")
kernel=$(uname -r)
stage=''

while (($#)); do
    case "$1" in
        --stage) stage=${2:?staging directory required}; shift 2 ;;
        --kernel) kernel=${2:?kernel release required}; shift 2 ;;
        *) echo 'usage: install.sh [--stage ABSOLUTE_DIRECTORY] [--kernel RELEASE]' >&2; exit 2 ;;
    esac
done

[[ "$version" =~ ^[0-9]{8}\.rfc[0-9]+\.s[0-9]+$ ]] || exit 1
[[ "$kernel" =~ ^[a-zA-Z0-9._+-]+$ ]] || exit 1
series=$(bash "$package_dir/host-tools.sh" wireplumber)
source_dir="$stage/usr/src/quantum-$version"

if [[ -n "$stage" ]]; then
    [[ "$stage" == /* && "$stage" != / ]] || {
        echo 'Staging requires an absolute directory other than /.' >&2
        exit 1
    }
else
    [[ $EUID == 0 ]] || { echo 'Host installation requires root.' >&2; exit 1; }
    command -v dkms >/dev/null
    [[ -f "/lib/modules/$kernel/build/Makefile" ]] || {
        echo "Install matching kernel headers for $kernel first." >&2
        exit 1
    }
    bash "$package_dir/host-tools.sh" check
fi

[[ ! -e "$source_dir" ]] || {
    echo "Source already exists: $source_dir. Inspect/remove that DKMS version before reinstalling." >&2
    exit 1
}
mkdir -p -- "$source_dir"
cp -R -- "$package_dir/module/." "$source_dir/"

if [[ -z "$stage" ]]; then
    dkms add -m quantum -v "$version"
    dkms build -m quantum -v "$version" -k "$kernel"
    dkms install -m quantum -v "$version" -k "$kernel"
fi

while IFS= read -r -d '' profile; do
    relative=${profile#"$package_dir/alsa/ucm2/"}
    install -D -m 0644 "$profile" "$stage/usr/share/alsa/ucm2/$relative"
done < <(find "$package_dir/alsa/ucm2" -type f -name '*.conf' -print0)

if [[ "$series" == 0.4 ]]; then
    install -D -m 0644 "$package_dir/alsa/wireplumber/51-quantum2626.lua" \
        "$stage/usr/share/wireplumber/main.lua.d/51-quantum2626.lua"
else
    install -D -m 0644 "$package_dir/alsa/wireplumber/51-quantum2626.conf" \
        "$stage/usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf"
fi
install -D -m 0644 "$package_dir/quantum2626-backend.conf" \
    "$stage/etc/modprobe.d/quantum2626-backend.conf"

if [[ -z "$stage" ]]; then
    depmod -a "$kernel"
    bash "$package_dir/host-tools.sh" refresh "$kernel"
    echo 'Installed for the next boot. No modules or audio services were restarted.'
else
    echo "Staged files under $stage; DKMS, depmod, and initramfs were not run."
fi
