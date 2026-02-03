#!/bin/bash
# Interactive register probing tool for Quantum 2626
# Allows reading/writing MMIO registers via driver module parameters
# Usage: ./register_probe.sh [read|write] <offset> [value]

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if driver is loaded
if ! lsmod | grep -q snd_quantum2626; then
    echo "ERROR: Driver not loaded. Load it first:" >&2
    echo "  cd $REPO_ROOT/driver && make && sudo insmod snd-quantum2626.ko" >&2
    exit 1
fi

# Get card number
CARD=$(cat /proc/asound/cards | grep -i quantum | head -1 | awk '{print $1}' || echo "")
if [ -z "$CARD" ]; then
    echo "ERROR: Quantum card not found in /proc/asound/cards" >&2
    exit 1
fi

echo "Quantum card found: card $CARD" >&2

# Check if driver supports register access via sysfs
SYSFS_BASE="/sys/module/snd_quantum2626/parameters"
if [ ! -d "$SYSFS_BASE" ]; then
    echo "ERROR: Driver parameters not found. Driver may need register access support." >&2
    exit 1
fi

# Function to read register
read_reg() {
    local offset=$1
    local hex_offset=$(printf "0x%x" $offset)
    
    echo "Reading MMIO+$hex_offset..." >&2
    
    # Try to read via dmesg if driver logs it, or use direct method
    # For now, we'll use the driver's dump functionality
    sudo dmesg -C > /dev/null 2>&1 || true
    
    # Trigger a read by reloading with dump or using a test parameter
    # This is a placeholder - we'll need driver support
    echo "Note: Direct register read requires driver support" >&2
    echo "Current baseline values from notes/MMIO_BASELINE.md:" >&2
    grep -E "^\\| 0x$(printf "%02x" $offset)" "$REPO_ROOT/notes/MMIO_BASELINE.md" || echo "Offset not in baseline"
}

# Function to write register (requires driver support)
write_reg() {
    local offset=$1
    local value=$2
    local hex_offset=$(printf "0x%x" $offset)
    local hex_value=$(printf "0x%x" $value)
    
    echo "Writing $hex_value to MMIO+$hex_offset..." >&2
    echo "Note: Register write requires driver support" >&2
    echo "This would need to be implemented in the driver" >&2
}

# Main
case "${1:-help}" in
    read|r)
        if [ -z "$2" ]; then
            echo "Usage: $0 read <offset_hex>" >&2
            echo "Example: $0 read 0x04" >&2
            exit 1
        fi
        OFFSET=$(( $2 ))
        read_reg $OFFSET
        ;;
    write|w)
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo "Usage: $0 write <offset_hex> <value_hex>" >&2
            echo "Example: $0 write 0x10 0x12345678" >&2
            exit 1
        fi
        OFFSET=$(( $2 ))
        VALUE=$(( $3 ))
        write_reg $OFFSET $VALUE
        ;;
    scan|s)
        echo "Scanning first 256 bytes of MMIO (64 registers)..." >&2
        echo "This will capture current register values from dmesg" >&2
        sudo dmesg | grep -E "MMIO\+0x" | head -64
        ;;
    baseline|b)
        echo "Capturing current MMIO baseline..." >&2
        "$SCRIPT_DIR/capture_mmio_baseline.sh"
        ;;
    help|*)
        echo "Quantum 2626 Register Probe Tool" >&2
        echo "" >&2
        echo "Usage: $0 <command> [args...]" >&2
        echo "" >&2
        echo "Commands:" >&2
        echo "  read <offset>     - Read register at offset (hex)" >&2
        echo "  write <off> <val> - Write value to register (hex)" >&2
        echo "  scan              - Scan first 64 registers" >&2
        echo "  baseline          - Capture current MMIO baseline" >&2
        echo "" >&2
        echo "Examples:" >&2
        echo "  $0 read 0x04" >&2
        echo "  $0 write 0x10 0x12345678" >&2
        echo "  $0 scan" >&2
        ;;
esac
