# Next Round Status - Windows Analysis

**Date:** 2026-02-03  
**Status:** Ready for deeper register analysis

## Current Driver Implementation

The Linux driver has been implemented with basic hardware register access:

### ✅ Implemented
- DMA buffer address programming (0x10300, 0x10304)
- Control register writes (0x100 = 0x8 to start, 0x0 to stop)
- Interrupt status reading (0x0004)
- Basic position tracking (software fallback)

### ❌ Missing / Needs Refinement
1. **Sample Rate Programming** - No registers identified yet
2. **Format Programming** - Bit depth, channel count not programmed
3. **Control Register Bit Fields** - We write 0x8, but exact bits unknown
4. **Hardware Position Register** - Using placeholder (0x0104)
5. **Interrupt Acknowledgment** - Method needs verification
6. **Buffer Size Registers** - May need to program buffer size separately

## What We Need to Find

### Priority 1: Format/Sample Rate Registers
- Which register(s) set sample rate (44100, 48000, 96000, 192000)?
- Which register(s) set bit depth (16, 24, 32)?
- Which register(s) set channel count?

### Priority 2: Control Register Details
- What do the bits in 0x100 mean?
- Is 0x8 the correct start value, or should it be a bit mask?
- Are there separate start/stop bits?

### Priority 3: Position Register
- Which register contains the hardware playback/capture position?
- How is position calculated (frames, bytes, samples)?

### Priority 4: Interrupt Handling
- Exact method of acknowledging interrupts
- Which bits in status register indicate what events?

## Analysis Tools Created

1. **`scripts/ghidra/find_format_registers.py`** - Searches for sample rate/format values
2. **`scripts/ghidra/run_format_analysis.ps1`** - Runs format analysis

## Next Steps

### Option 1: Enhanced Ghidra Analysis
- Run format register script (needs PyGhidra setup)
- Search for control register bit operations (AND, OR, XOR)
- Find position register by searching for counter/position operations
- Analyze interrupt handler in detail

### Option 2: Windows Capture During Different Operations
- Capture register activity at different sample rates (44100 vs 48000)
- Capture register activity with different formats (16-bit vs 24-bit)
- Compare register values to identify format/sample rate registers

### Option 3: Manual Ghidra Analysis
- Open project in Ghidra GUI
- Search for sample rate constants (44100, 48000, etc.)
- Trace where these values are written to MMIO
- Document findings in `notes/REGISTER_GUESSES.md`

## Recommended Approach

1. **Start with Windows capture** - Quickest way to see what changes
   - Play audio at 44100 Hz, capture registers
   - Play audio at 48000 Hz, capture registers
   - Compare to find sample rate register

2. **Then refine with Ghidra** - Understand the full picture
   - Use captured data to guide Ghidra search
   - Find exact bit fields and programming sequences

3. **Update driver** - Implement findings
   - Add format/sample rate programming
   - Refine control register usage
   - Fix position register

## Files to Check

- `notes/REGISTER_GUESSES.md` - Current register findings
- `notes/DRIVER_IMPLEMENTATION.md` - What's implemented
- `scripts/ghidra/find_format_registers.py` - Format analysis script
- `driver/snd-quantum2626.c` - Current driver implementation
