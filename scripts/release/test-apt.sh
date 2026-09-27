#!/usr/bin/env bash
# Exercise signed APT metadata in a disposable Ubuntu/Debian container.
set -Eeuo pipefail
[[ -f /.dockerenv || -f /run/.containerenv ]] || exit 1
native=${1:?native package directory required}
upgrade=${2:?upgrade package directory required}
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends apt-utils gnupg python3 ca-certificates
work=$(mktemp -d)
chmod 755 "$work"
export GNUPGHOME="$work/gnupg"
mkdir -m 700 "$GNUPGHOME"
trap 'gpgconf --kill gpg-agent' EXIT
gpg --batch --pinentry-mode loopback --passphrase '' --quick-generate-key \
    'Quantum disposable test key <test@example.invalid>' rsa2048 sign 1d
fingerprint=$(gpg --batch --with-colons --list-keys | awk -F: '$1 == "fpr" {print $10; exit}')
mkdir "$work/packages" "$work/lists" "$work/cache" "$work/downloads"
touch "$work/status"
cp "$native"/*.deb "$work/packages/"
python3 /workspace/scripts/release/apt_repository.py build "$work/packages" "$work/public" \
    --fingerprint "$fingerprint" --base-url https://example.invalid/quantum
gpgv --keyring "$work/public/quantum-archive-keyring.gpg" "$work/public/dists/experimental/InRelease"
grep -q '^Valid-Until:' "$work/public/dists/experimental/Release"
grep -q '^Acquire-By-Hash: yes' "$work/public/dists/experimental/Release"
printf 'deb [signed-by=%s] file:%s experimental main\n' \
    "$work/public/quantum-archive-keyring.gpg" "$work/public" > "$work/source.list"

apt_command() {
    local command=$1
    shift
    "$command" -o "Dir::Etc::sourcelist=$work/source.list" -o 'Dir::Etc::sourceparts=-' \
        -o "Dir::State::lists=$work/lists" -o "Dir::State::status=$work/status" \
        -o "Dir::Cache=$work/cache" "$@"
}

old_version=$(dpkg-deb -f "$native"/*.deb Version)
new_version=$(dpkg-deb -f "$upgrade"/*.deb Version)
apt_command apt-get update
apt_command apt-cache policy quantum-dkms | grep -F "Candidate: $old_version"
cd "$work/downloads"
apt_command apt-get download quantum-dkms
cmp ./*.deb "$native"/*.deb
printf 'Package: quantum-dkms\nStatus: install ok installed\nArchitecture: amd64\nVersion: %s\n\n' \
    "$old_version" > "$work/status"
cp "$upgrade"/*.deb "$work/packages/"
python3 /workspace/scripts/release/apt_repository.py build "$work/packages" "$work/next" \
    --fingerprint "$fingerprint" --base-url https://example.invalid/quantum
mv "$work/public" "$work/previous"
mv "$work/next" "$work/public"
apt_command apt-get update
apt_command apt-cache policy quantum-dkms | grep -F "Candidate: $new_version"
apt_command apt-cache policy quantum-dkms | grep -F "Installed: $old_version"

# Resolve against the real distro repositories, not only the isolated index.
# This catches unsupported dependency floors even when metadata tests pass.
install -m 0644 "$work/source.list" /etc/apt/sources.list.d/quantum-test.list
apt-get -o APT::Update::Error-Mode=any update
apt-get --simulate --no-remove install quantum-dkms
rm /etc/apt/sources.list.d/quantum-test.list

# Corrupt signed metadata: APT must reject it instead of accepting an unsigned feed.
sed -i 's/Origin: PreSonus/Origin: Tampered/' "$work/public/dists/experimental/InRelease"
if apt_command apt-get -o APT::Update::Error-Mode=any update; then
    echo 'ERROR: APT accepted tampered metadata.' >&2
    exit 1
fi
sed -i 's/^Valid-Until:.*/Valid-Until: Thu, 01 Jan 1970 00:00:01 +0000/' \
    "$work/public/dists/experimental/Release"
gpg --batch --yes --local-user "$fingerprint" --armor --clearsign \
    --output "$work/public/dists/experimental/InRelease" "$work/public/dists/experimental/Release"
if apt_command apt-get -o APT::Update::Error-Mode=any update; then
    echo 'ERROR: APT accepted expired metadata.' >&2
    exit 1
fi
echo 'PASS: signed APT update, download, dependency resolution, upgrade candidate, tamper rejection, and expiry rejection.'
