#!/usr/bin/env bash
# Run in a disposable Ubuntu container with only read-only repository/input mounts.
set -Eeuo pipefail
[[ -f /.dockerenv || -f /run/.containerenv ]] || {
    echo 'This destructive installation test requires a disposable container.' >&2
    exit 1
}
export DEBIAN_FRONTEND=noninteractive
input=${1:?published release input directory required}
cleanup=/workspace/scripts/maintenance/cleanup-ubuntu.py
apt-get update
apt-get install -y --no-install-recommends python3 build-essential dkms kmod \
    linux-headers-generic initramfs-tools alsa-ucm-conf wireplumber ca-certificates
cd "$input"
sha256sum --ignore-missing -c SHA256SUMS
sha256sum --ignore-missing -c native-2-SHA256SUMS
kernel=''
for headers in /lib/modules/*/build/Makefile; do
    [[ -f "$headers" ]] || continue
    kernel=${headers%/build/Makefile}
    kernel=${kernel##*/}
done
[[ -n "$kernel" ]]

# Preserve unrelated configuration, unknown overrides, package-owned profiles,
# and the distro's own kernel module location throughout all removals.
mkdir -p /etc/modprobe.d /etc/modules-load.d /home/tester/.config/pipewire/pipewire.conf.d
printf 'options snd-hda-intel power_save=1\n' > /etc/modprobe.d/unrelated.conf
printf 'snd-quantum\n# custom shared file\n' > /etc/modules-load.d/custom-audio.conf
mkdir -p "/lib/modules/$kernel/kernel/sound/test" "/lib/modules/$kernel/extra"

check_preserved() {
    grep -q 'power_save=1' /etc/modprobe.d/unrelated.conf
    grep -q 'snd-quantum' /etc/modules-load.d/custom-audio.conf
    cmp /tmp/legacy/snd-quantum2626.ko "/lib/modules/$kernel/kernel/sound/test/snd-quantum.ko"
    cmp /tmp/legacy/snd-quantum2626.ko "/lib/modules/$kernel/extra/unrelated.ko"
}

check_clean() {
    [[ -z $(dkms status -m quantum) ]]
    [[ ! -e /usr/share/alsa/ucm2/P2626/HiFi.conf ]]
    [[ ! -e /etc/modprobe.d/quantum2626-backend.conf ]]
    [[ ! -e "/lib/modules/$kernel/extra/snd-quantum2626.ko" ]]
    check_preserved
    python3 "$cleanup" --apply > /tmp/cleanup-repeat.log
    grep -q 'Nothing changed' /tmp/cleanup-repeat.log
}

# Real manually installed fallback module, without loading it.
mkdir /tmp/legacy
cp /workspace/driver/snd-quantum2626.c /tmp/legacy/
printf 'obj-m := snd-quantum2626.o\n' > /tmp/legacy/Makefile
make -j2 -C "/lib/modules/$kernel/build" M=/tmp/legacy modules
install -m 0644 /tmp/legacy/snd-quantum2626.ko "/lib/modules/$kernel/extra/"
# Valid ELF sentinels avoid feeding deliberately malformed modules to depmod.
cp /tmp/legacy/snd-quantum2626.ko "/lib/modules/$kernel/kernel/sound/test/snd-quantum.ko"
cp /tmp/legacy/snd-quantum2626.ko "/lib/modules/$kernel/extra/unrelated.ko"
WIREPLUMBER_SERIES=0.4 make -C /workspace/driver install-audio DESTDIR=/tmp/legacy-stage
cp -a /tmp/legacy-stage/usr/share/alsa/ucm2/. /usr/share/alsa/ucm2/
mkdir -p /usr/share/wireplumber/main.lua.d
cp /workspace/alsa/wireplumber/51-quantum2626.lua /usr/share/wireplumber/main.lua.d/
cp /workspace/driver/modprobe.d/quantum2626-inhouse.conf /etc/modprobe.d/quantum2626-backend.conf
printf '# custom profile retained in backup\n' >> /usr/share/alsa/ucm2/P2626/HiFi.conf
python3 "$cleanup" > /tmp/cleanup-preview.log
test -f "/lib/modules/$kernel/extra/snd-quantum2626.ko"
python3 "$cleanup" --apply | tee /tmp/cleanup-legacy.log
grep -R -q 'custom profile retained' /var/backups/quantum-cleanup/
check_clean

# Real tar installer and DKMS registration/build for the packaged kernel.
mkdir /tmp/source-release
tar -xzf quantum-*.tar.gz -C /tmp/source-release
bundle=$(find /tmp/source-release -mindepth 1 -maxdepth 1 -type d -name 'quantum-*')
WIREPLUMBER_SERIES=0.4 bash "$bundle/install.sh" --kernel "$kernel"
python3 "$cleanup" --apply | tee /tmp/cleanup-tar.log
check_clean

# Real DEB lifecycle, a failed/partial configuration, and remove-with-conffiles state.
apt-get install -y --no-install-recommends ./quantum-dkms_*-2_amd64.deb
printf '# user override\n' > /home/tester/.config/pipewire/pipewire.conf.d/51-quantum2626-rate.conf
python3 "$cleanup" --apply --user-home /home/tester | tee /tmp/cleanup-native.log
[[ ! -e /home/tester/.config/pipewire/pipewire.conf.d/51-quantum2626-rate.conf ]]
check_clean

dpkg --unpack ./quantum-dkms_*-2_amd64.deb
python3 "$cleanup" --apply | tee /tmp/cleanup-partial.log
check_clean

apt-get install -y --no-install-recommends ./quantum-dkms_*-2_amd64.deb
dpkg --remove quantum-dkms
test -f /etc/modprobe.d/quantum2626-backend.conf
python3 "$cleanup" --apply | tee /tmp/cleanup-conffiles.log
check_clean

# Cleanup must also work when Ubuntu's ALSA package owns the same profile name.
mkdir -p /tmp/owner/DEBIAN /tmp/owner/usr/share/alsa/ucm2/P2626
printf 'Package: unrelated-profile\nVersion: 1\nArchitecture: all\nMaintainer: Test <test@example.invalid>\nDescription: cleanup ownership sentinel\n' > /tmp/owner/DEBIAN/control
printf 'owned elsewhere\n' > /tmp/owner/usr/share/alsa/ucm2/P2626/HiFi.conf
dpkg-deb --build /tmp/owner /tmp/owner.deb
dpkg -i /tmp/owner.deb
python3 "$cleanup" --apply | tee /tmp/cleanup-owned.log
grep -q 'owned elsewhere' /usr/share/alsa/ucm2/P2626/HiFi.conf
grep -q 'unrelated-profile' /tmp/cleanup-owned.log
check_preserved
printf 'PASS: Ubuntu cleanup: manual module, tar/DKMS, DEB, partial install, residual conffiles, backups, repeat runs and unrelated ownership.\n'
