# Ghidra Analysis Findings Summary

**Date:** 2026-02-05  
**Status:** Comprehensive analysis in progress

## ✅ Confirmed Register Offsets

| Offset | Type | Function | Purpose (Confirmed/Suspected) |
|--------|------|----------|--------------------------------|
| 0x0000 | Read | FUN_140003d60 | Version/ID register |
| 0x0004 | Read | FUN_140003d60 | Status1 - Interrupt status (likely) |
| 0x0008 | Read | FUN_140003d60 | Status2 |
| 0x0010 | Read | FUN_140003d60 | Status3 |
| 0x0014 | Read | FUN_140003d60 | Status4 |
| 0x0100 | Write | FUN_140002e30 | Control register - Write 0x8 to start/enable |
| 0x0104 | Read | FUN_140003d60 | Status5 - Possible position register |
| 0x10300 | Read | FUN_140003d60 | Buffer0 - Playback DMA buffer address |
| 0x10304 | Read | FUN_140003d60 | Buffer1 - Capture DMA buffer address |

## 📊 Analysis Results

- **MMIO Base Storage:** 112+ references to offset 0xc8 (MMIO base in device structure)
- **Functions Using MMIO:** 44+ functions identified
- **Interrupt Handler:** IoConnectInterruptEx called from FUN_140003d60
- **Register Access Patterns:** Many offset patterns found, need filtering

## ❓ Missing Registers (To Find)

### Priority 1: Format/Sample Rate Registers
- **Sample Rate Register:** Which register sets 44100, 48000, 96000, 192000 Hz?
- **Bit Depth Register:** Which register sets 16, 24, 32-bit?
- **Channel Count Register:** Which register sets mono/stereo/multi-channel?

### Priority 2: Control Register Details
- **Control Register Bit Fields:** What do the bits in 0x100 mean?
  - Currently we write 0x8, but what does each bit do?
  - Are there separate start/stop bits?
  - Format/sample rate bits?

### Priority 3: Position Register
- **Hardware Position:** Which register contains playback/capture position?
  - Currently using 0x0104 as placeholder
  - Need to verify or find actual position register

### Priority 4: Interrupt Handling
- **Interrupt Handler Function:** Find the actual handler function
- **Interrupt Status Register:** Verify 0x0004 is interrupt status
- **Interrupt Acknowledge:** How to properly acknowledge interrupts?

## 🔍 Analysis Approach

### What's Working
1. **Known Function Analysis:** FUN_140003d60 and FUN_140002e30 analyzed
2. **MMIO Base Tracing:** Found 44+ functions using MMIO
3. **Interrupt Setup:** Found IoConnectInterruptEx calls

### Challenges
1. **Indirect Addressing:** MMIO base loaded into register, then offsets added
   - Pattern: `MOV RAX, [RCX + 0xc8]` then `MOV EDX, [RAX + 0x100]`
   - Makes pattern matching difficult
2. **Sample Rate Values:** Not found as literals - may be calculated or in lookup tables
3. **Register Offsets:** Many found but need filtering (stack vs MMIO)

## 📝 Next Steps

1. **Manual Ghidra Analysis:**
   - Open FUN_140003d60 in Ghidra GUI
   - Use Search > For Scalars for: 0x108, 0x10c, 0x200, 0x300
   - Follow XRefs from MMIO base usage
   - Decompile functions to see register access patterns

2. **Function Call Analysis:**
   - Find where FUN_140002e30 (control write) is called
   - Trace functions called after initialization
   - Look for stream start/stop functions

3. **Sample Rate Approach:**
   - Search for functions that might calculate sample rate divisors
   - Look for lookup tables with sample rate values
   - Check Windows driver behavior at different sample rates

4. **Linux Testing:**
   - Test current driver implementation
   - Use LED status as indicator
   - Compare register values with Windows baseline

## 🎯 Current Driver Status

**Implemented:**
- ✅ DMA buffer address programming (0x10300, 0x10304)
- ✅ Control register write (0x100 = 0x8)
- ✅ Status register reads (0x0, 0x4, 0x104)
- ✅ Interrupt handler skeleton

**Missing:**
- ❌ Sample rate programming
- ❌ Format programming (bit depth, channels)
- ❌ Hardware position register (using placeholder)
- ❌ Interrupt acknowledgment method

## 📁 Analysis Files

- `scripts/ghidra/find_all_registers.py` - Comprehensive search
- `scripts/ghidra/find_registers_simple.py` - Simple scalar search
- `scripts/ghidra/find_format_sample_rate.py` - Format/sample rate search
- `scripts/ghidra/find_interrupt_handler.py` - Interrupt analysis
- `scripts/ghidra/find_missing_registers.py` - Missing register finder
- `scripts/ghidra/trace_mmio_usage.py` - MMIO base tracing

## 💡 Recommendations

1. **Continue with current implementation** - We have enough to test
2. **Use Linux testing feedback** - LED status and register dumps will guide us
3. **Compare with Windows** - Capture Windows register values during playback
4. **Manual Ghidra analysis** - GUI analysis may be more effective for complex patterns
