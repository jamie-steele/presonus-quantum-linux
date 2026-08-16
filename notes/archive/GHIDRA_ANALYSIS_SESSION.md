# Ghidra Analysis Session - PreSonus Quantum 2626 Driver

**Date:** 2026-02-03  
**Driver:** `pae_quantum.sys` (Version 1.37.0.0)  
**Tool:** Ghidra 12.0.2  
**Status:** Initial analysis complete, ready for deeper investigation

## Summary

Successfully loaded and analyzed the Windows driver in Ghidra. Identified MMIO mapping function and several register offsets. Found initial register reads during device initialization and at least one register write operation.

## Key Functions Identified

### FUN_140003d60 - Device Initialization & MMIO Mapping

**Purpose:** Main device initialization function that maps MMIO and sets up the device.

**Key Operations:**
1. **MMIO Mapping:**
   ```c
   puVar10 = MmMapIoSpace(*(undefined8 *)(lVar5 + 0x38), *(undefined4 *)(lVar5 + 0x30), 0);
   *(undefined4 **)(param_1 + 200) = puVar10;  // Store MMIO base at param_1 + 0xc8
   ```

2. **Initial Register Reads (after mapping):**
   - Offset `0x0`: Read into `param_1 + 0x4f0`
   - Offset `0x4`: Read into `param_1 + 0x4f4`
   - Offset `0x8`: Read into `param_1 + 0x4f8`
   - Offset `0x10`: Read into `param_1 + 0x4fc`
   - Offset `0x14`: Read into `param_1 + 0x500`
   - Offset `0x104`: Read into `param_1 + 0x1d8`
   - Offset `0x10300`: Read into `param_1 + 0x1d0`
   - Offset `0x10304`: Read into `param_1 + 0x1d4`

3. **Interrupt Setup:**
   - Calls `IoConnectInterruptEx` to connect interrupt handler
   - Interrupt handler likely at `FUN_14000d410` or similar

4. **Other Operations:**
   - Device interface registration
   - Buffer/DMA setup
   - Stream initialization

### FUN_140002e30 - Register Write Function

**Purpose:** Writes to MMIO register at offset 0x100.

**Key Operation:**
```assembly
MOV dword ptr [RSI + 0x100], 0x8
```

**Decompiled:**
```c
*(undefined4 *) (param_1 + 0x20) = 8;
```

**Note:** Offset discrepancy (0x100 in assembly vs 0x20 in decompiler) suggests `param_1` is a structure pointer, and the structure is at `RSI + 0xe0`.

## MMIO Base Address Storage

- **Location:** `param_1 + 0xc8` (200 decimal, 0xc8 hex)
- **Access Pattern:** `*(longlong *)(param_1 + 200) + offset`
- **Variable Name:** `puVar10` in `FUN_140003d60`

## Register Offsets Found

### Initialization Reads (from FUN_140003d60)

| Offset | Hex | Purpose | Stored At |
|--------|-----|---------|-----------|
| 0x0    | 0x0 | Version/ID? | param_1 + 0x4f0 |
| 0x4    | 0x4 | Status/Control | param_1 + 0x4f4 |
| 0x8    | 0x8 | Status/Control | param_1 + 0x4f8 |
| 0x10   | 0x10 | Status/Control | param_1 + 0x4fc |
| 0x14   | 0x14 | Status/Control | param_1 + 0x500 |
| 0x104  | 0x104 | Status/Control | param_1 + 0x1d8 |
| 0x10300 | 0x10300 | Buffer/Channel? | param_1 + 0x1d0 |
| 0x10304 | 0x10304 | Buffer/Channel? | param_1 + 0x1d4 |

### Register Writes (from FUN_140002e30)

| Offset | Hex | Value | Purpose |
|--------|-----|-------|---------|
| 0x100  | 0x100 | 0x8 | Control register? |

### Scalar Search Results

**0x100 (256 decimal):** Found 50 instances
- Many appear to be register offsets
- Pattern: `MOV [register + 0x100], value` (writes)
- Pattern: `MOV register, [base + 0x100]` (reads)

## Next Steps for Future Analysis

1. **Find More Register Writes:**
   - Search for other write patterns
   - Look for `WRITE_REGISTER_ULONG` if used
   - Search for direct memory writes to MMIO base

2. **Interrupt Handler Analysis:**
   - Find the interrupt handler function (connected via `IoConnectInterruptEx`)
   - Look for interrupt status register reads
   - Find interrupt acknowledge register writes

3. **Buffer/DMA Registers:**
   - Search for `AllocateCommonBuffer` or DMA functions
   - Find where buffer addresses are written to hardware
   - Look for buffer size/position registers

4. **Stream Control:**
   - Find start/stop functions
   - Look for format/sample rate registers
   - Find position registers

5. **Search for More Offsets:**
   - Use "Search for Scalars" for: `0x104`, `0x108`, `0x10c`, `0x200`, `0x300`
   - Check functions that use MMIO base (`param_1 + 200`)

6. **Cross-Reference Analysis:**
   - Follow XRefs from `FUN_140003d60` to find other functions using MMIO
   - Check where `FUN_140002e30` is called from
   - Trace the flow of MMIO base address through the code

## Search Tips for Ghidra

1. **Search for Scalars:** Best way to find register offsets
   - Search > For Scalars...
   - Search for: `0x100`, `0x104`, `0x200`, etc.

2. **Symbol Tree:** Find function references
   - Symbol Tree > Functions > Right-click > Show References

3. **Cross-References:** Follow data flow
   - Right-click variable > Show References
   - Look at XRefs panel

4. **Decompiler:** Press `F5` on any function to see pseudo-C code

## Files to Review

- `notes/REGISTER_GUESSES.md` - Register offset documentation
- `notes/MMIO_BASELINE.md` - Linux baseline MMIO dump
- `driver-reference/pae_quantum.inf` - Driver metadata
- `notes/DRIVER_ANALYSIS.md` - Initial driver analysis

## Notes

- PDB file not found, but analysis is still productive
- Driver uses direct memory writes rather than `WRITE_REGISTER_*` macros
- MMIO base is stored in device extension structure
- Large offsets (0x10300+) suggest per-channel or buffer-related registers
- Need to correlate with Linux MMIO baseline to confirm register purposes
