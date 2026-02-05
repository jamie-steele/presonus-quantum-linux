#!/bin/bash
# Run Ghidra headless analysis on pae_quantum.sys and execute a Python script.
# Usage:
#   ./scripts/run_ghidra_analysis.sh
#   ./scripts/run_ghidra_analysis.sh trace_stream_start_writes.py
#   ./scripts/run_ghidra_analysis.sh find_mmio_registers.py
#
# Requires: run scripts/setup_ghidra_linux.sh first, and have driver-reference/pae_quantum.sys

set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT_DIR="$REPO/scripts/ghidra"
DRIVER_REF="$REPO/driver-reference"
DRIVER_BIN="${DRIVER_BIN:-$DRIVER_REF/pae_quantum.sys}"
PROJECT_DIR="${GHIDRA_PROJECT_DIR:-$REPO/tools/ghidra_projects}"
PROJECT_NAME="${GHIDRA_PROJECT_NAME:-Quantum2626}"
POST_SCRIPT="${1:-trace_stream_start_writes.py}"

# Find Ghidra install
GHIDRA_INSTALL_DIR="${GHIDRA_INSTALL_DIR:-$REPO/tools/ghidra}"
if [ ! -d "$GHIDRA_INSTALL_DIR" ]; then
  GHIDRA_INSTALL_DIR="${GHIDRA_INSTALL_DIR:-$HOME/ghidra}"
fi
HEADLESS=$(find "$GHIDRA_INSTALL_DIR" -name analyzeHeadless -path '*/support/analyzeHeadless' 2>/dev/null | head -1)
if [ -z "$HEADLESS" ]; then
  echo "ERROR: Ghidra not found. Run first: ./scripts/setup_ghidra_linux.sh"
  echo "  Or set GHIDRA_INSTALL_DIR to your Ghidra install (e.g. .../ghidra_11.1_PUBLIC)"
  exit 1
fi
GHIDRA_ROOT="$(dirname "$(dirname "$HEADLESS")")"

if [ ! -f "$DRIVER_BIN" ]; then
  echo "ERROR: Driver binary not found: $DRIVER_BIN"
  echo "  Copy pae_quantum.sys into driver-reference/ or set DRIVER_BIN=/path/to/pae_quantum.sys"
  exit 1
fi

if [ ! -f "$SCRIPT_DIR/$POST_SCRIPT" ]; then
  echo "ERROR: Script not found: $SCRIPT_DIR/$POST_SCRIPT"
  exit 1
fi

mkdir -p "$PROJECT_DIR"
echo "=== Ghidra headless ==="
echo "  Ghidra:    $GHIDRA_ROOT"
echo "  Driver:    $DRIVER_BIN"
echo "  Project:   $PROJECT_DIR / $PROJECT_NAME"
echo "  PostScript: $POST_SCRIPT"
echo ""

# -import imports and analyzes the binary; -postScript runs after analysis
# Script output goes to console; script can also write files to SCRIPT_DIR
"$HEADLESS" \
  "$PROJECT_DIR" \
  "$PROJECT_NAME" \
  -import "$DRIVER_BIN" \
  -scriptPath "$SCRIPT_DIR" \
  -postScript "$POST_SCRIPT"

echo ""
echo "Done. If the script wrote files, check $SCRIPT_DIR/"
