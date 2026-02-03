#!/bin/bash
# Iterative register testing with feedback loop
# Tests hypotheses about register functions and reports results
# Usage: ./iterative_register_test.sh <test_name> <offset> <value> [description]

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NOTES="$REPO_ROOT/notes"
RESULTS="$NOTES/register_tests"

mkdir -p "$RESULTS"

# Get card number
CARD=$(cat /proc/asound/cards | grep -i quantum | head -1 | awk '{print $1}' || echo "4")

echo "=== Iterative Register Test ===" >&2
echo "Card: $CARD" >&2
echo "Results: $RESULTS" >&2
echo "" >&2

# Function to capture state
capture_state() {
    local label=$1
    local outfile="$RESULTS/${label}_$(date +%Y%m%d_%H%M%S).txt"
    
    {
        echo "=== $label ==="
        echo "Timestamp: $(date)"
        echo ""
        echo "--- MMIO from dmesg ---"
        sudo dmesg | grep -E "MMIO\+0x" | tail -64
        echo ""
        echo "--- ALSA state ---"
        cat /proc/asound/card$CARD/pcm*/sub*/status 2>/dev/null || echo "No active streams"
        echo ""
        echo "--- Recent dmesg ---"
        sudo dmesg | tail -20
    } > "$outfile"
    
    echo "State captured: $outfile" >&2
    echo "$outfile"
}

# Function to test register write
test_write() {
    local test_name=$1
    local offset=$2
    local value=$3
    local description="${4:-No description}"
    local hex_offset=$(printf "0x%x" $offset)
    local hex_value=$(printf "0x%x" $value)
    
    echo "Test: $test_name" >&2
    echo "  Offset: $hex_offset" >&2
    echo "  Value: $hex_value" >&2
    echo "  Description: $description" >&2
    echo "" >&2
    
    # Capture before state
    BEFORE=$(capture_state "before_${test_name}")
    
    # Perform write (placeholder - needs driver support)
    echo "  [Would write $hex_value to $hex_offset here]" >&2
    echo "  Note: Requires driver register write support" >&2
    
    # Wait a moment
    sleep 1
    
    # Capture after state
    AFTER=$(capture_state "after_${test_name}")
    
    # Compare
    echo "" >&2
    echo "=== Comparison ===" >&2
    echo "Before: $BEFORE" >&2
    echo "After:  $AFTER" >&2
    echo "" >&2
    
    # Try to detect changes
    if diff -q "$BEFORE" "$AFTER" > /dev/null 2>&1; then
        echo "Result: NO CHANGES DETECTED" >&2
    else
        echo "Result: CHANGES DETECTED - check files for details" >&2
        diff -u "$BEFORE" "$AFTER" | head -50 || true
    fi
    
    # Record test
    {
        echo "Test: $test_name"
        echo "Date: $(date)"
        echo "Offset: $hex_offset"
        echo "Value: $hex_value"
        echo "Description: $description"
        echo "Before: $BEFORE"
        echo "After: $AFTER"
        echo ""
    } >> "$RESULTS/test_log.txt"
}

# Function to test with audio playback
test_with_playback() {
    local test_name=$1
    local offset=$2
    local value=$3
    local description="${4:-No description}"
    
    echo "Test with playback: $test_name" >&2
    
    # Stop wireplumber if running
    systemctl --user stop wireplumber 2>/dev/null || true
    
    # Capture before
    BEFORE=$(capture_state "before_playback_${test_name}")
    
    # Start playback in background
    echo "Starting playback..." >&2
    aplay -D "plughw:$CARD,0" -r 48000 -f S16_LE -c 2 /dev/zero &
    APID=$!
    sleep 2
    
    # Perform register operation
    echo "Performing register operation..." >&2
    # [Register write would go here]
    
    sleep 2
    
    # Capture during
    DURING=$(capture_state "during_playback_${test_name}")
    
    # Stop playback
    kill $APID 2>/dev/null || true
    wait $APID 2>/dev/null || true
    sleep 1
    
    # Capture after
    AFTER=$(capture_state "after_playback_${test_name}")
    
    # Restart wireplumber
    systemctl --user start wireplumber 2>/dev/null || true
    
    echo "Results:" >&2
    echo "  Before: $BEFORE" >&2
    echo "  During: $DURING" >&2
    echo "  After:  $AFTER" >&2
}

# Main
case "${1:-help}" in
    test|t)
        if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
            echo "Usage: $0 test <name> <offset_hex> <value_hex> [description]" >&2
            exit 1
        fi
        test_write "$2" $(( $3 )) $(( $4 )) "${5:-}"
        ;;
    playback|p)
        if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
            echo "Usage: $0 playback <name> <offset_hex> <value_hex> [description]" >&2
            exit 1
        fi
        test_with_playback "$2" $(( $3 )) $(( $4 )) "${5:-}"
        ;;
    list|l)
        echo "Test results in $RESULTS:" >&2
        ls -lh "$RESULTS"/*.txt 2>/dev/null | tail -20
        ;;
    help|*)
        echo "Iterative Register Testing Tool" >&2
        echo "" >&2
        echo "Usage: $0 <command> [args...]" >&2
        echo "" >&2
        echo "Commands:" >&2
        echo "  test <name> <off> <val> [desc]  - Test register write" >&2
        echo "  playback <name> <off> <val> [desc] - Test with audio playback" >&2
        echo "  list                            - List test results" >&2
        echo "" >&2
        echo "Examples:" >&2
        echo "  $0 test enable_bit 0x10 0x1 'Test enable bit'" >&2
        echo "  $0 playback format 0x20 0x48000 'Test sample rate'" >&2
        ;;
esac
