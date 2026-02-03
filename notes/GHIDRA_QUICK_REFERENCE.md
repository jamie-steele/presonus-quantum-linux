# Ghidra Quick Reference - Quantum 2626 Analysis

Quick reference for continuing the Ghidra analysis session.

## Key Addresses

- **MMIO Mapping Function:** `FUN_140003d60` at `0x140003d60`
- **MMIO Base Storage:** `param_1 + 0xc8` (200 decimal)
- **Register Write Function:** `FUN_140002e30` at `0x140002e30`

## How to Resume Analysis

1. **Open Ghidra:**
   ```powershell
   cd C:\source\quantum\.git\presonus-quantum2626-linux\scripts
   .\ghidra_analyze_driver.ps1
   ```

2. **Open Project:**
   - File > Open Project
   - Navigate to: `%USERPROFILE%\ghidra_projects\Quantum2626_Driver`
   - Open `pae_quantum.sys`

3. **Quick Navigation:**
   - Press `G` (Go to address)
   - Type: `140003d60` (MMIO mapping function)
   - Or: `140002e30` (Register write function)

## Useful Searches

### Find Register Offsets
1. Search > For Scalars...
2. Search for: `0x100`, `0x104`, `0x108`, `0x200`, `0x300`
3. Double-click results to see context

### Find Function References
1. Symbol Tree > Functions
2. Find function (e.g., `FUN_140002e30`)
3. Right-click > Show References

### Find MMIO Base Usage
1. In `FUN_140003d60`, find `param_1 + 200`
2. Right-click > Show References
3. This shows all uses of MMIO base

## Key Functions to Investigate

- `FUN_140003d60` - MMIO mapping and initialization
- `FUN_140002e30` - Register write at 0x100
- `FUN_14000d410` - Likely interrupt handler (from `IoConnectInterruptEx`)
- Functions called after initialization - may contain stream control

## Register Offsets to Search For

- `0x100` - Found (write in FUN_140002e30)
- `0x104` - Found (read in FUN_140003d60)
- `0x0`, `0x4`, `0x8`, `0x10`, `0x14` - Found (reads in FUN_140003d60)
- `0x10300`, `0x10304` - Found (reads in FUN_140003d60)
- `0x200`, `0x300`, `0x400` - Not yet found (search for these)

## Documentation Files

- `notes/GHIDRA_ANALYSIS_SESSION.md` - Full analysis notes
- `notes/REGISTER_GUESSES.md` - Register offset table
- `docs/GHIDRA_ANALYSIS_GUIDE.md` - Detailed analysis guide
- `docs/GHIDRA_QUICK_SEARCH.md` - Search patterns
