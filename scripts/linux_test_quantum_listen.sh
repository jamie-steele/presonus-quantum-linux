#!/bin/bash
# Run several control_value tests with a real sound so you can hear which (if any) produces output.
# Masks pipewire for the whole run so it can't respawn between tests.
#
# Usage: ./scripts/linux_test_quantum_listen.sh [wav_file]
# Default WAV: /usr/share/sounds/alsa/Front_Left.wav (install alsa-utils if missing)
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER_DIR="$REPO/driver"
CARD=4
WAV="${1:-/usr/share/sounds/alsa/Front_Left.wav}"

if [ ! -f "$WAV" ]; then
  echo "No WAV found at: $WAV"
  echo "Usage: $0 [path/to/audio.wav]"
  echo "Install a test sound: sudo apt install alsa-utils  # provides Front_Left.wav"
  exit 1
fi

echo "=== Quantum 2626: listen test (control_value 0x8, 0x88, 0x9, 0x10) ==="
echo "Sound file: $WAV"
echo ""

# Mask pipewire for the whole run so it can't respawn between iterations
echo "Stopping and masking user audio for duration of test..."
systemctl --user stop pipewire.socket pipewire-pulse pipewire wireplumber 2>/dev/null || true
sleep 2
systemctl --user mask pipewire.socket pipewire pipewire-pulse wireplumber 2>/dev/null || true
sleep 2

echo "Releasing card $CARD..."
for try in 1 2 3 4 5 6 7 8; do
  for dev in /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c; do
    [ -e "$dev" ] && sudo fuser -k "$dev" 2>/dev/null || true
  done
  sleep 2
  still=$(sudo lsof /dev/snd/controlC$CARD /dev/snd/pcmC${CARD}D0p /dev/snd/pcmC${CARD}D0c 2>/dev/null || true)
  if [ -z "$still" ]; then
    echo "  Card free."
    break
  fi
  echo "  [try $try] still in use, retrying..."
  if [ $try -eq 8 ]; then
    echo "ERROR: Card still in use. Unmasking and exiting."
    systemctl --user unmask pipewire.socket pipewire pipewire-pulse wireplumber 2>/dev/null || true
    exit 1
  fi
done

for VAL in 0x8 0x88 0x9 0x10; do
  echo "--- control_value=$VAL ---"
  sudo rmmod snd_quantum2626 2>/dev/null || true
  sudo insmod "$DRIVER_DIR/snd-quantum2626.ko" control_value=$VAL
  sleep 1
  echo "Playing... (listen now)"
  aplay -D "plughw:$CARD,0" -q "$WAV" 2>/dev/null || true
  echo "Pause 3s (did you hear that?)"
  sleep 3
done

echo ""
echo "Capturing dmesg..."
TS=$(date +%Y%m%d_%H%M%S)
sudo dmesg | tail -150 > "$REPO/notes/dmesg_quantum_listen_$TS.txt"
echo "Saved: notes/dmesg_quantum_listen_$TS.txt"

echo "Unmasking and starting user audio..."
systemctl --user unmask pipewire.socket pipewire pipewire-pulse wireplumber 2>/dev/null || true
systemctl --user start pipewire pipewire-pulse wireplumber 2>/dev/null || true
echo "Done. Which control_value (0x8, 0x88, 0x9, 0x10) produced sound?"