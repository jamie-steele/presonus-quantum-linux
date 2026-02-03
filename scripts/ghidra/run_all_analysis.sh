#!/bin/bash
# Run all Ghidra analysis scripts in headless mode
# Usage: ./run_all_analysis.sh <ghidra_install_path> <project_path> <project_name>

GHIDRA_PATH="$1"
PROJECT_PATH="$2"
PROJECT_NAME="$3"

if [ -z "$GHIDRA_PATH" ] || [ -z "$PROJECT_PATH" ] || [ -z "$PROJECT_NAME" ]; then
    echo "Usage: $0 <ghidra_install_path> <project_path> <project_name>"
    echo "Example: $0 ~/Ghidra/ghidra_12.0.2_PUBLIC ~/ghidra_projects Quantum2626_Driver"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Running Ghidra analysis scripts..."
echo "Ghidra: $GHIDRA_PATH"
echo "Project: $PROJECT_PATH/$PROJECT_NAME"
echo ""

# Run each script
for script in find_mmio_registers.py find_buffer_registers.py find_interrupt_registers.py; do
    echo "=== Running $script ==="
    "$GHIDRA_PATH/support/analyzeHeadless" \
        "$PROJECT_PATH" \
        "$PROJECT_NAME" \
        -process pae_quantum.sys \
        -scriptPath "$SCRIPT_DIR" \
        -postScript "$script" \
        -deleteProject
    echo ""
done

echo "Analysis complete!"
