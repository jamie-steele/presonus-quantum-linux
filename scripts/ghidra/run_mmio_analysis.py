#!/usr/bin/env python3
"""
Standalone PyGhidra script to find MMIO registers
Can be run headlessly with: python run_mmio_analysis.py
"""

import os
import sys
import json
from pathlib import Path

# Set Ghidra path before importing pyghidra
ghidra_path = os.environ.get('GHIDRA_INSTALL_DIR', r'C:\Users\Jamie\Ghidra\ghidra_12.0.2_PUBLIC')
if not os.path.exists(ghidra_path):
    print(f"ERROR: Ghidra not found at {ghidra_path}")
    print("Set GHIDRA_INSTALL_DIR environment variable or update this script")
    sys.exit(1)

os.environ['GHIDRA_INSTALL_DIR'] = ghidra_path

# Import PyGhidra
try:
    from pyghidra import *
    from ghidra.program.model.address import Address
    from ghidra.program.model.listing import Instruction, InstructionIterator
    from ghidra.program.model.scalar import Scalar
    from ghidra.util.task import ConsoleTaskMonitor
except ImportError as e:
    print(f"ERROR: Failed to import PyGhidra: {e}")
    print("Make sure PyGhidra is installed: pip install pyghidra")
    sys.exit(1)

# Driver file path
driver_file = r'C:\Users\Jamie\Desktop\Quantum2626_DriverFiles\pae_quantum.sys'
if not os.path.exists(driver_file):
    print(f"ERROR: Driver file not found: {driver_file}")
    sys.exit(1)

# Results storage
registers_read = {}
registers_written = {}
mmio_base_vars = set()
functions_using_mmio = set()

def get_function_name(address):
    """Get function name containing the given address"""
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

def find_mmio_base():
    """Find where MmMapIoSpace is called and trace the MMIO base address"""
    print("=== Finding MMIO Base Address ===")
    
    # Find MmMapIoSpace symbol
    symbol_table = currentProgram.getSymbolTable()
    mmio_symbol = None
    
    for symbol in symbol_table.getExternalSymbols():
        if symbol.getName() == "MmMapIoSpace":
            mmio_symbol = symbol
            break
    
    if not mmio_symbol:
        print("  WARNING: MmMapIoSpace not found in symbol table")
        return None
    
    # Find references to MmMapIoSpace
    refs = getReferencesTo(mmio_symbol.getAddress())
    print(f"  Found {refs.size()} references to MmMapIoSpace")
    
    for ref in refs:
        from_addr = ref.getFromAddress()
        func = getFunctionContaining(from_addr)
        func_name = func.getName() if func else "UNKNOWN"
        print(f"    Called from: {func_name} at {from_addr}")
        functions_using_mmio.add(func_name)
    
    return mmio_symbol

def extract_register_offsets():
    """Extract register offsets from memory operations"""
    print("\n=== Extracting Register Offsets ===")
    
    listing = currentProgram.getListing()
    monitor = ConsoleTaskMonitor()
    
    inst_iter = listing.getInstructions(True)
    count = 0
    found_offsets = set()
    
    # Common register offset patterns
    interesting_offsets = [
        0x0, 0x4, 0x8, 0x10, 0x14, 0x18, 0x1c, 0x20,
        0x100, 0x104, 0x108, 0x10c, 0x110, 0x114,
        0x200, 0x204, 0x208, 0x20c,
        0x300, 0x400, 0x500,
        0x1000, 0x2000, 0x3000,
        0x10300, 0x10304, 0x10308
    ]
    
    for inst in inst_iter:
        if monitor.isCancelled():
            break
        
        count += 1
        if count % 10000 == 0:
            print(f"  Processed {count} instructions...")
        
        mnemonic = inst.getMnemonicString()
        
        # Look for memory operations
        if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST"]:
            ops = inst.getOperands()
            
            for i, op in enumerate(ops):
                if op and op.isScalar():
                    scalar = op.getScalar()
                    offset = scalar.getUnsignedValue()
                    
                    # Check if it's a reasonable MMIO offset
                    if 0 <= offset <= 0x100000:
                        found_offsets.add(offset)
                        
                        # Determine if read or write
                        is_write = mnemonic in ["MOV", "OR", "AND", "XOR"] and i == 0
                        is_read = mnemonic in ["MOV", "CMP", "TEST"] and i == 1
                        
                        addr = inst.getAddress()
                        func_name = get_function_name(addr)
                        
                        if is_write:
                            if offset not in registers_written:
                                registers_written[offset] = []
                            registers_written[offset].append({
                                'address': str(addr),
                                'function': func_name,
                                'instruction': str(inst)
                            })
                        elif is_read:
                            if offset not in registers_read:
                                registers_read[offset] = []
                            registers_read[offset].append({
                                'address': str(addr),
                                'function': func_name,
                                'instruction': str(inst)
                            })
    
    print(f"  Processed {count} total instructions")
    print(f"  Found {len(found_offsets)} unique register offsets")
    
    return found_offsets

def generate_report():
    """Generate register map report"""
    print("\n=== Register Map Report ===")
    
    all_offsets = set(registers_read.keys()) | set(registers_written.keys())
    sorted_offsets = sorted(all_offsets)
    
    print("\n## Found Register Offsets:")
    print("| Offset | Hex | Reads | Writes | Functions |")
    print("|--------|-----|-------|--------|-----------|")
    
    for offset in sorted_offsets:
        reads = len(registers_read.get(offset, []))
        writes = len(registers_written.get(offset, []))
        
        funcs_read = set(r['function'] for r in registers_read.get(offset, []))
        funcs_write = set(w['function'] for w in registers_written.get(offset, []))
        all_funcs = list(funcs_read | funcs_write)[:5]
        
        print(f"| {offset} | 0x{offset:x} | {reads} | {writes} | {', '.join(all_funcs)} |")
    
    print(f"\n=== Summary ===")
    print(f"Found {len(all_offsets)} unique register offsets")
    print(f"Total reads: {sum(len(v) for v in registers_read.values())}")
    print(f"Total writes: {sum(len(v) for v in registers_written.values())}")
    
    # Save to JSON
    output_file = Path(__file__).parent / "mmio_registers.json"
    results = {
        'registers_read': {str(k): v for k, v in registers_read.items()},
        'registers_written': {str(k): v for k, v in registers_written.items()},
        'summary': {
            'total_offsets': len(all_offsets),
            'total_reads': sum(len(v) for v in registers_read.values()),
            'total_writes': sum(len(v) for v in registers_written.values())
        }
    }
    
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")

def main():
    """Main analysis function"""
    print("=" * 60)
    print("MMIO Register Discovery (PyGhidra)")
    print("=" * 60)
    
    # Open the driver file
    print(f"\nOpening driver file: {driver_file}")
    
    # Note: PyGhidra needs to be run in a specific way
    # This script should be run with: pyghidra run_mmio_analysis.py
    # Or imported in a PyGhidra session
    
    print("\nNOTE: This script needs to be run with PyGhidra launcher")
    print("Run: pyghidra run_mmio_analysis.py")
    print("Or use the analyzeHeadless with PyGhidra enabled")

if __name__ == "__main__":
    main()
