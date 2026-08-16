# Ghidra Analysis Progress

**Date:** 2026-02-05  
**Status:** Comprehensive analysis in progress

## What We've Found

### ✅ Confirmed Register Offsets

| Offset | Type | Found In | Purpose (Suspected) |
|--------|------|----------|---------------------|
| 0x0000 | Read | FUN_140003d60 | Version/ID register |
| 0x0004 | Read | FUN_140003d60 | Status/Control (interrupt status) |
| 0x0008 | Read | FUN_140003d60 | Status/Control |
| 0x0010 | Read | FUN_140003d60 | Status/Control |
| 0x0014 | Read | FUN_140003d60 | Status/Control |
| 0x0100 | Write | FUN_140002e30 | Control register (write 0x8 to start) |
| 0x0104 | Read | FUN_140003d60 | Status/Control (possible position) |
| 0x10300 | Read | FUN_140003d60 | Buffer register (playback DMA address) |
| 0x10304 | Read | FUN_140003d60 | Buffer register (capture DMA address) |

### 📊 Analysis Results

- **MMIO Base Storage:** Found 122 references to offset 0xc8 (MMIO base storage)
- **Functions Using MMIO:** 75+ functions identified
- **Register Access Patterns:** Found many offset patterns, need filtering

### 🔍 Current Analysis

Running comprehensive register search - finding many offset patterns. Need to:
1. Filter for actual MMIO registers (not stack operations)
2. Focus on known functions (FUN_140003d60, FUN_140002e30)
3. Find format/sample rate registers
4. Analyze interrupt handler

## Scripts Created

1. `find_all_registers.py` - Comprehensive search (found 14 offsets, many were stack)
2. `find_mmio_registers_enhanced.py` - Enhanced MMIO-specific search
3. `find_registers_simple.py` - Simple scalar search (finding many patterns)

## Next Actions

1. **Filter Results** - Focus on offsets found in known MMIO functions
2. **Manual Analysis** - Use Ghidra GUI to trace specific functions
3. **Cross-Reference** - Follow XRefs from FUN_140003d60 to find all MMIO usage
4. **Sample Rate Search** - Look for 44100, 48000 values and trace to registers

## Key Functions to Analyze

- `FUN_140003d60` - Device initialization (already analyzed)
- `FUN_140002e30` - Control register write (already found)
- `FUN_14000d410` - Likely interrupt handler (needs analysis)
- Functions called after initialization - may contain stream control
