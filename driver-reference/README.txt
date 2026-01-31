# Quantum 2626 Driver Files Collection
Date: 2026-01-31 02:36
Windows Version: Microsoft Windows NT 10.0.26200.0

## Files Collected
- pae_quantum.sys - Main driver binary (~200KB)
- pae_quantum.inf - Driver installation file
- All files from driver directory

## Device Information
Device ID: PCI\VEN_1C67&DEV_0104&SUBSYS_01041C67
Driver Version: 1.37.0.0

## Next Steps
1. Copy this entire folder to your Linux machine
2. Use the driver files for reverse engineering:
   - strings pae_quantum.sys > quantum_strings.txt
   - Use Ghidra/IDA Pro for disassembly
3. Compare resources.txt with Linux lspci -vv output

## File Locations (Windows)
Driver: C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\
INF: C:\WINDOWS\INF\oem73.inf
