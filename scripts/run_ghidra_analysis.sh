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
# Remove existing project so -import doesn't hit "conflicting program file"
rm -rf "$PROJECT_DIR/${PROJECT_NAME}.rep" "$PROJECT_DIR/${PROJECT_NAME}.gpr"

# Ghidra 12+ needs JDK 21. Use it if available so the launcher doesn't prompt.
if [ -z "${JAVA_HOME:-}" ]; then
  for jdk in /usr/lib/jvm/java-21-openjdk-amd64 /usr/lib/jvm/java-21-openjdk-*; do
    if [ -d "$jdk" ] && [ -x "$jdk/bin/java" ]; then
      export JAVA_HOME="$jdk"
      break
    fi
  done
fi
if [ -n "${JAVA_HOME:-}" ]; then
  echo "  JAVA_HOME: $JAVA_HOME"
fi

echo "=== Ghidra headless ==="
echo "  Ghidra:    $GHIDRA_ROOT"
echo "  Driver:    $DRIVER_BIN"
echo "  PostScript: $POST_SCRIPT"
echo ""

# Prefer PyGhidra so Python scripts (e.g. trace_stream_start_writes.py) actually run
export GHIDRA_INSTALL_DIR="$GHIDRA_ROOT"
PYGHIDRA_PYTHON=""
[ -x "$REPO/tools/ghidra_venv/bin/python3" ] && "$REPO/tools/ghidra_venv/bin/python3" -c "import pyghidra" 2>/dev/null && PYGHIDRA_PYTHON="$REPO/tools/ghidra_venv/bin/python3"
[ -z "$PYGHIDRA_PYTHON" ] && command -v python3 >/dev/null 2>&1 && python3 -c "import pyghidra" 2>/dev/null && PYGHIDRA_PYTHON="python3"
if [ -n "$PYGHIDRA_PYTHON" ]; then
  echo "  Using PyGhidra (Python)."
  $PYGHIDRA_PYTHON -m pyghidra "$DRIVER_BIN" "$SCRIPT_DIR/$POST_SCRIPT"
else
  echo "  ERROR: PyGhidra not found. Python scripts need PyGhidra (analyzeHeadless uses Jython only)."
  echo ""
  echo "  Install PyGhidra, then re-run:"
  echo "    ./scripts/setup_ghidra_linux.sh"
  echo "  Or manually (with venv):"
  echo "    GHIDRA_INSTALL_DIR=$GHIDRA_ROOT tools/ghidra_venv/bin/python3 -m ensurepip --upgrade"
  echo "    GHIDRA_INSTALL_DIR=$GHIDRA_ROOT tools/ghidra_venv/bin/python3 -m pip install pyghidra"
  echo "  Then: ./scripts/run_ghidra_analysis.sh"
  exit 1
fi

echo ""
echo "Done. If the script wrote files, check $SCRIPT_DIR/"
