#!/bin/bash
# Quick Linux driver test script
# Run this after loading the driver to check status

echo "=== Quantum 2626 Driver Test ==="
echo ""

# Check if driver is loaded
if lsmod | grep -q quantum; then
    echo "✅ Driver is loaded"
    DRIVER_LOADED=1
else
    echo "❌ Driver not loaded"
    echo "   Load with: sudo insmod driver/snd-quantum2626.ko"
    DRIVER_LOADED=0
fi

echo ""

# Check dmesg for driver messages
echo "=== Recent Driver Messages ==="
dmesg | grep -i quantum | tail -20
echo ""

# Check ALSA cards
echo "=== ALSA Cards ==="
if command -v aplay >/dev/null 2>&1; then
    aplay -l 2>/dev/null | grep -i quantum || echo "  Quantum card not found in aplay -l"
else
    echo "  aplay not installed"
fi
echo ""

# Check device files
echo "=== Device Files ==="
if [ -d /dev/snd ]; then
    ls -l /dev/snd/ | grep -i quantum || echo "  No quantum device files found"
else
    echo "  /dev/snd not found"
fi
echo ""

# Check interrupts
echo "=== Interrupts ==="
if [ -f /proc/interrupts ]; then
    grep -i quantum /proc/interrupts || echo "  No quantum interrupts (may be using timer fallback)"
else
    echo "  /proc/interrupts not accessible"
fi
echo ""

# Check register values from dmesg
echo "=== Register Values (from dmesg) ==="
dmesg | grep "MMIO+0x" | tail -20 || echo "  No register values found"
echo ""

# LED status reminder
echo "=== LED Status Check ==="
echo "  Check the blue LED on the Quantum 2626:"
echo "  - Solid blue = Device initialized correctly ✅"
echo "  - Not solid = Initialization incomplete ❌"
echo ""

if [ $DRIVER_LOADED -eq 1 ]; then
    echo "=== Quick Test ==="
    echo "  Try playback:"
    echo "    aplay /usr/share/sounds/alsa/Front_Left.wav"
    echo ""
    echo "  Watch dmesg in another terminal:"
    echo "    sudo dmesg -w"
    echo ""
fi

echo "=== Done ==="
