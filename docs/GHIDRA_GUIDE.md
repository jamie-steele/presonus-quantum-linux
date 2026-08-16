# Ghidra Analysis Guide - PreSonus Quantum 2626 Driver

**Target:** `pae_quantum.sys` (Windows kernel driver)  
**Goal:** Reverse engineer MMIO register map and hardware control flow

## Table of Contents
- [Getting Started](#getting-started)
- [Quick Search Patterns](#quick-search-patterns)
- [Detailed Analysis Workflow](#detailed-analysis-workflow)
- [Key Functions to Find](#key-functions-to-find)
- [Quick Reference](#quick-reference)
- [Analysis Findings](#analysis-findings)

---

## Getting Started

### 1. Launch Ghidra

```powershell
.\scripts\ghidra_analyze_driver.ps1
```

### 2. Create/Open Project

**New Project:**
- File > New Project
- Choose "Non-Shared Project"
- Name: `Quantum2626_Driver`
- Location: `%USERPROFILE%\ghidra_projects`

**Resume Existing:**
- File > Open Project
- Navigate to: `%USERPROFILE%\ghidra_projects\Quantum2626_Driver`
- Open `pae_quantum.sys`

### 3. Import Driver (First Time Only)

- File > Import File
- Select: `pae_quantum.sys`
- Language: `x86:LE:64:default:windows` (or let Ghidra auto-detect)
- Format: `PE` (Portable Executable)
- When prompted, click "Yes" to analyze
- Use default analysis options
- **Click "OK" on PDB warning** - We can work without it

---

## Quick Search Patterns

### Find MMIO Mapping Functions

**Search for:** (Ctrl+Shift+F or Search > For References)
- `MmMapIoSpace` - Maps MMIO region
- `MmUnmapIoSpace` - Unmaps MMIO region

**What to do:**
1. Search > For References > To Address
2. Enter: `MmMapIoSpace`
3. Double-click result to jump to where it's called
4. Look for base address being stored (usually in device extension)

### Find Register Read/Write Functions

**Search for:**
- `READ_REGISTER_ULONG` - 32-bit register read
- `WRITE_REGISTER_ULONG` - 32-bit register write
- `READ_REGISTER_USHORT` - 16-bit register read
- `WRITE_REGISTER_USHORT` - 16-bit register write

**What to do:**
1. Search > For References > To Address
2. Enter one of the above functions
3. Follow XRefs to see where registers are accessed
4. Note the offsets (e.g., `[base+0x100]`)

### Search for Common Register Offsets

**Search for scalars:** (Search > For Scalars)
- `0x0`, `0x4`, `0x8`, `0x10` (control registers)
- `0x100`, `0x104`, `0x108` (buffer registers)
- `0x200`, `0x204` (interrupt registers)
- `0x1000`, `0x2000` (channel registers)

### Find Interrupt Handling

**Search for:**
- `IoConnectInterrupt` - Connects interrupt handler
- `InterruptService` - Interrupt service routine

### Find Buffer/DMA Functions

**Search for:**
- `AllocateCommonBuffer` - DMA buffer allocation
- `GetScatterGatherList` - Scatter-gather list
- `MapTransfer` - Transfer mapping

---

## Detailed Analysis Workflow

### Step 1: Find Entry Points

1. Go to **Symbol Tree > Functions**
2. Look for:
   - `DriverEntry` - Main driver entry point
   - `AddDevice` - Device addition handler
   - `Dispatch` functions - IRP handlers

### Step 2: Trace MMIO Initialization

1. Find where BAR is mapped (search for `MmMapIoSpace`)
2. Follow the code to see where base address is stored
3. Look for register access patterns from that base

### Step 3: Find Register Offsets

**Method 1 - String Search:**
- Search > For Strings
- Look for hex patterns like "0x0000", "0x0100", etc.

**Method 2 - Scalar Search:**
- Search > For Scalars
- Look for common offsets: 0x0, 0x4, 0x8, 0x10, 0x100, 0x200, etc.

**Method 3 - Cross-Reference:**
- Find a known function (e.g., interrupt handler)
- Use XRefs to find where it's called
- Trace back to register access

### Step 4: Document Register Map

Document findings in this format:

```
Offset 0x0000: Control Register
  - Write: Start/stop stream (bit 0 = start)
  - Read: Status bits
  - Found in: FUN_14002xxxx (StartStream function)
```

### Step 5: Find Buffer Registers

1. Search for DMA buffer allocation
2. Find where buffer address is written to hardware
3. Document buffer address register offset
4. Find buffer size/position registers

---

## Key Functions to Find

### 1. MMIO Register Access

**What to look for:**
- Base address from BAR0 (usually stored in device extension)
- Register offsets (0x0000, 0x0004, 0x0008, etc.)
- Read/write patterns around these offsets

**Example pattern:**
```c
// In Ghidra decompiler (F5), you might see:
void FUN_14002xxxx(longlong device_base) {
    // Read status
    status = READ_REGISTER_ULONG(device_base + 0x100);
    
    // Write control
    WRITE_REGISTER_ULONG(device_base + 0x104, 0x1);
}
```

### 2. Buffer Management (DMA)

**What to look for:**
- Buffer address registers (where DMA buffer address is written)
- Buffer size registers
- Buffer position/status registers

### 3. Interrupt Handling

**What to look for:**
- Interrupt status register (read to check interrupt source)
- Interrupt acknowledge register (write to clear interrupt)
- Interrupt enable/disable registers

### 4. Audio Stream Control

**Search for:**
- Functions with "Start", "Stop", "Pause", "Resume" in names
- Format-related functions (sample rate, bit depth, channels)
- Position/status queries

**What to look for:**
- Start/stop control register (bit to enable/disable stream)
- Format register (sample rate, bit depth encoding)
- Position register (current playback/capture position)
- Status register (underrun, overrun, etc.)

### 5. PCI Configuration

**What to look for:**
- Which BAR is used (BAR0, BAR1, etc.)
- BAR size and type (MMIO vs I/O port)
- Device-specific PCI config registers

---

## Quick Reference

### Key Addresses (Project-Specific)

- **MMIO Mapping Function:** `FUN_140003d60` at `0x140003d60`
- **MMIO Base Storage:** `param_1 + 0xc8` (200 decimal)
- **Register Write Function:** `FUN_140002e30` at `0x140002e30`

### Quick Navigation (Press `G` for Go to address)

- `140003d60` - MMIO mapping function
- `140002e30` - Register write function
- `14000d410` - Likely interrupt handler

### Useful Keyboard Shortcuts

- **F5** - Decompile function (shows pseudo-C code)
- **G** - Go to address
- **Ctrl+Shift+F** - Search for references
- **Ctrl+F** - Search in current view
- **X** - Show cross-references (XRefs)

### Find MMIO Base Usage

1. In `FUN_140003d60`, find `param_1 + 200` (0xc8)
2. Right-click > Show References
3. This shows all uses of MMIO base (112+ references)

---

## Analysis Findings

### ✅ Confirmed Register Offsets

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

### 📊 Analysis Statistics

- **MMIO Base Storage:** 112+ references to offset 0xc8
- **Functions Using MMIO:** 44+ functions identified
- **Interrupt Handler:** IoConnectInterruptEx called from FUN_140003d60

### ❓ Missing Registers (Priority Search)

**Priority 1: Format/Sample Rate Registers**
- Sample Rate Register: Which register sets 44100, 48000, 96000, 192000 Hz?
- Bit Depth Register: Which register sets 16, 24, 32-bit?
- Channel Count Register: Which register sets mono/stereo/multi-channel?

**Priority 2: Control Register Details**
- Control Register Bit Fields: What do the bits in 0x100 mean?
  - Currently we write 0x8, but what does each bit do?
  - Are there separate start/stop bits?

**Priority 3: Position Register**
- Hardware Position: Which register contains playback/capture position?
  - Currently using 0x0104 as placeholder
  - Need to verify actual position register

**Priority 4: Interrupt Handling**
- Interrupt Handler Function: Find the actual handler
- Interrupt Status Register: Verify 0x0004 is interrupt status
- Interrupt Acknowledge: How to properly acknowledge interrupts?

---

## Common Patterns

### Register Read Pattern:
```assembly
mov eax, [device_base]      ; Load base address
mov edx, [eax+offset]       ; Read register
```

### Register Write Pattern:
```assembly
mov eax, [device_base]      ; Load base address
mov [eax+offset], value     ; Write register
```

### Interrupt Handler Pattern:
```assembly
; Read interrupt status
mov eax, [device_base+0x100]
test eax, 0x01              ; Check bit 0
jz no_interrupt
; Clear interrupt
mov [device_base+0x104], 0x01
```

---

## Analysis Tips

1. **Use Decompiler:** Press F5 to show pseudo-C code (easier to read)
2. **Rename Functions:** Right-click > Rename to give meaningful names
3. **Add Comments:** Right-click > Set Comment to document findings
4. **Create Structures:** Define structures for device extension, register map
5. **Cross-Reference:** Use XRefs (Ctrl+Shift+F) to find all uses of a function/register
6. **Filter Results:** Many offsets found may be stack operations, not MMIO - focus on known MMIO functions

### Analysis Challenges

1. **Indirect Addressing:** MMIO base loaded into register, then offsets added
   - Pattern: `MOV RAX, [RCX + 0xc8]` then `MOV EDX, [RAX + 0x100]`
   - Makes automated pattern matching difficult
2. **Sample Rate Values:** Not found as literals - may be calculated or in lookup tables
3. **Register Offsets:** Many found but need filtering (stack vs MMIO)

---

## Expected Findings

Based on typical audio drivers:

- **Control Registers:** 0x0000-0x00FF (stream control, format, etc.)
- **Buffer Registers:** 0x0100-0x01FF (DMA buffer address, size, position)
- **Interrupt Registers:** 0x0200-0x02FF (status, acknowledge, enable)
- **Channel Registers:** 0x1000+ (per-channel control, if multi-channel)

---

## Next Steps

After finding register offsets:

1. Document in `notes/REGISTER_GUESSES.md`
2. Test on Linux using `snd-quantum2626` module
3. Compare with Windows behavior (see `docs/WINDOWS_PROFILING.md`)
4. Iterate and refine based on testing results

## Documentation Files

- **This Guide:** `docs/GHIDRA_GUIDE.md` - Complete analysis guide
- **Register Map:** `notes/REGISTER_GUESSES.md` - Register offset table
- **Session Notes:** `notes/GHIDRA_ANALYSIS_SESSION.md` - Detailed session logs
- **Findings:** `notes/GHIDRA_FINDINGS_SUMMARY.md` - Summary of confirmed findings
- **Analysis Outputs:** `notes/analysis/ghidra_outputs/` - Script output files

## Resources

- [Ghidra Documentation](https://ghidra-sre.org/)
- [Windows Driver Architecture](https://docs.microsoft.com/en-us/windows-hardware/drivers/)
- [PCI/PCIe MMIO](https://wiki.osdev.org/PCI)
