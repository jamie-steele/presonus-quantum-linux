#!/usr/bin/env bash
# Local equivalent of the native workflow's build job, in a disposable container.
set -Eeuo pipefail
[[ -f /.dockerenv || -f /run/.containerenv ]] || exit 1
bundle=${1:?source bundle directory required}
output=${2:?output directory required}
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3 rpm dpkg-dev git ca-certificates file
work=$(mktemp -d)
cd "$bundle"
sha256sum -c SHA256SUMS
tar -xzf quantum-*.tar.gz -C "$work"
package=$(find "$work" -mindepth 1 -maxdepth 1 -type d -name 'quantum-*')
git config --global --add safe.directory /workspace
revision=$(cat /workspace/packaging/native/revision)
python3 /workspace/scripts/release/build_native.py "$package" "$output/native"
python3 /workspace/scripts/release/build_native.py "$package" "$output/upgrade" --revision "$((revision + 1))"
