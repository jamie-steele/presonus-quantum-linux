#!/bin/bash
# Run several tests with a real sound so you can hear which (if any) produces output.
# Masks pipewire for the whole run so it can't respawn between tests.
#
# Usage: ./scripts/linux_test_quantum_listen.sh [wav_file]
# Default WAV: first .wav in samples/ (e.g. samples/Rain Stick 128bpm.wav)
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER_DIR="$REPO/driver"
SAMPLES_DIR="$REPO/samples"
CARD=4
WAV="$1"
if [ -z "$WAV" ] || [ ! -f "$WAV" ]; then
  WAV=$(ls "$SAMPLES_DIR"/*.wav 2>/dev/null | head -1)
fi
if [ -z "$WAV" ] || [ ! -f "$WAV" ]; then
  echo "No WAV found. Put a .wav in $SAMPLES_DIR/ or pass: $0 /path/to/file.wav"
  exit 1
fi

echo "=== Quantum 2626: listen test (multiple param combos) ==="
echo "Sound file: $WAV"
echo ""

# Use reload script to release Quantum card and unload (masks pipewire, kills holders, rmmod)
echo "Releasing Quantum and unloading module (via reload script)..."
export RELOAD_ONLY=1
"$REPO/scripts/reload_quantum_driver.sh" || {
  echo "ERROR: reload script failed. Fix the above, then run this script again."
  exit 1
}
echo ""

# Build so we have latest params
echo "Building driver..."
make -C "$DRIVER_DIR" 2>&1 | tail -3

# Unload module; if in use, script exits so user can run reload_quantum_driver.sh first
unload_module() {
  local out
  out=$(sudo rmmod snd_quantum2626 2>&1) || true
  if ! lsmod | grep -q snd_quantum2626; then
    return 0
  fi
  echo "ERROR: could not unload snd_quantum2626 (module in use?)."
  echo "$out"
  echo "Run this first: ./scripts/reload_quantum_driver.sh"
  echo "Then run this listen script again."
  systemctl --user unmask pipewire.socket pipewire pipewire-pulse wireplumber 2>/dev/null || true
  exit 1
}

play_one() {
  CARD=$(cat /proc/asound/cards 2>/dev/null | grep -i quantum | head -1 | awk '{print $1}')
  [ -z "$CARD" ] && CARD=4
  echo "Playing on card $CARD... (listen now)"
  aplay -D "plughw:$CARD,0" -q "$WAV" 2>/dev/null || true
  echo "Pause 3s (did you hear that?)"
  sleep 3
}

echo "Unloading module (must succeed before we can reload with new params)..."
unload_module
sleep 1

# 1) STATUS2=0 STATUS3=0, control=0x8 (Ghidra stream-start style)
echo "--- reg_status2_value=0 reg_status3_value=0 control_value=0x8 ---"
sudo insmod "$DRIVER_DIR/snd-quantum2626.ko" reg_status2_value=0 reg_status3_value=0 control_value=0x8
sleep 1
play_one

# 2–5) control_value sweep (no status2/3)
for VAL in 0x8 0x88 0x9 0x10; do
  echo "--- control_value=$VAL (no status2/3) ---"
  unload_module
  sleep 1
  sudo insmod "$DRIVER_DIR/snd-quantum2626.ko" control_value=$VAL
  sleep 1
  play_one
done

echo ""
echo "Capturing dmesg..."
TS=$(date +%Y%m%d_%H%M%S)
sudo dmesg | tail -150 > "$REPO/notes/dmesg_quantum_listen_$TS.txt"
echo "Saved: notes/dmesg_quantum_listen_$TS.txt"

echo "Unmasking and starting user audio..."
systemctl --user unmask pipewire.socket pipewire pipewire-pulse wireplumber 2>/dev/null || true
systemctl --user start pipewire pipewire-pulse wireplumber 2>/dev/null || true
echo "Done. Note which run (status2/3=0 + 0x8, or control_value 0x8/0x88/0x9/0x10) produced sound."