# PreSonus Quantum 2626 - Windows Driver Analysis

**Date:** 2026-01-31  
**Driver Extraction:** Complete

## Driver Information

### Driver File
- **Name:** `pae_quantum.sys`
- **Company:** PreSonus
- **Product:** PAE Quantum Driver
- **Version:** 1.37.0.0
- **Size:** ~200 KB

### Driver Locations (Windows)
1. `C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\pae_quantum.sys`
   - Size: 203,408 bytes (198.64 KB)
   - Modified: 2025-09-12
   - Version: 1.37.0.0

2. `C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_60e367fe3befdd09\pae_quantum.sys`
   - Size: 203,904 bytes (199.12 KB)
   - Modified: 2024-12-18
   - Version: 1.37.0.0

### INF File
- **Location:** `C:\WINDOWS\INF\oem73.inf`
- **Driver Version:** 01/31/2023, 1.37.0.0
- **Device ID:** `PCI\VEN_1C67&DEV_0104&SUBSYS_01041C67`
- **Device Name:** "PreSonus Quantum 2626"

### Device Details
- **Vendor ID:** 0x1C67 (PreSonus)
- **Device ID:** 0x0104
- **Subsystem Vendor:** 0x1C67
- **Subsystem Device:** 0x0104
- **Class:** MEDIA (Audio)

## Driver Architecture

The driver uses Windows Kernel Streaming (KS) and WDM Audio:
- Includes: `ks.inf`, `wdmaudio.inf`
- Uses: `mssysfx.CopyFilesAndRegister` (Microsoft System Effects)

## Extracted Strings

The driver binary contains obfuscated/encoded function names and identifiers. Some interesting patterns:
- Function-like names: `HINIT`, `TLTL`, `VWAWH`, `ATAVAWH`
- Control flow: `taff`, `toff` (possibly timing-related)
- Register-like patterns: `ffff`, `ffffff`, `fffff`

**Note:** The strings appear to be obfuscated, which is common in proprietary audio drivers to protect intellectual property.

## Next Steps for Linux Driver Development

### 1. Copy Driver Files to Linux
```bash
# Copy the driver file from Windows to Linux
# Use the newer version (2025-09-12) for analysis
scp user@windows:/path/to/pae_quantum.sys ./
```

### 2. Extract All Strings
```bash
strings pae_quantum.sys > quantum_strings.txt
# Look for register names, function names, protocol identifiers
```

### 3. Disassemble (if PE/COFF format)
```bash
# Windows drivers are PE format, may need objdump or specialized tools
objdump -d pae_quantum.sys > quantum_disassembly.txt
# Or use readelf if it's a different format
```

### 4. Binary Analysis Tools
- **Ghidra** (free): Full reverse engineering, decompilation
- **IDA Pro** (commercial): Industry standard disassembler
- **radare2** (free): Command-line reverse engineering framework
- **Binary Ninja** (commercial): Modern reverse engineering platform

### 5. Key Areas to Analyze
1. **PCI Configuration Space Access** - How the driver reads/writes PCI registers
2. **Memory Mapped I/O (MMIO)** - BAR access patterns
3. **Interrupt Handling** - IRQ registration and handling
4. **Audio Stream Management** - PCM buffer management
5. **Control Interface** - Register maps for audio control

### 6. Compare with Linux PCI Info
From `lspci -vv` on Linux:
- **BAR 0:** Memory at 0x64000000 (1 MiB)
- Compare Windows driver's MMIO patterns with Linux BAR access

## Reverse Engineering Notes

The driver is relatively small (~200KB), suggesting:
- May be a wrapper around a firmware/FPGA
- Core functionality might be in hardware/firmware
- Driver primarily handles PCI communication and audio streaming

The obfuscated strings suggest the driver uses:
- Custom register naming conventions
- Possibly encrypted or encoded function names
- Standard Windows audio stack (KS/WDM)

## Resources

- **INF File:** `C:\WINDOWS\INF\oem73.inf` (contains device installation details)
- **Driver File:** `pae_quantum.sys` (main driver binary)
- **Full extraction output:** `notes/driver_extraction.txt`

## Collected Files (Ready for Linux)

**Location on Windows Desktop:** `C:\Users\<USERNAME>\Desktop\Quantum2626_DriverFiles\`

All driver files have been collected and are ready to transfer to Linux:
- `pae_quantum.sys` (203,408 bytes) - Main driver binary
- `pae_quantum.inf` (3,326 bytes) - Driver installation file
- `pae_quantum.cat` (12,439 bytes) - Driver catalog/signature file
- `pae_quantum.PNF` (10,644 bytes) - Precompiled INF file
- `resources.txt` - Device resource information (IRQ, memory)
- `services.txt` - Service information
- `README.txt` - Collection summary

**To transfer to Linux:**
1. Copy the entire `Quantum2626_DriverFiles` folder to Linux (USB, network share, or scp)
2. On Linux, extract strings: `strings pae_quantum.sys > quantum_strings.txt`
3. Use reverse engineering tools (Ghidra, IDA Pro, radare2) to analyze the binary

## Related Devices

The INF file also lists other Quantum devices:
- Quantum (DEV_0101)
- Quantum 2 (DEV_0102)
- Quantum 4848 (DEV_0103)
- **Quantum 2626 (DEV_0104)** ← This device
- Quantum Mobile (DEV_0105)

All use the same driver (`pae_quantum.sys`), suggesting similar hardware architecture.
