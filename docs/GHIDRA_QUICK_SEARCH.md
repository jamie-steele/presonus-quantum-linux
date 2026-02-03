# Ghidra Quick Search Guide - Finding MMIO Registers

## Immediate Next Steps

1. **Click "OK" on the PDB warning** - We can work without it
2. **Start searching for MMIO patterns**

## Search Commands (Press Ctrl+Shift+F or Search > For References)

### 1. Find MMIO Mapping Functions

**Search for:**
- `MmMapIoSpace` - Maps MMIO region
- `MmUnmapIoSpace` - Unmaps MMIO region

**What to do:**
1. Search > For References > To Address
2. Enter: `MmMapIoSpace` (or search in Symbol Tree)
3. Double-click the result to jump to where it's called
4. Look for the base address being stored (usually in device extension)

### 2. Find Register Read/Write Patterns

**Search for:**
- `READ_REGISTER_ULONG` - 32-bit register read
- `WRITE_REGISTER_ULONG` - 32-bit register write
- `READ_REGISTER_USHORT` - 16-bit register read
- `WRITE_REGISTER_USHORT` - 16-bit register write

**What to do:**
1. Search > For References > To Address
2. Enter one of the above functions
3. Follow the XRefs to see where registers are accessed
4. Note the offsets (e.g., `[base+0x100]`)

### 3. Search for Common Register Offsets

**Search for scalars:**
1. Search > For Scalars
2. Look for common offsets:
   - `0x0`, `0x4`, `0x8`, `0x10` (control registers)
   - `0x100`, `0x104`, `0x108` (buffer registers)
   - `0x200`, `0x204` (interrupt registers)
   - `0x1000`, `0x2000` (channel registers)

### 4. Find Interrupt Handling

**Search for:**
- `IoConnectInterrupt` - Connects interrupt handler
- `InterruptService` - Interrupt service routine

**What to do:**
1. Find the interrupt handler function
2. Look for register reads to check interrupt status
3. Look for register writes to acknowledge interrupts

### 5. Find Buffer/DMA Functions

**Search for:**
- `AllocateCommonBuffer` - DMA buffer allocation
- `GetScatterGatherList` - Scatter-gather list
- `MapTransfer` - Transfer mapping

**What to do:**
1. Find where buffers are allocated
2. Trace where buffer addresses are written to hardware
3. Note the register offset where address is written

## Quick Navigation Tips

- **F5** - Decompile function (shows pseudo-C code)
- **G** - Go to address
- **Ctrl+Shift+F** - Search for references
- **Ctrl+F** - Search in current view
- **X** - Show cross-references (XRefs)

## What We're Looking For

Document any register offsets you find in this format:

```
Offset 0x0000: Control Register
  - Write: Start/stop stream (bit 0 = start)
  - Read: Status bits
  - Found in: FUN_14002xxxx (StartStream function)

Offset 0x0100: Buffer Address Register
  - Write: DMA buffer physical address
  - Found in: FUN_14002xxxx (SetupBuffer function)
```

## Example Pattern to Look For

In the decompiler, you might see:
```c
void FUN_14002xxxx(longlong device_base) {
    // Read status
    status = READ_REGISTER_ULONG(device_base + 0x100);
    
    // Write control
    WRITE_REGISTER_ULONG(device_base + 0x104, 0x1);
}
```

The offsets `0x100` and `0x104` are what we need!
