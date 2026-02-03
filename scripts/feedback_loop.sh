#!/bin/bash
# Feedback loop for iterative register discovery
# Tests hypotheses and provides structured feedback
# Usage: ./feedback_loop.sh <hypothesis_file> or interactive mode

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NOTES="$REPO_ROOT/notes"
RESULTS="$NOTES/feedback_loop"

mkdir -p "$RESULTS"

# Source register access script
REG_ACCESS="$SCRIPT_DIR/register_access.sh"

echo "=== Register Discovery Feedback Loop ===" >&2
echo "Results directory: $RESULTS" >&2
echo "" >&2

# Function to test a hypothesis
test_hypothesis() {
    local name=$1
    local offset=$2
    local operation=$3  # read, write, or test
    local value=${4:-0}
    local description=${5:-"No description"}
    
    local hex_offset=$(printf "0x%x" $offset)
    local hex_value=$(printf "0x%x" $value)
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local result_file="$RESULTS/${name}_${timestamp}.txt"
    
    echo "=== Testing: $name ===" >&2
    echo "  Offset: $hex_offset" >&2
    echo "  Operation: $operation" >&2
    [ "$operation" = "write" ] && echo "  Value: $hex_value" >&2
    echo "  Description: $description" >&2
    echo "" >&2
    
    {
        echo "Hypothesis: $name"
        echo "Timestamp: $(date)"
        echo "Offset: $hex_offset"
        echo "Operation: $operation"
        [ "$operation" = "write" ] && echo "Value: $hex_value"
        echo "Description: $description"
        echo ""
        echo "--- BEFORE ---"
    } > "$result_file"
    
    # Capture before state
    "$REG_ACCESS" scan 0 63 >> "$result_file" 2>&1 || true
    sudo dmesg | tail -10 >> "$result_file" 2>&1 || true
    
    echo "" >> "$result_file"
    echo "--- OPERATION ---" >> "$result_file"
    
    # Perform operation
    case "$operation" in
        read)
            "$REG_ACCESS" read $hex_offset >> "$result_file" 2>&1
            ;;
        write)
            "$REG_ACCESS" write $hex_offset $hex_value >> "$result_file" 2>&1
            sleep 0.5
            ;;
        test)
            # Write, then read back
            "$REG_ACCESS" write $hex_offset $hex_value >> "$result_file" 2>&1
            sleep 0.5
            "$REG_ACCESS" read $hex_offset >> "$result_file" 2>&1
            ;;
    esac
    
    echo "" >> "$result_file"
    echo "--- AFTER ---" >> "$result_file"
    
    # Capture after state
    "$REG_ACCESS" scan 0 63 >> "$result_file" 2>&1 || true
    sudo dmesg | tail -20 >> "$result_file" 2>&1 || true
    
    echo "" >> "$result_file"
    echo "--- ANALYSIS ---" >> "$result_file"
    
    # Try to detect changes
    if grep -q "WRITE:" "$result_file"; then
        echo "Write operation completed" >> "$result_file"
        OLD_VAL=$(grep "old:" "$result_file" | sed 's/.*old: 0x\([0-9a-f]*\).*/\1/' | head -1)
        NEW_VAL=$(grep "WRITE:" "$result_file" | sed 's/.*WRITE: 0x\([0-9a-f]*\).*/\1/' | head -1)
        if [ "$OLD_VAL" != "$NEW_VAL" ]; then
            echo "Value changed: 0x$OLD_VAL -> 0x$NEW_VAL" >> "$result_file"
        fi
    fi
    
    echo "" >&2
    echo "Result saved: $result_file" >&2
    echo "--- Summary ---" >&2
    tail -20 "$result_file" | head -15 >&2
    echo "" >&2
    
    echo "$result_file"
}

# Interactive mode
interactive_mode() {
    echo "Interactive Register Testing" >&2
    echo "Enter hypotheses to test (or 'quit' to exit)" >&2
    echo "" >&2
    
    while true; do
        read -p "Test name: " name
        [ "$name" = "quit" ] && break
        
        read -p "Offset (hex, e.g. 0x10): " offset_str
        offset=$(( $offset_str ))
        
        read -p "Operation [read/write/test]: " op
        op=${op:-read}
        
        if [ "$op" = "write" ] || [ "$op" = "test" ]; then
            read -p "Value (hex, e.g. 0x1234): " value_str
            value=$(( $value_str ))
        else
            value=0
        fi
        
        read -p "Description: " desc
        
        test_hypothesis "$name" $offset "$op" $value "$desc"
        
        echo "" >&2
        read -p "Continue? [Y/n] " cont
        [ "$cont" = "n" ] && break
    done
}

# Batch mode from file
batch_mode() {
    local file=$1
    
    if [ ! -f "$file" ]; then
        echo "ERROR: Hypothesis file not found: $file" >&2
        exit 1
    fi
    
    echo "Processing hypotheses from: $file" >&2
    echo "" >&2
    
    while IFS= read -r line; do
        # Skip comments and empty lines
        [[ "$line" =~ ^#.*$ ]] && continue
        [ -z "$line" ] && continue
        
        # Parse: name,offset,operation,value,description
        IFS=',' read -r name offset op value desc <<< "$line"
        
        test_hypothesis "$name" $(( $offset )) "$op" $(( ${value:-0} )) "$desc"
        
        sleep 1
    done < "$file"
}

# Main
case "${1:-interactive}" in
    interactive|i)
        interactive_mode
        ;;
    batch|b)
        if [ -z "$2" ]; then
            echo "Usage: $0 batch <hypothesis_file>" >&2
            echo "File format: name,offset_hex,operation,value_hex,description" >&2
            exit 1
        fi
        batch_mode "$2"
        ;;
    test|t)
        if [ -z "$2" ] || [ -z "$3" ] || [ -z "$4" ]; then
            echo "Usage: $0 test <name> <offset_hex> <operation> [value_hex] [description]" >&2
            exit 1
        fi
        test_hypothesis "$2" $(( $3 )) "$4" $(( ${5:-0} )) "${6:-}"
        ;;
    list|l)
        echo "Test results:" >&2
        ls -lth "$RESULTS"/*.txt 2>/dev/null | head -20
        ;;
    help|*)
        echo "Feedback Loop for Register Discovery" >&2
        echo "" >&2
        echo "Usage: $0 [mode] [args...]" >&2
        echo "" >&2
        echo "Modes:" >&2
        echo "  interactive  - Interactive testing (default)" >&2
        echo "  batch <file> - Process hypotheses from file" >&2
        echo "  test <name> <off> <op> [val] [desc] - Single test" >&2
        echo "  list         - List test results" >&2
        echo "" >&2
        echo "Operations: read, write, test (write+read)" >&2
        echo "" >&2
        echo "Example hypothesis file format:" >&2
        echo "  # name,offset,operation,value,description" >&2
        echo "  enable_bit,0x10,write,0x1,Test enable bit" >&2
        echo "  status_reg,0x04,read,0,Read status register" >&2
        ;;
esac
