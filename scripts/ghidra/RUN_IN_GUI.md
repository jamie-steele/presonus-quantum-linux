# Running Ghidra Scripts in GUI

Since headless mode requires PyGhidra setup, run the scripts in the Ghidra GUI instead.

## Quick Steps

1. **Open Ghidra:**
   ```powershell
   cd C:\source\quantum\.git\presonus-quantum2626-linux\scripts
   .\ghidra_analyze_driver.ps1
   ```

2. **Open your project:**
   - File > Open Project
   - Navigate to: `%USERPROFILE%\ghidra_projects\Quantum2626_Driver`
   - Open `pae_quantum.sys`

3. **Run the script:**
   - Window > Python (or Window > Script Manager)
   - Click the folder icon to browse scripts
   - Navigate to: `C:\source\quantum\.git\presonus-quantum2626-linux\scripts\ghidra`
   - Select: `find_mmio_registers.py`
   - Click "Run Script"

4. **View results:**
   - Check the console output
   - Script will prompt to save results to JSON

## Alternative: Use Ghidra's Built-in Search

If scripts don't work, use Ghidra's built-in features:

1. **Search for Scalars:**
   - Search > For Scalars...
   - Search for: `0x100`, `0x104`, `0x200`, etc.
   - Double-click results to see context

2. **Find References:**
   - Symbol Tree > External Functions
   - Find `MmMapIoSpace`
   - Right-click > Show References

3. **Cross-References:**
   - Find a function (e.g., `FUN_140003d60`)
   - Right-click > Show References

## Expected Output

The script should output:
- Register offsets found
- Functions using each register
- Read vs write categorization
- JSON export option
