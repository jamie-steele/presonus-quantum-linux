# Analysis Data Directory

This directory contains raw analysis data and output files from various reverse engineering and testing activities.

## Directory Structure

### `register_data/`
Register capture data from Linux driver testing:
- `init_writes.txt` - Initial register writes captured
- `init_writes_likely.txt` - Likely initialization sequence
- `stream_start_writes.txt` - Register writes when starting audio stream
- `stream_start_writes_detail.txt` - Detailed stream start sequence

### `dmesg_logs/`
Linux kernel logs from driver testing sessions:
- `dmesg_quantum_*.txt` - Kernel messages from driver loading and testing
- `dmesg_quantum_listen_*.txt` - Kernel messages during audio playback/capture
- Logs are timestamped (format: YYYYMMDD_HHMMSS)

### `ghidra_outputs/`
Output files from Ghidra analysis scripts:
- `all_registers.txt` - Complete register list from Ghidra
- `analysis_output.txt` - Ghidra script analysis results
- `function_analysis.txt` - Function-level analysis
- `interrupt_analysis.txt` - Interrupt handler analysis
- `mmio_registers_enhanced.txt` - Enhanced MMIO register findings
- Various other script outputs

## Usage

These files are used for:
1. **Reference** - Historical data for comparison with new findings
2. **Analysis** - Source data for identifying patterns and register mappings
3. **Validation** - Comparing Linux behavior with Windows driver behavior
4. **Documentation** - Supporting evidence for register mapping decisions

## Related Documentation

- `../REGISTER_GUESSES.md` - Consolidated register findings from this data
- `../GHIDRA_FINDINGS_SUMMARY.md` - Summary of Ghidra analysis results
- `docs/GHIDRA_GUIDE.md` - How to perform analysis to generate this data
