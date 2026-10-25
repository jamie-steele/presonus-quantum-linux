#!/usr/bin/env bash
# Never install packages or run cleanup on the host.
set -Eeuo pipefail
repository=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
input=${QUANTUM_CLEANUP_INPUT:?set QUANTUM_CLEANUP_INPUT to the downloaded release directory}
evidence=${QUANTUM_CLEANUP_EVIDENCE:?set QUANTUM_CLEANUP_EVIDENCE to an evidence directory}
[[ "$input" == /* && -d "$input" && "$evidence" == /* ]] || {
    echo 'Input and evidence directories must be absolute paths.' >&2
    exit 1
}
mounts=()
if [[ -n "${QUANTUM_MIGRATION_CANDIDATE:-}" ]]; then
    [[ "$QUANTUM_MIGRATION_CANDIDATE" == /* && -d "$QUANTUM_MIGRATION_CANDIDATE" ]] || exit 1
    mounts+=(-v "$QUANTUM_MIGRATION_CANDIDATE:/candidate:ro")
fi
mkdir -p "$evidence"
for version in 22.04 24.04; do
    docker run --rm --cpus=2 --memory=3g \
        --cap-drop=NET_RAW --cap-drop=MKNOD --security-opt=no-new-privileges \
        -v "$repository:/workspace:ro" -v "$input:/input:ro" \
        "${mounts[@]}" "ubuntu:$version" bash /workspace/scripts/maintenance/test-cleanup-ubuntu.sh /input \
        2>&1 | tee "$evidence/ubuntu-$version.log"
done
