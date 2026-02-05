# Linux Driver Testing Guide

**Date:** 2026-02-05  
**Purpose:** Test the current Linux driver implementation and gather feedback

## Prerequisites

- Linux system with Quantum 2626 connected
- Kernel headers installed (for building driver)
- ALSA utilities installed (`alsa-utils` package)
- Root/sudo access

## Step 1: Build the Driver

```bash
cd driver
make
```

**Expected output:** Should compile without errors, creating `snd-quantum2626.ko`

**If build fails:**
- Check kernel headers: `sudo apt install linux-headers-$(uname -r)` (Debian/Ubuntu)
- Or: `sudo dnf install kernel-devel` (Fedora/RHEL)

## Step 2: Load the Driver

```bash
# Load the driver
sudo insmod snd-quantum2626.ko

# Or with debug output
sudo insmod snd-quantum2626.ko dump_on_trigger=1
```

**Check dmesg immediately:**
```bash
dmesg | tail -30
```

**What to look for:**
- ✅ "MMIO+0x00: 0x..." - Register values at probe
- ✅ "Device status check (LED should be solid if initialized)" - Status registers
- ✅ "snd-quantum2626: PreSonus Quantum 2626 at ..." - Card registered
- ❌ Any errors or warnings

## Step 3: Check Device Status

### A. Check LED
- **Blue LED should be solid** = Device initialized correctly
- **LED not solid** = Initialization incomplete, check dmesg

### B. Check ALSA Card
```bash
# List audio cards
aplay -l
arecord -l

# Should show:
# card X: Quantum2626 [PreSonus Quantum 2626], device 0: Quantum PCM [Quantum PCM]
```

### C. Check Device Files
```bash
ls -l /dev/snd/ | grep quantum
# Should show controlC0, pcmC0D0p (playback), pcmC0D0c (capture)
```

### D. Check Interrupts
```bash
cat /proc/interrupts | grep quantum
# Should show interrupt count if MSI/IRQ is working
```

## Step 4: Test Playback

```bash
# Test with a simple tone
speaker-test -c 2 -t sine -f 1000 -l 1

# Or play a test file
aplay /usr/share/sounds/alsa/Front_Left.wav

# Or specify card directly
aplay -D plughw:CARD,0 /usr/share/sounds/alsa/Front_Left.wav
```

**While playing, check dmesg:**
```bash
# Watch dmesg in real-time
sudo dmesg -w
```

**What to look for:**
- ✅ "prepare playback: dma_addr=0x... buffer_size=..." - Buffer programmed
- ✅ "prepare: CONTROL 0x100 = 0x8" - Control register written
- ✅ "trigger: START" - Stream started
- ✅ Interrupt messages (if IRQ working)
- ❌ Any errors or xruns

## Step 5: Test Capture

```bash
# Record for 5 seconds
arecord -D plughw:CARD,0 -f cd -d 5 test.wav

# Check if file was created and has data
ls -lh test.wav
file test.wav
```

## Step 6: Capture Register Dumps

### A. Baseline (at load)
```bash
# Already captured in dmesg, but you can also:
sudo modprobe snd-quantum2626 reg_scan=1
dmesg | grep "MMIO+"
```

### B. During Playback
```bash
# Load with dump enabled
sudo rmmod snd-quantum2626
sudo insmod snd-quantum2626.ko dump_on_trigger=1

# Play audio
aplay /usr/share/sounds/alsa/Front_Left.wav

# Check dmesg for register dumps
dmesg | grep -A 20 "MMIO at prepare"
dmesg | grep -A 20 "MMIO at trigger"
```

### C. Manual Register Read
```bash
# Read specific register (example: 0x100)
sudo rmmod snd-quantum2626
sudo insmod snd-quantum2626.ko reg_read_offset=0x100
dmesg | grep "MMIO+0x100"
```

## Step 7: Compare with Windows Baseline

**From Windows baseline (`notes/MMIO_BASELINE.md`):**
- Register 0x00: Should be 0x00000000 (or device ID)
- Register 0x04: Should be 0x01030060 (status/ID)
- Register 0x08: Should be 0x00000010

