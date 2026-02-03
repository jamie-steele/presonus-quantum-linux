# Ghidra Analysis Guide - PreSonus Quantum 2626 Driver

**Target:** `pae_quantum.sys` (Windows kernel driver)  
**Goal:** Reverse engineer MMIO register map and hardware control flow

## Getting Started

1. **Launch Ghidra:**
   ```powershell
   .\scripts\ghidra_analyze_driver.ps1
   ```

2. **Create Project:**
   - File > New Project
   - Choose "Non-Shared Project"
   - Name: `Quantum2626_Driver`
   - Location: `%USERPROFILE%\ghidra_projects`

3. **Import Driver:**
   - File > Import File
   - Select: `pae_quantum.sys`
   - Language: `x86:LE:64:default:windows` (or let Ghidra auto-detect)
   - Format: `PE` (Portable Executable)

4. **Analyze:**
   - When prompted, click "Yes" to analyze
   - Use default analysis options (or customize)
   - Wait for analysis to complete

## Key Functions to Find

### 1. MMIO Register Access

**Search for:**
- `MmMapIoSpace` - Maps MMIO region
- `MmUnmapIoSpace` - Unmaps MMIO region
- `READ_REGISTER_ULONG` / `WRITE_REGISTER_ULONG` - 32-bit register access
- `READ_REGISTER_USHORT` / `WRITE_REGISTER_USHORT` - 16-bit register access

**What to look for:**
- Base address from BAR0 (usually stored in device extension)
- Register offsets (0x0000, 0x0004, 0x0008, etc.)
- Read/write patterns around these offsets

**Example pattern:**
```c
// In Ghidra, you might see:
mov eax, [rbx+0x10]        // Load base address
mov edx, [rax+0x100]       // Read register at offset 0x100
```

### 2. Buffer Management (DMA)

**Search for:**
- `AllocateCommonBuffer` - Allocates DMA buffer
- `GetScatterGatherList` - Gets scatter-gather list
- `MapTransfer` - Maps transfer buffer

**What to look for:**
- Buffer address registers (where DMA buffer address is written)
- Buffer size registers
- Buffer position/status registers

### 3. Interrupt Handling

**Search for:**
- `IoConnectInterrupt` - Connects interrupt handler
- `InterruptService` - Interrupt service routine
- `IoRequestDpc` - Deferred procedure call

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

**Search for:**
- `IoReadConfig*` / `IoWriteConfig*` - PCI config space access
- BAR reading/writing

**What to look for:**
- Which BAR is used (BAR0, BAR1, etc.)
- BAR size and type (MMIO vs I/O port)
- Device-specific PCI config registers

## Analysis Workflow

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

1. **Method 1 - String Search:**
   - Search > For Strings
   - Look for hex patterns like "0x0000", "0x0100", etc.

2. **Method 2 - Scalar Search:**
   - Search > For Scalars
   - Look for common offsets: 0x0, 0x4, 0x8, 0x10, 0x100, 0x200, etc.

3. **Method 3 - Cross-Reference:**
   - Find a known function (e.g., interrupt handler)
   - Use XRefs to find where it's called
   - Trace back to register access

### Step 4: Document Register Map

Create a document with:
- Register offset
- Read/Write access
- Function where it's used
- Likely purpose (based on context)

**Example:**
```
Offset 0x0000: Control Register
  - Write: Start/stop stream
  - Read: Status bits
  - Found in: StartStream() function
```

### Step 5: Find Buffer Registers

1. Search for DMA buffer allocation
2. Find where buffer address is written to hardware
3. Document buffer address register offset
4. Find buffer size/position registers

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

## Tips

1. **Use Decompiler:** Ghidra's decompiler (F5) shows pseudo-C code, easier to read
2. **Rename Functions:** Right-click > Rename to give meaningful names
3. **Add Comments:** Right-click > Set Comment to document findings
4. **Create Structures:** Define structures for device extension, register map
5. **Cross-Reference:** Use XRefs (Ctrl+Shift+F) to find all uses of a function/register

## Expected Findings

Based on typical audio drivers, you should find:

- **Control Registers:** 0x0000-0x00FF (stream control, format, etc.)
- **Buffer Registers:** 0x0100-0x01FF (DMA buffer address, size, position)
- **Interrupt Registers:** 0x0200-0x02FF (status, acknowledge, enable)
- **Channel Registers:** 0x1000+ (per-channel control, if multi-channel)

## Next Steps

After finding register offsets:

1. Document in `notes/REGISTER_GUESSES.md`
2. Test on Linux using `snd-quantum2626` module parameters
3. Compare with Windows behavior
4. Iterate and refine

## Resources

- [Ghidra Documentation](https://ghidra-sre.org/)
- [Windows Driver Architecture](https://docs.microsoft.com/en-us/windows-hardware/drivers/)
- [PCI/PCIe MMIO](https://wiki.osdev.org/PCI)
