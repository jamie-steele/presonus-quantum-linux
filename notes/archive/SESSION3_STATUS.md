# Session 3 Status - Register Work Needed

**Date:** 2026-01-31  
**Status:** Working driver skeleton, need register programming

## Current State

### ✅ What's Working

1. **Driver Skeleton** (`driver/snd-quantum2626.c`):
   - ✅ PCI device claimed (1c67:0104)
   - ✅ BAR 0 mapped (1 MiB MMIO space at `chip->iobase`)
   - ✅ ALSA card registered
   - ✅ PCM device created (playback + capture)
   - ✅ IRQ handling wired (MSI or timer fallback)
   - ✅ MMIO baseline captured (first 64 bytes logged at probe)

2. **Infrastructure:**
   - ✅ Driver builds and loads
   - ✅ Card appears in `aplay -l` / `arecord -l`
   - ✅ Dump-on-trigger support for reverse engineering

### ❌ What's Missing

1. **No Hardware Register Programming:**
   - `prepare()` - doesn't program buffers, format, or sample rate
   - `trigger()` - doesn't start/stop hardware streams
   - `pointer()` - uses fake timer-based position, not hardware
   - IRQ handler - doesn't read/ack interrupt status

2. **Unknown Register Map:**
   - Which MMIO offsets are which registers?
   - Buffer address registers?
   - Format/sample rate registers?
   - Start/stop control bits?
   - Position/status registers?
   - Interrupt status/ack?

## Known MMIO Baseline

From `notes/MMIO_BASELINE.md`:

| Offset | Value      | Notes |
|--------|------------|-------|
| 0x00   | 0x00000000 | |
| 0x04   | 0x01030060 | Non-zero; possible ID/version or config |
| 0x08   | 0x00000010 | |
| 0x0c   | 0xffffffff | Likely unimplemented / read-as-one |
| 0x10   | 0x00000000 | |
| 0x14   | 0x00000000 | |
| 0x18-0x3c | 0xffffffff | Likely unimplemented |

## Next Steps - Register Discovery & Implementation

### Phase 1: Reverse Engineer Windows Driver

**Goal:** Find register offsets and programming sequences from `pae_quantum.sys`

1. **Analyze Windows Driver Binary:**
   - Load `pae_quantum.sys` in Ghidra/IDA Pro
   - Search for MMIO access patterns:
     - Base address + offset patterns
     - Constants matching known offsets (0x04, 0x08, etc.)
     - Buffer address writes
     - Format/sample rate programming
     - Start/stop control bits

2. **Key Areas to Find:**
   - **Buffer Setup:** Where does driver write DMA buffer addresses?
   - **Format Programming:** Sample rate, bit depth, channel count
   - **Stream Control:** Start/stop/enable bits
   - **Position Reading:** Hardware pointer register
   - **Interrupt Handling:** Status register, ack register

3. **Document Findings:**
   - Update `notes/REGISTER_GUESSES.md` with:
     - Offset → suspected role
     - Source (Ghidra analysis, experimentation)
     - Programming sequence

### Phase 2: Implement Hardware Access

**Goal:** Program actual hardware registers in Linux driver

1. **Implement `prepare()`:**
   ```c
   // Program buffer address(es) from runtime->dma_addr
   // Program format: sample rate, bit depth, channels
   // Program period size / buffer size
   ```

2. **Implement `trigger()`:**
   ```c
   // START: Set enable/start bit(s) in control register
   // STOP: Clear enable/start bit(s), optionally reset position
   ```

3. **Implement `pointer()`:**
   ```c
   // Read hardware position register
   // Convert to frames and return
   ```

4. **Refine IRQ Handler:**
   ```c
   // Read interrupt status register
   // Only call snd_pcm_period_elapsed() when device reports period
   // Acknowledge interrupt
   ```

### Phase 3: Testing & Refinement

1. **Test Playback:**
   - `aplay -D plughw:CARD,0 test.wav`
   - Check for actual audio output
   - Monitor for xruns

2. **Test Capture:**
   - `arecord -D plughw:CARD,0 test.wav`
   - Verify audio is captured
   - Check for xruns

3. **Refine:**
   - Adjust buffer sizes if needed
   - Fix timing issues
   - Handle different sample rates/formats

## Resources Available

### Documentation
- `docs/REVERSE_ENGINEERING_PLAN.md` - Detailed reverse engineering plan
- `notes/MMIO_BASELINE.md` - Known register values at load
- `notes/REGISTER_GUESSES.md` - Template for documenting findings
- `driver/README.md` - Driver build/load instructions

### Windows Driver Reference
- `driver-reference/pae_quantum.inf` - Device IDs, service info
- `driver-reference/README.md` - Reference file descriptions
- **Note:** `pae_quantum.sys` binary should be kept locally (not in repo)

### Scripts
- `scripts/capture_mmio_baseline.sh` - Capture MMIO at load
- `scripts/probe_during_playback.sh` - Capture MMIO during playback
- `scripts/windows_re_strings.ps1` - Extract strings from Windows driver
- `scripts/windows_re_next_run.ps1` - Full reverse engineering run

## Current Driver Code Status

**File:** `driver/snd-quantum2626.c`

**Lines to modify:**
- `quantum_pcm_prepare()` (line 159) - Currently just dumps MMIO, needs register programming
- `quantum_pcm_trigger()` (line 175) - Currently just manages timer, needs hardware start/stop
- `quantum_pcm_pointer()` (line 225) - Currently uses fake position, needs hardware read
- `snd_quantum_interrupt()` (line 284) - Currently just signals period, needs status read/ack

**BAR Access:**
- ✅ BAR 0 is mapped: `chip->iobase = pci_iomap(pci, 0, 0);` (line 357)
- ✅ Can read/write: `readl(chip->iobase + offset)`, `writel(value, chip->iobase + offset)`
- ❌ Need to know which offsets to use!

## Immediate Next Steps

1. **If you have `pae_quantum.sys` locally:**
   - Load it in Ghidra
   - Search for MMIO access patterns
   - Document register offsets in `notes/REGISTER_GUESSES.md`

2. **If you need to extract more info:**
   - Run `scripts/windows_re_strings.ps1` on Windows
   - Look for register names, offsets, buffer operations

3. **Experimental approach:**
   - Use `dump_on_trigger=1` to see register changes during playback
   - Compare baseline vs. during playback
   - Try writing to suspected registers and observe behavior

## Questions to Answer

1. **Buffer Programming:**
   - Where does driver write DMA buffer address?
   - Is there a buffer descriptor table?
   - How are multiple periods handled?

2. **Format Programming:**
   - Which register sets sample rate?
   - Which register sets bit depth?
   - Which register sets channel count?

3. **Stream Control:**
   - Which bit(s) start playback?
   - Which bit(s) start capture?
   - How to stop streams?

4. **Position/Status:**
   - Which register has current position?
   - Which register has interrupt status?
   - How to acknowledge interrupts?

## Success Criteria

- [ ] `prepare()` programs hardware buffers and format
- [ ] `trigger(START)` actually starts hardware stream
- [ ] `trigger(STOP)` stops hardware stream
- [ ] `pointer()` reads actual hardware position
- [ ] IRQ handler reads and acknowledges interrupt status
- [ ] Audio actually plays through device
- [ ] Audio actually captures from device
- [ ] No xruns during normal operation
