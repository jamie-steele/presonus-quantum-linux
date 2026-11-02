#!/usr/bin/env bash
# Invoked by test-distro.sh after installing disposable container dependencies.
set -Eeuo pipefail
family=${1:?family required}
packages=${2:?native package directory required}
upgrade=${3:?upgrade test package directory required}
kernel=${4:?packaged kernel required}
[[ -f /.dockerenv || -f /run/.containerenv ]] || exit 1
export LC_ALL=C

rpm_checked() {
    local log
    log=$(mktemp)
    rpm "$@" 2>&1 | tee "$log"
    # rpm may return success even when a post-install scriptlet fails.
    if grep -qi 'scriptlet failed' "$log"; then
        echo 'RPM scriptlet failed despite the transaction exit status.' >&2
        return 1
    fi
    rm "$log"
}

check_installed() {
    local version=$1
    dkms status -m quantum -v "$version" -k "$kernel" | grep -q ': installed'
    modinfo -k "$kernel" snd-quantum
    test -f /usr/share/alsa/ucm2/P2626/HiFi.conf
    local series
    series=$(bash /workspace/driver/scripts/host-tools.sh wireplumber)
    if [[ "$series" == 0.4 ]]; then
        test -L /usr/share/wireplumber/main.lua.d/51-quantum2626.lua
        test ! -e /usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf
    else
        test ! -e /usr/share/wireplumber/main.lua.d/51-quantum2626.lua
        test -L /usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf
    fi
    python3 /workspace/scripts/release/validate-audio.py /usr/share/alsa
    # Minimal distro containers may exclude /usr/share/doc during unpacking.
    # Extract only the test headers from the exact package being validated.
    local test_source archive
    test_source=$(mktemp -d)
    archive=usr/share/doc/quantum-dkms/acp/source/pipewire-1.6.2.tar.gz
    case "$family" in
        ubuntu|debian)
            local package_file="$packages/quantum-dkms_${version}_amd64.deb"
            [[ -f "$package_file" ]] || package_file="$upgrade/quantum-dkms_${version}_amd64.deb"
            dpkg-deb --fsys-tarfile "$package_file" | tar -x -C "$test_source" "./$archive"
            ;;
        fedora|opensuse)
            local suffix=fc43
            [[ "$family" == fedora ]] || suffix=suse
            local package_file="$packages/quantum-dkms-${version}.$suffix.x86_64.rpm"
            [[ -f "$package_file" ]] || package_file="$upgrade/quantum-dkms-${version}.$suffix.x86_64.rpm"
            (cd "$test_source"; rpm2cpio "$package_file" | cpio -id --quiet "./$archive")
            ;;
    esac
    bash /workspace/scripts/release/test-packaged-acp.sh "$test_source/$archive"
    rm -rf "$test_source"
}

old_version=$(python3 -c 'import json,glob,sys; print(json.load(open(glob.glob(sys.argv[1]+"/native-*-manifest.json")[0]))["native_version"])' "$packages")
new_version=$(python3 -c 'import json,glob,sys; print(json.load(open(glob.glob(sys.argv[1]+"/native-*-manifest.json")[0]))["native_version"])' "$upgrade")
case "$family" in
    ubuntu|debian)
        apt-get install -y "$packages"/*.deb
        check_installed "$old_version"
        bash /workspace/scripts/release/test-wireplumber-policy.sh
        apt-get install -y --reinstall "$packages"/*.deb
        check_installed "$old_version"
        printf '\n# preserved native-package test setting\n' >> /etc/modprobe.d/quantum2626-backend.conf
        apt-get install -y "$upgrade"/*.deb
        check_installed "$new_version"
        [[ -z $(dkms status -m quantum -v "$old_version") ]]
        grep -q 'preserved native-package test' /etc/modprobe.d/quantum2626-backend.conf
        apt-get remove -y quantum-dkms
        [[ -z $(dkms status -m quantum -v "$new_version") ]]
        test -f /etc/modprobe.d/quantum2626-backend.conf
        apt-get purge -y quantum-dkms
        test ! -e /etc/modprobe.d/quantum2626-backend.conf
        ;;
    fedora|opensuse)
        suffix=fc43
        [[ "$family" == fedora ]] || suffix=suse
        # Dependencies were installed by the distro's own manager above.
        rpm_checked -ivh "$packages"/*".$suffix.x86_64.rpm"
        check_installed "$old_version"
        rpm_checked -Uvh --replacepkgs "$packages"/*".$suffix.x86_64.rpm"
        check_installed "$old_version"
        printf '\n# preserved native-package test setting\n' >> /etc/modprobe.d/quantum2626-backend.conf
        rpm_checked -Uvh "$upgrade"/*".$suffix.x86_64.rpm"
        check_installed "$new_version"
        [[ -z $(dkms status -m quantum -v "$old_version") ]]
        grep -q 'preserved native-package test' /etc/modprobe.d/quantum2626-backend.conf
        rpm_checked -e quantum-dkms
        [[ -z $(dkms status -m quantum -v "$new_version") ]]
        test ! -e /etc/modprobe.d/quantum2626-backend.conf
        ;;
esac
test ! -e /usr/share/alsa/ucm2/P2626/HiFi.conf
test ! -L /usr/share/wireplumber/main.lua.d/51-quantum2626.lua
test ! -L /usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf
test ! -e /usr/lib/quantum-dkms/spa-0.2/alsa/libspa-alsa.so
test ! -e /usr/lib/systemd/user/wireplumber.service.d/51-quantum-acp.conf
test ! -e /usr/src/quantum-"$new_version"
echo 'PASS: native install, reinstall, packaging-revision upgrade, config preservation, and removal.'
