#!/bin/bash
# One-shot test: reload driver (optional params), play a few seconds, capture dmesg to notes/.
# Usage:
#   ./scripts/linux_test_quantum.sh
#   MODPARAMS="reg_srate_offset=0x108 reg_srate_value=48000" ./scripts/linux_test_quantum.sh
#   ./scripts/linux_test_quantum.sh --no-reload --duration 3
#   ./scripts/linux_test_quantum.sh --build
#   RELOAD_FORCE_MASK=1 ./scripts/linux_test_quantum.sh   # if wireplumber keeps respawning
#   ./scripts/linux_test_quantum.sh --sound   # uses samples/*.wav if no path given
#   ./scripts/linux_test_quantum.sh --sound /path/to/file.wav
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER_DIR="$REPO/driver"
NOTES_DIR="$REPO/notes"
SAMPLES_DIR="$REPO/samples"
CARD=4
RELOAD=1
DURATION=5
BUILD=0
SOUND_FILE=""
SOUND_FLAG=0

while [ $# -gt 0 ]; do
  case "$1" in
    --no-reload) RELOAD=0 ;;
    --duration)  DURATION="$2"; shift ;;
    --build)     BUILD=1 ;;
    --sound)     SOUND_FLAG=1; SOUND_FILE="$2"; shift ;;
  esac
  shift
done
# If --sound with no path, use first WAV in samples/
if [ "$SOUND_FLAG" -eq 1 ] && { [ -z "$SOUND_FILE" ] || [ ! -f "$SOUND_FILE" ]; }; then
  SOUND_FILE=$(ls "$SAMPLES_DIR"/*.wav 2>/dev/null | head -1)
fi

# MODPARAMS: set from env, e.g. MODPARAMS="reg_srate_offset=0x108 reg_srate_value=48000"
MODPARAMS=$(echo "${MODPARAMS:-}" | sed 's/^ *//; s/ *$//')

echo "=== Quantum 2626 test: card=$CARD reload=$RELOAD duration=${DURATION}s build=$BUILD ==="
[ -n "$MODPARAMS" ] && echo "MODPARAMS: $MODPARAMS"

if [ "$BUILD" -eq 1 ]; then
  echo "Building driver..."
  make -C "$DRIVER_DIR" 2>&1
fi

if [ "$RELOAD" -eq 1 ]; then
  export RELOAD_ONLY=1
  [ -n "$MODPARAMS" ] && export MODPARAMS
  "$REPO/scripts/reload_quantum_driver.sh"
  sleep 1
fi

# Auto-detect Quantum card index (after reload it may not be 4)
CARD=$(cat /proc/asound/cards 2>/dev/null | grep -i quantum | head -1 | awk '{print $1}')
[ -z "$CARD" ] && CARD=4

if [ -n "$SOUND_FILE" ] && [ -f "$SOUND_FILE" ]; then
  echo "Playing sound: $SOUND_FILE (listen for output on Quantum)"
  aplay -D "plughw:$CARD,0" -q "$SOUND_FILE" || true
else
  echo "Playing silence on plughw:$CARD,0 for ${DURATION}s..."
  aplay -D "plughw:$CARD,0" -d "$DURATION" -f S16_LE -r 48000 -c 2 /dev/zero || true
fi

TS=$(date +%Y%m%d_%H%M%S)
LOG="$NOTES_DIR/dmesg_quantum_$TS.txt"
echo "Capturing dmesg to $LOG..."
sudo dmesg | tail -300 > "$LOG"
echo "  $(wc -l < "$LOG") lines written."

echo "Starting user audio..."
systemctl --user start pipewire pipewire-pulse wireplumber 2>/dev/null || true

echo "Done. Inspect: $LOG"
