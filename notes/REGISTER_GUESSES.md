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

## Next Steps

1. Search for `WRITE_REGISTER_ULONG` to find register writes
2. Find interrupt handler (connected via `IoConnectInterruptEx`) to find interrupt status registers
3. Search for buffer/DMA functions to find buffer address registers
4. Look for stream start/stop functions to find control registers

## Baseline Comparison

Baseline at load: `notes/MMIO_BASELINE.md`. During playback (with `dump_on_trigger=1`): `notes/MMIO_during_playback_*.txt`.
