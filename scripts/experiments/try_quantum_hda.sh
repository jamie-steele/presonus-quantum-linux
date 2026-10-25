#!/bin/bash
# Try to get the PreSonus Quantum 2626 (1c67:0104) working by adding its PCI ID
# to snd_hda_intel at runtime. Needs root. "For shits" — might work if the device
# has an HD Audio–compatible codec behind the Thunderbolt bridge.

VEN="1c67"
DEV="0104"
SUBVEN="1c67"
SUBDEV="0104"
DRIVER="snd_hda_intel"
SYS="/sys/bus/pci/drivers/$DRIVER"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo $0"
  exit 1
fi

echo "=== Try Quantum 2626 with $DRIVER (new_id) ==="
echo "Device: $VEN:$DEV (PreSonus)"
echo ""

# Add dynamic PCI ID so the driver will probe our device
if [ ! -d "$SYS" ]; then
  echo "Loading $DRIVER..."
  modprobe "$DRIVER" || true
fi
if [ ! -f "$SYS/new_id" ]; then
  echo "Driver $DRIVER has no new_id (not a PCI driver or no dynamic IDs)."
  exit 1
fi

# Try two-value form first (vendor device); some drivers reject four-value (with subvendor/subdevice)
echo "Adding ID (vendor device): $VEN $DEV"
if echo "$VEN $DEV" > "$SYS/new_id" 2>/dev/null; then
  echo "new_id accepted (two-value)."
elif echo "$VEN $DEV $SUBVEN $SUBDEV" > "$SYS/new_id" 2>/dev/null; then
  echo "new_id accepted (four-value)."
else
  echo "new_id rejected (Invalid argument). This driver may not accept dynamic IDs for this device."
  echo "Check: cat /sys/bus/pci/drivers/snd_hda_intel/new_id 2>/dev/null (should be write-only)."
  exit 1
fi
echo "Done. Checking ALSA..."
sleep 1

if aplay -l 2>/dev/null | grep -qi "quantum\|presonus\|1c67"; then
  echo ""
  echo "*** New card may have appeared. Run: aplay -l ; arecord -l"
else
  echo ""
  aplay -l 2>&1 || true
  echo ""
  echo "No Quantum card showed up. Probe may have failed (wrong driver for this hardware)."
  echo "Removing dynamic ID..."
  echo "$VEN $DEV" > "$SYS/remove_id" 2>/dev/null || true
  echo "$VEN $DEV $SUBVEN $SUBDEV" > "$SYS/remove_id" 2>/dev/null || true
  echo "Check dmesg for errors: dmesg | tail -20"
fi
