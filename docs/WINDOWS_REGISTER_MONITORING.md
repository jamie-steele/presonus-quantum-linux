# Windows Register Monitoring - Using Working Driver

**Goal:** Monitor what registers the working Windows driver (`pae_quantum.sys`) accesses during audio playback/capture to build the register map.

## Why This Approach

Since Windows has a **working driver**, we can:
1. Monitor its MMIO register access in real-time
2. See exactly which registers it reads/writes
3. Capture the sequence of operations
4. Build the register map from actual working behavior

This is much more effective than blind reverse engineering!

## Tools Available

### 1. Windows Performance Recorder (WPR) - Recommended

**Built into Windows**, can trace kernel driver I/O operations.

**Usage:**
```powershell
# Run as Administrator
cd scripts
.\windows_capture_register_activity.ps1 -OutputFile quantum_trace.etl -DurationSeconds 30
```

**While trace is running:**
- Play audio on Quantum 2626
- The trace captures all driver I/O activity

**Analyze results:**
- Open `quantum_trace.etl` in Windows Performance Analyzer (WPA)
- Look for I/O operations, memory access patterns
- Filter by `pae_quantum` driver

### 2. WinDbg (Advanced)

**Kernel debugging** - Can set breakpoints on MMIO access.

**Setup:**
- Requires kernel debugging configuration
- Can hook MMIO read/write operations
- More complex but very powerful

### 3. Process Monitor (ProcMon)

**Shows driver file/registry activity** - May reveal register values in registry.

**Usage:**
1. Download from Microsoft Sysinternals
2. Filter by `pae_quantum.sys` process
3. Look for registry writes (may contain register values)
4. Look for file I/O patterns

### 4. Custom Monitoring Driver (Most Direct)

**Create a filter driver** that sits between the hardware and `pae_quantum.sys` to log all MMIO access.

**Advantages:**
- Direct MMIO access logging
- Can capture exact register offsets and values
- Can log read/write operations separately

## Recommended Workflow

### Step 1: Baseline Capture (Idle)

```powershell
# Capture what registers are accessed when device is idle
.\windows_capture_register_activity.ps1 -OutputFile baseline.etl -DurationSeconds 5
```

### Step 2: Playback Capture

```powershell
# Capture during audio playback
.\windows_capture_register_activity.ps1 -OutputFile playback.etl -DurationSeconds 10 -StartPlayback
```

### Step 3: Compare

- Compare baseline vs playback traces
- Identify which registers change
- Document register offsets and their functions

### Step 4: Test Hypotheses

Based on findings, test specific registers:
- Which register sets sample rate?
- Which register starts playback?
- Which register has buffer address?

## Scripts Provided

1. **`windows_monitor_mmio.ps1`** - Overview and tool detection
2. **`windows_capture_register_activity.ps1`** - Automated WPR capture

## Expected Output

From the traces, we should be able to identify:

- **Buffer Registers:** Where DMA buffer addresses are written
- **Format Registers:** Sample rate, bit depth, channel configuration
- **Control Registers:** Start/stop bits, enable flags
- **Status Registers:** Position, interrupt status
- **Sequence:** Order of operations (prepare → start → stop)

## Next Steps After Capture

1. **Analyze traces** in WPA to extract register patterns
2. **Document findings** in `notes/REGISTER_GUESSES.md`
3. **Implement in Linux driver** using discovered register map
4. **Test and refine** using Linux feedback loop tools

## Alternative: Direct MMIO Monitoring

If WPR doesn't capture MMIO directly, we may need:
- A custom kernel filter driver
- Or use WinDbg with MMIO breakpoints
- Or use a hardware-level PCIe analyzer (expensive)

## Feedback Loop

Once we have register patterns from Windows:
1. Implement in Linux driver
2. Test with Linux feedback loop tools
3. Compare behavior with Windows
4. Refine until audio works

This gives us the best of both worlds:
- **Windows:** Working driver shows us what to do
- **Linux:** Feedback loop helps us get it right
