#!/bin/bash
# Try one init_control_value at a time so you can watch the LED after each load.
# Usage: ./scripts/init_led_test.sh
# Optional: ./scripts/init_led_test.sh 0x8 0x88 0x10   (only try these)
set -e
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DRIVER_DIR="$REPO/driver"

# Default list: single values to try for CONTROL 0x100 at init
DEFAULT_VALUES="0x8 0x88 0x10 0x9 0x80 0x18 0x1 0x20 0x40"
VALUES="${*:-$DEFAULT_VALUES}"

echo "=== Init LED test: one value at a time (watch the blue LED) ==="
echo "Values to try: $VALUES"
echo ""

# Get to clean state: release card and unload
echo "Releasing and unloading..."
export RELOAD_ONLY=1
"$REPO/scripts/reload_quantum_driver.sh" 2>/dev/null || true
sleep 2
if ! sudo rmmod snd_quantum2626 2>/dev/null; then
  echo "Module still in use. Run first: $REPO/scripts/reload_quantum_driver.sh"
  echo "Then run this script again."
  exit 1
fi
sleep 1

for VAL in $VALUES; do
  echo "--- Loading with init_control_value=$VAL ---"
  sudo insmod "$DRIVER_DIR/snd-quantum2626.ko" init_control_value=$VAL
  echo "    >>> Look at the LED now (solid = good?). Waiting 8s..."
  sleep 8
  echo "    Unloading..."
  sudo rmmod snd_quantum2626
  sleep 2
done

echo ""
echo "Loading with default (init_control_value=-1, i.e. 0x8) so you have the card back."
sudo insmod "$DRIVER_DIR/snd-quantum2626.ko"
echo "Done. Note which value (if any) made the LED solid."
echo "Then load with that value: sudo insmod $DRIVER_DIR/snd-quantum2626.ko init_control_value=0xNN"
