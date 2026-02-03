# MMIO Capture Strategy - What to Test

## Initial Discovery (Minimal Testing)

For **initial register discovery**, you only need:

### 1. Baseline (Idle)
- Device powered on, no audio playing
- Capture: `quantum_baseline.etl`
- **Purpose:** See register state when idle

### 2. Simple Playback
- Play audio to **one output** (e.g., Main OUT or Line OUT 1/2)
- Capture: `quantum_playback.etl`
- **Purpose:** Discover:
  - Buffer address registers
  - Format/sample rate registers
  - Start/stop control bits
  - Position registers

### 3. Simple Capture
- Record from **one input** (e.g., Line IN 1/2 or Mic IN 1/2)
- Capture: `quantum_capture.etl`
- **Purpose:** See if capture uses different registers or same ones

## Why This is Enough

The **core register operations** are likely:
- **Shared across channels** - Same buffer setup mechanism
- **Same format registers** - One set for all channels
- **Channel-specific offsets** - Base registers + channel offset

So testing one channel reveals the pattern, then we can extrapolate to others.

## What We'll Learn

From minimal testing:
- ✅ **Buffer setup:** Where DMA addresses go
- ✅ **Format programming:** Sample rate, bit depth, channels
- ✅ **Stream control:** Start/stop/enable bits
- ✅ **Position tracking:** Hardware pointer register
- ✅ **Register layout:** Base offsets and structure

## Later Testing (If Needed)

After implementing basic playback/capture in Linux:

1. **Multi-channel testing:**
   - Test if channels use offset registers (e.g., channel 0 at 0x100, channel 1 at 0x200)
   - Or if they share registers with channel select bits

2. **Different formats:**
   - Test different sample rates (44.1k, 48k, 96k, 192k)
   - Test different bit depths (16-bit, 24-bit, 32-bit)

3. **Routing:**
   - Test channel routing/mixing registers (if any)

## Recommended Capture Sequence

```powershell
# 1. Baseline (5 seconds, idle)
.\windows_capture_register_activity.ps1 -OutputFile baseline.etl -DurationSeconds 5

# 2. Playback (10-15 seconds, play music to Main OUT)
.\windows_capture_register_activity.ps1 -OutputFile playback.etl -DurationSeconds 15

# 3. Capture (10-15 seconds, record from one input)
.\windows_capture_register_activity.ps1 -OutputFile capture.etl -DurationSeconds 15
```

That's it! Three captures should reveal the core register map.

## Analysis Priority

1. **Compare baseline vs playback:**
   - Which registers change?
   - What values are written?
   - What's the sequence?

2. **Compare playback vs capture:**
   - Same registers or different?
   - Different offsets or same?

3. **Document findings:**
   - Update `notes/REGISTER_GUESSES.md`
   - Note register offsets and suspected functions

## Bottom Line

**Start simple:** One playback, one capture.  
**Extrapolate:** Use the pattern for all channels.  
**Refine later:** Test edge cases if needed.

You don't need to test all 26 inputs and 26 outputs for initial discovery!
