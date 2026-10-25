#!/usr/bin/env bash
# Only disposable package-test containers: no device passthrough or module loads.
set -Eeuo pipefail
[[ -f /.dockerenv || -f /run/.containerenv ]] || exit 1
bundle=${1:?extracted source bundle required}
packages=${2:?candidate DEB directory required}
kernel=${3:?packaged kernel required}
baseline=${4:-}
upstream=$(<"$bundle/VERSION")
version=$(dpkg-deb -f "$packages"/*.deb Version)
package=$(find "$packages" -maxdepth 1 -name '*.deb' -print -quit)
[[ "$version" == "$upstream-"* ]]
# Debian's tar installer legitimately refreshes initramfs. Supply the full kernel
# image/config instead of treating a header-only filesystem as a boot install.
# shellcheck disable=SC1091
source /etc/os-release
if [[ "$ID" == debian && ! -f "/boot/config-$kernel" ]]; then
    apt-get install -y --no-install-recommends "linux-image-$kernel"
fi
# Remove only the synthetic ownership fixture from the preceding cleanup test.
if dpkg-query -W unrelated-profile >/dev/null 2>&1; then
    dpkg --purge unrelated-profile
fi
# Existing lifecycle tests leave no native package installed.
if dpkg-query -W -f='${db:Status-Abbrev}' quantum-dkms 2>/dev/null | grep -q '^ii'; then
    dpkg --purge quantum-dkms
fi
# Keep a real fallback module and a stale tar/DKMS install present simultaneously.
mkdir -p /tmp/migration-fallback/inhouse
cp /workspace/driver/inhouse/*.[ch] /tmp/migration-fallback/inhouse/
cp /workspace/driver/inhouse/Kbuild /tmp/migration-fallback/Makefile
make -j2 -C "/lib/modules/$kernel/build" M=/tmp/migration-fallback modules
mkdir -p "/lib/modules/$kernel/extra"
install -m 0644 /tmp/migration-fallback/snd-quantum2626.ko "/lib/modules/$kernel/extra/"
# The source test can have left an unregistered source directory.
rm -rf "/usr/src/quantum-$upstream"
WIREPLUMBER_SERIES=0.4 bash "$bundle/install.sh" --kernel "$kernel"
cp /workspace/driver/modprobe.d/quantum2626-inhouse.conf /etc/modprobe.d/quantum2626-backend.conf
printf '\n# legacy customized profile before unpack\n' >> /usr/share/alsa/ucm2/P2626/HiFi.conf
mkdir -p /etc/modules-load.d /home/tester/.config/pipewire/pipewire.conf.d
printf '# shared policy\nsnd-quantum2626\n' > /etc/modules-load.d/migration-shared.conf
printf '# user custom rate\n' > /home/tester/.config/pipewire/pipewire.conf.d/51-quantum2626-rate.conf

# A broken replacement build must not retire the old working installation.
dpkg --unpack "$package"
test -f "/lib/modules/$kernel/extra/snd-quantum2626.ko"
grep -R -q 'legacy customized profile before unpack' /var/backups/quantum-migration/preinstall.*/files/
cp "/usr/src/quantum-$version/quantum_main.c" /tmp/quantum-main-before-failure.c
printf '\n#error deliberately_broken_migration_test\n' >> "/usr/src/quantum-$version/quantum_main.c"
if dpkg --configure quantum-dkms; then
    echo 'ERROR: deliberately broken replacement unexpectedly configured.' >&2
    exit 1
fi
dkms status -m quantum -v "$upstream" | grep -q ': installed'
test -f "/lib/modules/$kernel/extra/snd-quantum2626.ko"
cp /tmp/quantum-main-before-failure.c "/usr/src/quantum-$version/quantum_main.c"
dpkg --configure quantum-dkms
[[ -z $(dkms status -m quantum -v "$upstream") ]]
[[ ! -e "/usr/src/quantum-$upstream" ]]
[[ ! -e "/lib/modules/$kernel/extra/snd-quantum2626.ko" ]]
dkms status -m quantum -v "$version" | grep -q ': installed'
modinfo -k "$kernel" snd-quantum >/dev/null
grep -q '^blacklist snd-quantum2626$' /etc/modprobe.d/quantum2626-backend.conf
if grep -q '^blacklist snd-quantum$' /etc/modprobe.d/quantum2626-backend.conf; then exit 1; fi
grep -q 'snd-quantum2626' /etc/modules-load.d/migration-shared.conf
grep -q 'user custom rate' /home/tester/.config/pipewire/pipewire.conf.d/51-quantum2626-rate.conf
# Retry configuration and normal reinstall must both leave the target installed.
dpkg-reconfigure --frontend=noninteractive quantum-dkms
apt-get install -y --no-install-recommends --no-remove --reinstall "$package"
dkms status -m quantum -v "$version" | grep -q ': installed'

# An older published native package takes the ordinary upgrade route. Keep a
# custom conffile; migration must not replace it with the generated default.
if [[ -n "$baseline" ]]; then
    dpkg --purge quantum-dkms
    apt-get install -y --no-install-recommends --no-remove "$baseline"
    printf '\n# native custom policy retained\n' >> /etc/modprobe.d/quantum2626-backend.conf
    apt-get install -y --no-install-recommends --no-remove "$package"
    grep -q 'native custom policy retained' /etc/modprobe.d/quantum2626-backend.conf
    dkms status -m quantum -v "$version" | grep -q ': installed'
fi
# Leave the container clean for further package checks.
dpkg --purge quantum-dkms
printf 'PASS: automatic package migration, pre-unpack backup, failed-build preservation, retry, reinstall and custom configuration.\n'