**Compare Linux values:**
```bash
dmesg | grep "MMIO+0x"
```

**If values differ:**
- Note the differences
- May indicate initialization sequence issue

## Step 8: Check for Sound Output

**Expected behavior:**
- ✅ Audio plays through Quantum 2626 outputs
- ✅ No xruns (underruns/overruns)
- ✅ LED remains solid

**If no sound:**
- Check dmesg for errors
- Verify buffer addresses are programmed
- Check if interrupts are firing
- Compare register values with Windows

## Step 9: Capture Debug Information

**Create a debug report:**
```bash
# Save all relevant info
{
    echo "=== System Info ==="
    uname -a
    echo ""
    echo "=== PCI Device ==="
    lspci -vv -s $(lspci | grep -i presonus | cut -d' ' -f1)
    echo ""
    echo "=== Driver Logs ==="
    dmesg | grep -i quantum
    echo ""
    echo "=== ALSA Cards ==="
    aplay -l
    arecord -l
    echo ""
    echo "=== Interrupts ==="
    cat /proc/interrupts | grep -E "quantum|audio"
} > quantum_test_report.txt
```

## Step 10: Test Different Scenarios

### A. Different Sample Rates
```bash
# Test 44.1 kHz
aplay -D plughw:CARD,0 -r 44100 test.wav

# Test 48 kHz
aplay -D plughw:CARD,0 -r 48000 test.wav

# Test 96 kHz
aplay -D plughw:CARD,0 -r 96000 test.wav
```

**Check dmesg for each:**
- Do register values change?
- Which registers change with sample rate?

### B. Different Formats
```bash
# Test 16-bit
aplay -D plughw:CARD,0 -f S16_LE test.wav

# Test 24-bit (if supported)
aplay -D plughw:CARD,0 -f S24_LE test.wav
```

## What to Report Back

1. **LED Status:**
   - [ ] Solid blue (good!)
   - [ ] Not solid (initialization issue)

2. **Device Detection:**
   - [ ] Card appears in `aplay -l`
   - [ ] Device files created in `/dev/snd/`

3. **Playback:**
   - [ ] Audio plays
   - [ ] No audio (but no errors)
   - [ ] Errors in dmesg

4. **Register Values:**
   - Copy register dumps from dmesg
   - Compare with Windows baseline
   - Note any differences

5. **Interrupts:**
   - [ ] Interrupts firing (check `/proc/interrupts`)
   - [ ] No interrupts (using timer fallback)

6. **Errors/Warnings:**
   - Copy any error messages from dmesg
   - Note any xruns or underruns

## Troubleshooting

### Driver won't load
```bash
# Check for errors
dmesg | tail -20

# Common issues:
# - Kernel version mismatch (rebuild driver)
# - Missing dependencies
# - Device already claimed by another driver
```

### No sound output
1. Check LED status
2. Verify register values match Windows
3. Check if interrupts are working
4. Verify buffer addresses are programmed
5. Check for xruns in dmesg

### Device not detected
```bash
# Check PCI device
lspci | grep -i presonus

# Check if driver is loaded
lsmod | grep quantum

# Check dmesg for probe errors
dmesg | grep quantum
```

## Next Steps After Testing

Based on test results:
1. **If LED not solid:** Need to find missing initialization register
2. **If no sound:** Compare register values with Windows, find format/sample rate registers
3. **If interrupts not working:** Verify IRQ setup, check interrupt handler
4. **If sound works:** Great! Refine format/sample rate support

## Files to Check

- `dmesg` output - Register values and debug info
- `/proc/interrupts` - Interrupt status
- `aplay -l` / `arecord -l` - Device detection
- Register dumps - Compare with Windows baseline

## Quick Test Checklist

- [ ] Driver builds successfully
- [ ] Driver loads without errors
- [ ] LED is solid blue
- [ ] Card appears in `aplay -l`
- [ ] Can attempt playback
- [ ] Register values logged in dmesg
- [ ] Interrupts working (or timer fallback)
- [ ] Audio output (or errors logged)

Good luck! Report back with dmesg output and LED status.
