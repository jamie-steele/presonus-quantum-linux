#!/bin/bash
# Set up Ghidra on Linux for Quantum 2626 driver RE: install Java, download and unpack Ghidra.
# Run from repo root: ./scripts/setup_ghidra_linux.sh
# Optional: GHIDRA_INSTALL_DIR=/path ./scripts/setup_ghidra_linux.sh

set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALL_DIR="${GHIDRA_INSTALL_DIR:-$REPO/tools/ghidra}"
DRIVER_REF="$REPO/driver-reference"

echo "=== Ghidra setup for Quantum 2626 RE ==="
echo "Install dir: $INSTALL_DIR"
echo ""

# --- Java ---
# Ghidra 12+ requires JDK 21. Prefer 21 so the headless launcher doesn't prompt.
echo "Checking Java (Ghidra 12+ needs JDK 21; 11.x works with 17)..."
if [ -d /usr/lib/jvm/java-21-openjdk-amd64 ] && [ -x /usr/lib/jvm/java-21-openjdk-amd64/bin/java ]; then
  echo "  Found: JDK 21 at /usr/lib/jvm/java-21-openjdk-amd64"
elif command -v java >/dev/null 2>&1; then
  VER=$(java -version 2>&1 | head -1)
  echo "  Found: $VER"
  if java -version 2>&1 | grep -q '"21\.'; then
    echo "  OK (Java 21)"
  else
    echo "  Ghidra 12+ needs JDK 21. Install: sudo apt install openjdk-21-jdk"
    echo "  Then run this script again or set JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64"
  fi
else
  echo "  Java not found. Installing openjdk-21-jdk (required for Ghidra 12+)..."
  sudo apt-get update -qq
  sudo apt-get install -y openjdk-21-jdk
  echo "  Done. JDK 21 home: /usr/lib/jvm/java-21-openjdk-amd64"
fi
echo ""

# --- Ghidra ---
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

if [ -f support/analyzeHeadless ] || [ -f */support/analyzeHeadless ]; then
  GHIDRA_ROOT=$(dirname "$(dirname "$(find . -name analyzeHeadless -path '*/support/analyzeHeadless' 2>/dev/null | head -1)")")
  echo "Ghidra already installed at: $INSTALL_DIR/$GHIDRA_ROOT"
  echo "  To reinstall, remove that folder and run this script again."
  echo ""
  VENV_DIR="$REPO/tools/ghidra_venv"
  echo "Setting up PyGhidra in $VENV_DIR..."
  export GHIDRA_INSTALL_DIR="$INSTALL_DIR/$GHIDRA_ROOT"
  if [ -x "$VENV_DIR/bin/python3" ] && "$VENV_DIR/bin/python3" -c "import pyghidra" 2>/dev/null; then
    echo "  PyGhidra venv already OK."
  else
    [ ! -x "$VENV_DIR/bin/python3" ] && python3 -m venv "$VENV_DIR" 2>/dev/null
    [ ! -x "$VENV_DIR/bin/pip" ] && [ ! -x "$VENV_DIR/bin/pip3" ] && "$VENV_DIR/bin/python3" -m ensurepip --upgrade 2>/dev/null || true
    if GHIDRA_INSTALL_DIR="$INSTALL_DIR/$GHIDRA_ROOT" "$VENV_DIR/bin/python3" -m pip install pyghidra; then
      echo "  Installed PyGhidra in venv."
    else
      echo "  Pip install failed. Try manually:"
      echo "    GHIDRA_INSTALL_DIR=$INSTALL_DIR/$GHIDRA_ROOT $VENV_DIR/bin/python3 -m pip install pyghidra"
      exit 1
    fi
  fi
  echo ""
  echo "Next: put the Windows driver binary in the repo for analysis:"
  echo "  cp /path/to/pae_quantum.sys $DRIVER_REF/"
  echo "Then run headless analysis:"
  echo "  ./scripts/run_ghidra_analysis.sh"
  exit 0
fi

