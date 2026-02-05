#!/bin/bash
# One-shot test: reload driver (optional params), play a few seconds, capture dmesg to notes/.
# Usage:
#   ./scripts/linux_test_quantum.sh
#   MODPARAMS="reg_srate_offset=0x108 reg_srate_value=48000" ./scripts/linux_test_quantum.sh
#   ./scripts/linux_test_quantum.sh --no-reload --duration 3
#   ./scripts/linux_test_quantum.sh --build
#   RELOAD_FORCE_MASK=1 ./scripts/linux_test_quantum.sh   # if wireplumber keeps respawning
#   ./scripts/linux_test_quantum.sh --sound /usr/share/sounds/alsa/Front_Left.wav  # play real sound to hear if hardware works
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER_DIR="$REPO/driver"
NOTES_DIR="$REPO/notes"
CARD=4
RELOAD=1
DURATION=5
BUILD=0
SOUND_FILE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --no-reload) RELOAD=0 ;;
    --duration)  DURATION="$2"; shift ;;
    --build)     BUILD=1 ;;
    --sound)     SOUND_FILE="$2"; shift ;;
  esac
  shift
done

# MODPARAMS: set from env, e.g. MODPARAMS="reg_srate_offset=0x108 reg_srate_value=48000"
MODPARAMS=$(echo "${MODPARAMS:-}" | sed 's/^ *//; s/ *$//')

echo "=== Quantum 2626 test: reload=$RELOAD duration=${DURATION}s build=$BUILD ==="
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
