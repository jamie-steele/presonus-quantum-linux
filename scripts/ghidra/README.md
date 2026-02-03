# Ghidra Automation Scripts

Automated scripts to reverse engineer the PreSonus Quantum 2626 driver register map.

## Scripts

### 1. `find_mmio_registers.py`
**Purpose:** Find all MMIO register offsets automatically

**What it does:**
- Finds `MmMapIoSpace` call to locate MMIO base
- Traces all uses of MMIO base address
- Extracts register offsets from memory accesses
- Categorizes reads vs writes
- Generates a comprehensive register map report

**Usage:**
```bash
# In Ghidra GUI:
Window > Python > Run script > find_mmio_registers.py

# Or headless:
analyzeHeadless <project_path> <project_name> -process pae_quantum.sys -script find_mmio_registers.py
```

**Output:** Register map with offsets, access types, and function contexts

### 2. `find_buffer_registers.py`
**Purpose:** Find DMA buffer address registers

**What it does:**
- Finds `AllocateCommonBuffer` and related DMA functions
- Traces buffer address writes to MMIO
- Identifies buffer size/position registers

**Usage:** Same as above

### 3. `find_interrupt_registers.py`
**Purpose:** Find interrupt status and acknowledge registers

**What it does:**
- Finds interrupt handler functions (via `IoConnectInterruptEx`)
- Analyzes interrupt handlers for register reads/writes
- Identifies interrupt status registers (read to check interrupt)
- Identifies interrupt acknowledge registers (write to clear interrupt)

**Usage:** Same as above

## Quick Start

### Option 1: Run in Ghidra GUI

1. Open Ghidra and load your project
2. Open `pae_quantum.sys`
3. Window > Python
4. File > Run Script
5. Select one of the scripts
6. Review output in console

### Option 2: Run Headless (Windows)

```powershell
# Set paths
$ghidra = "C:\Users\Jamie\Ghidra\ghidra_12.0.2_PUBLIC"
$project = "$env:USERPROFILE\ghidra_projects"
$projectName = "Quantum2626_Driver"

# Run analysis
& "$ghidra\support\analyzeHeadless" `
    $project `
    $projectName `
    -process pae_quantum.sys `
    -scriptPath "C:\source\quantum\.git\presonus-quantum2626-linux\scripts\ghidra" `
    -postScript find_mmio_registers.py
```

### Option 3: Run All Scripts

```powershell
cd C:\source\quantum\.git\presonus-quantum2626-linux\scripts\ghidra
.\run_all_analysis.ps1
```

## Expected Results

After running the scripts, you should have:

1. **Complete register map:**
   - All register offsets (reads and writes)
   - Functions that access each register
   - Values written to registers
   - Context for each access

2. **Buffer registers:**
   - DMA buffer address register offsets
   - Buffer size registers
   - Buffer position registers

3. **Interrupt registers:**
   - Interrupt status register offset
   - Interrupt acknowledge register offset
   - Interrupt enable/disable registers

## Output Files

Scripts can export results to JSON files for further processing:
- `register_map.json` - Complete register map
- `buffer_registers.json` - Buffer-related registers
- `interrupt_registers.json` - Interrupt-related registers

## Troubleshooting

**Script doesn't find registers:**
- Make sure the project has been analyzed (Analysis > Auto Analyze)
- Check that `pae_quantum.sys` is the active program
- Verify Ghidra version compatibility (tested with 12.0.2)

**Headless mode issues:**
- Ensure Java 21+ is in PATH
- Check project path is correct
- Verify script paths are absolute or relative to script directory

## Next Steps

After running these scripts:
1. Review the register map
2. Correlate with Linux MMIO baseline (`notes/MMIO_BASELINE.md`)
3. Test register accesses on Linux using module parameters
4. Implement driver functions based on discovered registers
