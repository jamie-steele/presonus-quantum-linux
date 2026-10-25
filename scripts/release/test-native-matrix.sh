#!/usr/bin/env bash
# All package mutations happen in disposable containers.
set -Eeuo pipefail
repository=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
bundle=${QUANTUM_NATIVE_BUNDLE:?set QUANTUM_NATIVE_BUNDLE}
packages=${QUANTUM_NATIVE_PACKAGES:?set QUANTUM_NATIVE_PACKAGES}
upgrade=${QUANTUM_NATIVE_UPGRADE:?set QUANTUM_NATIVE_UPGRADE}
evidence=${QUANTUM_NATIVE_EVIDENCE:?set QUANTUM_NATIVE_EVIDENCE}
for directory in "$bundle" "$packages" "$upgrade"; do
    [[ "$directory" == /* && -d "$directory" ]] || exit 1
done
[[ "$evidence" == /* ]] || exit 1
mkdir -p "$evidence"
read -r -a images <<< "${QUANTUM_NATIVE_IMAGES:-ubuntu:22.04 ubuntu:24.04 debian:12 debian:13}"
for image in "${images[@]}"; do
    case "$image" in
        ubuntu:22.04|ubuntu:24.04|debian:12|debian:13) ;;
        *) echo "Unsupported test image: $image" >&2; exit 1 ;;
    esac
    family=${image%%:*}
    id=${image/:/-}
    mkdir -p "$evidence/$id"
    docker run --rm --cpus=2 --memory=3g \
        --cap-drop=NET_RAW --cap-drop=MKNOD --security-opt=no-new-privileges \
        -v "$repository:/workspace:ro" -v "$bundle:/bundle:ro" \
        -v "$packages:/native:ro" -v "$upgrade:/upgrade:ro" \
        -v "$evidence/$id:/evidence" "$image" \
        bash /workspace/scripts/release/test-distro.sh "$family" /bundle /evidence /native /upgrade \
        2>&1 | tee "$evidence/$id/console.log"
done
