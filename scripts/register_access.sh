#!/bin/bash
# Direct register access via driver module parameters
# This script uses the driver's module parameters to read/write registers
# Usage: ./register_access.sh [read|write|scan] <offset> [value]

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if driver is loaded
if ! lsmod | grep -q snd_quantum2626; then
    echo "ERROR: Driver not loaded. Load it first:" >&2
    echo "  cd $REPO_ROOT/driver && make && sudo insmod snd-quantum2626.ko" >&2
    exit 1
fi

MODULE="snd_quantum2626"
PARAM_DIR="/sys/module/$MODULE/parameters"

# Function to read register
read_reg() {
    local offset=$1
    local hex_offset=$(printf "0x%x" $offset)
    
    echo "Reading MMIO+$hex_offset..." >&2
    
    # Clear dmesg to see new output
    sudo dmesg -C > /dev/null 2>&1 || true
    
    # Set parameter to trigger read
    echo $offset | sudo tee "$PARAM_DIR/reg_read_offset" > /dev/null
    
    # Wait a moment for driver to process
    sleep 0.1
    
    # Get result from dmesg
    sudo dmesg | grep -E "MMIO\+0x.*READ:" | tail -1
    
    # Clear the parameter
    echo -1 | sudo tee "$PARAM_DIR/reg_read_offset" > /dev/null
}

# Function to write register
write_reg() {
    local offset=$1
    local value=$2
    local hex_offset=$(printf "0x%x" $offset)
    local hex_value=$(printf "0x%x" $value)
    
    echo "Writing $hex_value to MMIO+$hex_offset..." >&2
    
    # Clear dmesg
    sudo dmesg -C > /dev/null 2>&1 || true
    
    # Set parameters
    echo $value | sudo tee "$PARAM_DIR/reg_write_value" > /dev/null
    echo $offset | sudo tee "$PARAM_DIR/reg_write_offset" > /dev/null
    
    # Wait for driver to process
    sleep 0.1
    
    # Get result from dmesg
    sudo dmesg | grep -E "MMIO\+0x.*WRITE:" | tail -1
    
    # Clear parameters
    echo 0 | sudo tee "$PARAM_DIR/reg_write_value" > /dev/null
    echo -1 | sudo tee "$PARAM_DIR/reg_write_offset" > /dev/null
}

# Function to scan registers
scan_regs() {
    local start=${1:-0}
    local end=${2:-255}
    local hex_start=$(printf "0x%x" $start)
    local hex_end=$(printf "0x%x" $end)
    
    echo "Scanning MMIO from $hex_start to $hex_end..." >&2
    
    # Clear dmesg
    sudo dmesg -C > /dev/null 2>&1 || true
    
    # Trigger scan
    echo 1 | sudo tee "$PARAM_DIR/reg_scan" > /dev/null
    
    # Wait
    sleep 0.2
    
    # Get results
    sudo dmesg | grep -E "MMIO\+0x" | grep -E "MMIO Scan|MMIO\+0x[0-9a-f]{2}:"
    
    # Clear
    echo 0 | sudo tee "$PARAM_DIR/reg_scan" > /dev/null
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
        START=${2:-0}
        END=${3:-255}
        scan_regs $START $END
        ;;
    help|*)
        echo "Quantum 2626 Register Access Tool" >&2
        echo "" >&2
        echo "Usage: $0 <command> [args...]" >&2
        echo "" >&2
        echo "Commands:" >&2
        echo "  read <offset>        - Read register at offset (hex)" >&2
        echo "  write <off> <val>   - Write value to register (hex)" >&2
        echo "  scan [start] [end]  - Scan registers (default 0x00-0xff)" >&2
        echo "" >&2
        echo "Examples:" >&2
        echo "  $0 read 0x04" >&2
        echo "  $0 write 0x10 0x12345678" >&2
        echo "  $0 scan" >&2
        echo "  $0 scan 0x00 0x3f  # Scan first 64 bytes" >&2
        ;;
esac
