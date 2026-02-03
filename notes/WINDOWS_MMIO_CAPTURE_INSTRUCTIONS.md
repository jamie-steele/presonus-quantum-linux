# Windows MMIO Capture Instructions

**Device Found:** PreSonus Quantum 2626 (PCI\VEN_1C67&DEV_0104)  
**Driver:** PreSonus Quantum 2626 v1.37.0.0  
**Service:** pae_quantum (running)

## Quick Start - Capture Register Activity

### Option 1: Using Windows Performance Recorder (WPR) - Recommended

**Run PowerShell as Administrator**, then:

```powershell
cd C:\source\quantum\.git\presonus-quantum2626-linux\scripts

# Capture baseline (idle)
.\windows_capture_register_activity.ps1 -OutputFile quantum_baseline.etl -DurationSeconds 5

# Capture during playback (play audio manually)
.\windows_capture_register_activity.ps1 -OutputFile quantum_playback.etl -DurationSeconds 10
```

**Or manually:**
```powershell
# Start trace
wpr -start GeneralProfile

# Play audio on Quantum 2626 (use any audio player)
# Wait 10-30 seconds

# Stop trace
wpr -stop quantum_trace.etl
```

### Option 2: Manual WPR Commands

```powershell
# As Administrator
wpr -start GeneralProfile -filemode
# Now play audio...
wpr -stop quantum_trace.etl
```

## Analyzing the Trace

1. **Open Windows Performance Analyzer (WPA):**
   - Search for "wpa.exe" in Start menu
   - Or: `C:\Program Files (x86)\Windows Kits\10\Windows Performance Toolkit\wpa.exe`

2. **Load the trace:**
   - File → Open → Select `quantum_trace.etl`

3. **Look for:**
   - I/O operations
   - Driver activity (filter by `pae_quantum`)
   - Memory access patterns
   - MMIO read/write operations

## What to Look For

- **Register offsets** that are accessed
- **Values** written to registers
- **Sequence** of operations (prepare → start → stop)
- **Differences** between baseline and playback

## Alternative: Process Monitor

If WPR doesn't show MMIO directly:

1. Download Process Monitor from Sysinternals
2. Filter by process: `pae_quantum` or service name
3. Look for:
   - Registry writes (may contain register values)
   - File I/O patterns
   - Device I/O control operations

## Next Steps After Capture

1. Document findings in `notes/REGISTER_GUESSES.md`
2. Implement discovered registers in Linux driver
3. Test with Linux feedback loop tools
4. Compare behavior with Windows

## Current Device Status

✅ Device detected: PCI\VEN_1C67&DEV_0104  
✅ Driver loaded: PreSonus Quantum 2626 v1.37.0.0  
✅ Service running: PreSonus Hardware Access Service  
✅ Ready for tracing
