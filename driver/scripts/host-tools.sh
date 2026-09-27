#!/usr/bin/env bash
set -Eeuo pipefail

initramfs_tool() {
    local requested=${INITRAMFS_TOOL:-auto}
    local candidate

    if [[ "$requested" != auto ]]; then
        case "$requested" in
            update-initramfs|dracut|mkinitcpio) ;;
            *) echo "Unsupported initramfs tool: $requested" >&2; return 1 ;;
        esac
        command -v "$requested" >/dev/null || {
            echo "Required initramfs tool is missing: $requested" >&2
            return 1
        }
        printf '%s\n' "$requested"
        return
    fi

    for candidate in update-initramfs dracut mkinitcpio; do
        if command -v "$candidate" >/dev/null; then
            printf '%s\n' "$candidate"
            return
        fi
    done
    echo 'Install update-initramfs, dracut, or mkinitcpio before installing.' >&2
    return 1
}

wireplumber_series() {
    local version=${WIREPLUMBER_SERIES:-auto}
    if [[ "$version" == auto ]]; then
        version=$(wireplumber --version)
        if [[ "$version" =~ [[:space:]]0\.4\. ]]; then
            version=0.4
        elif [[ "$version" =~ [[:space:]]0\.[5-9]\. ]]; then
            version=0.5
        else
            echo 'Unknown WirePlumber version; set WIREPLUMBER_SERIES=0.4 or 0.5.' >&2
            return 1
        fi
    fi
    case "$version" in
        0.4|0.5) printf '%s\n' "$version" ;;
        *) echo "Unsupported WirePlumber series: $version" >&2; return 1 ;;
    esac
}

case ${1:-} in
    check)
        initramfs_tool >/dev/null
        ;;
    refresh)
        kernel=${2:?kernel release required}
        case "$(initramfs_tool)" in
            update-initramfs) update-initramfs -u -k "$kernel" ;;
            dracut) dracut --force --kver "$kernel" ;;
            mkinitcpio) mkinitcpio -P ;;
        esac
        ;;
    wireplumber)
        wireplumber_series
        ;;
    *) echo 'usage: host-tools.sh check|refresh KERNEL|wireplumber' >&2; exit 2 ;;
esac