echo "Downloading Ghidra (this may take a few minutes, ~200MB)..."
# Prefer latest from API; fallback to known 11.1 build (Java 17)
GHIDRA_URL=""
if command -v curl >/dev/null 2>&1; then
  GHIDRA_URL=$(curl -sL "https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest" 2>/dev/null | grep -oE 'https://[^"]+ghidra[^"]+\.zip' | grep -v source | head -1)
fi
if [ -z "$GHIDRA_URL" ]; then
  GHIDRA_URL="https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.1_build/ghidra_11.1_PUBLIC_20241218.zip"
  echo "  Using fallback: Ghidra 11.1"
fi

ZIP="$INSTALL_DIR/ghidra.zip"
if command -v curl >/dev/null 2>&1; then
  curl -sL -o "$ZIP" "$GHIDRA_URL"
elif command -v wget >/dev/null 2>&1; then
  wget -q -O "$ZIP" "$GHIDRA_URL"
else
  echo "ERROR: need curl or wget to download Ghidra"
  exit 1
fi

if [ ! -f "$ZIP" ] || [ ! -s "$ZIP" ]; then
  echo "ERROR: download failed or empty. Get Ghidra manually:"
  echo "  https://github.com/NationalSecurityAgency/ghidra/releases"
  echo "  Extract to: $INSTALL_DIR"
  exit 1
fi

echo "Extracting..."
unzip -q -o "$ZIP" -d "$INSTALL_DIR"
rm -f "$ZIP"
GHIDRA_DIR=$(find "$INSTALL_DIR" -maxdepth 1 -type d -name 'ghidra_*' | head -1)
if [ -z "$GHIDRA_DIR" ]; then
  echo "ERROR: could not find ghidra_* folder after extract"
  exit 1
fi
echo "  Installed: $GHIDRA_DIR"
echo ""

# --- PyGhidra (so Python scripts run in headless) ---
VENV_DIR="$REPO/tools/ghidra_venv"
echo "Setting up PyGhidra..."
export GHIDRA_INSTALL_DIR="$GHIDRA_DIR"
if [ -x "$VENV_DIR/bin/python3" ] && "$VENV_DIR/bin/python3" -c "import pyghidra" 2>/dev/null; then
  echo "  PyGhidra venv already OK."
else
  # Create venv if missing
  if [ ! -x "$VENV_DIR/bin/python3" ]; then
    if ! python3 -m venv "$VENV_DIR" 2>/dev/null; then
      echo "  ERROR: python3 -m venv failed. Install: sudo apt install python3.10-venv"
      echo "  Then re-run this script."
      exit 1
    fi
  fi
  # Bootstrap pip if venv has no pip/pip3
  if [ ! -x "$VENV_DIR/bin/pip" ] && [ ! -x "$VENV_DIR/bin/pip3" ]; then
    echo "  Bootstrapping pip in venv..."
    "$VENV_DIR/bin/python3" -m ensurepip --upgrade 2>/dev/null || true
  fi
  if GHIDRA_INSTALL_DIR="$GHIDRA_DIR" "$VENV_DIR/bin/python3" -m pip install pyghidra; then
    echo "  Installed PyGhidra in $VENV_DIR"
  else
    echo "  Pip install failed. Try: GHIDRA_INSTALL_DIR=$GHIDRA_DIR $VENV_DIR/bin/python3 -m pip install pyghidra"
    exit 1
  fi
  echo "  Run analysis with: ./scripts/run_ghidra_analysis.sh"
fi
echo ""

# --- Driver binary reminder ---
if [ ! -f "$DRIVER_REF/pae_quantum.sys" ]; then
  echo "Put the Windows driver binary in the repo for headless analysis:"
  echo "  cp /path/to/pae_quantum.sys $DRIVER_REF/"
  echo ""
fi

echo "Setup done. Run headless analysis with:"
echo "  ./scripts/run_ghidra_analysis.sh"
echo "Or open the GUI: $GHIDRA_DIR/ghidraRun"
