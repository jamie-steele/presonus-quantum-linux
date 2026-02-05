# Register guesses (from Ghidra / reverse-engineering)

Fill in as you identify MMIO offsets from `pae_quantum.sys` or experimentation.

## Initial Register Reads (from FUN_140003d60)

Found in `FUN_140003d60` after `MmMapIoSpace` call. These registers are read during device initialization.

| Offset | Suspected role | Source / notes |
|--------|----------------|----------------|
| 0x0    | Version/ID register | Read immediately after MMIO mapping, stored at param_1+0x4f0 |
| 0x4    | Status/Control | Read during init, stored at param_1+0x4f4 |
| 0x8    | Status/Control | Read during init, stored at param_1+0x4f8 |
| 0x10   | Status/Control | Read during init, stored at param_1+0x4fc |
| 0x14   | Status/Control | Read during init, stored at param_1+0x500 |
| 0x104  | Status/Control | Read during init, stored at param_1+0x1d8 |
| 0x10300| Buffer/Channel register | Large offset, likely per-channel or buffer related, stored at param_1+0x1d0 |
| 0x10304| Buffer/Channel register | Large offset, likely per-channel or buffer related, stored at param_1+0x1d4 |

## Register Writes (from FUN_140002e30)

| Offset | Hex | Value | Purpose | Function |
|--------|-----|-------|---------|----------|
| 0x100  | 0x100 | 0x8 | Control register? | FUN_140002e30 |

**Note:** Found via scalar search. Assembly shows `MOV [RSI + 0x100], 0x8`. Decompiler shows `*(param_1 + 0x20) = 8`, suggesting structure offset.

## MMIO Base Address Storage

- MMIO base address stored at: `param_1 + 0xc8` (200 decimal)
- Access pattern: `*(longlong *)(param_1 + 200) + offset`

## Register Writes Found

| Offset | Value | Function | Notes |
|--------|-------|----------|-------|
| 0x100  | 0x8   | FUN_140002e30 | Control register - write 0x8 to start/enable |

**Note:** Found 50 instances of offset 0x100 in code, suggesting it's a key control register.

## Analysis Status

**Ghidra Analysis Completed:**
- ✅ Found 9 confirmed register offsets
- ✅ Identified 44+ functions using MMIO
- ✅ Found interrupt setup (IoConnectInterruptEx in FUN_140003d60)
- ✅ Traced MMIO base usage (112+ references to offset 0xc8)

**Still Missing:**
- ❌ Format/sample rate registers (not found as literals - may be calculated)
- ❌ Control register bit fields (need to analyze 0x100 register in detail)
- ❌ Hardware position register (0x0104 is placeholder, needs verification)
- ❌ Interrupt handler function (need to trace from IoConnectInterruptEx)

## Functions Using MMIO

From comprehensive analysis, 75+ functions use MMIO. Key functions:
- `FUN_140003d60` - MMIO mapping and initialization (reads: 0x0, 0x4, 0x8, 0x10, 0x14, 0x104, 0x10300, 0x10304)
- `FUN_140002e30` - Control register write (0x100 = 0x8)
- Many other functions access MMIO base + offsets

## Analysis Status

✅ **Completed:**
- Found MMIO base storage location (offset 0xc8 in device structure)
- Identified 8+ register offsets from initialization function
- Found control register write pattern
- Identified 75+ functions using MMIO

⏳ **In Progress:**
- Comprehensive register search (finding many offsets, need to filter for actual MMIO)
- Sample rate/format register discovery
- Interrupt handler analysis

## Next Steps

1. **Filter register search results** - Many offsets found, need to identify which are actual MMIO vs stack
2. **Find format/sample rate registers** - Search for where sample rate values (44100, 48000) are written
3. **Analyze interrupt handler** - Find function connected via `IoConnectInterruptEx`
4. **Find position register** - Search for counter/position operations
5. **Control register bit fields** - Analyze 0x100 register to understand bit meanings

## Baseline Comparison

Baseline at load: `notes/MMIO_BASELINE.md`. During playback (with `dump_on_trigger=1`): `notes/MMIO_during_playback_*.txt`.
