"""
Simplified MMIO register finder that works reliably with PyGhidra
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction
from ghidra.program.model.scalar import Scalar
from ghidra.util.task import ConsoleTaskMonitor
import json
import os

# Results
registers_read = {}
registers_written = {}
functions_using_mmio = set()

def main():
    print("=" * 60)
    print("MMIO Register Discovery (Simplified)")
    print("=" * 60)
    
    # Get program listing
    listing = currentProgram.getListing()
    monitor = ConsoleTaskMonitor()
    
    # Get all instructions
    print("\n=== Searching for Register Offsets ===")
    inst_iter = listing.getInstructions(True)
    
    count = 0
    found_offsets = set()
    
    try:
        for inst in inst_iter:
            if monitor.isCancelled():
                break
            
            count += 1
            if count % 5000 == 0:
                print("  Processed {} instructions...".format(count))
            
            mnemonic = inst.getMnemonicString()
            addr = inst.getAddress()
            func = getFunctionContaining(addr)
            func_name = func.getName() if func else "UNKNOWN"
            
            # Look for memory operations
            if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST", "LEA"]:
                ops = inst.getOperands()
                
                # Check all operands for scalar offsets
                for i, op in enumerate(ops):
                    if op and op.isScalar():
                        scalar = op.getScalar()
                        offset = scalar.getUnsignedValue()
                        
                        # Filter reasonable offsets (0 to 1MB, or small unaligned)
                        if 0 <= offset <= 0x100000:
                            found_offsets.add(offset)
                            
                            # Determine read/write
                            is_write = (i == 0 and mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR"])
                            is_read = (i == 1 and mnemonic in ["MOV", "CMP", "TEST"]) or (i == 0 and mnemonic in ["CMP", "TEST"])
                            
                            # Get value if write
                            value = None
                            if is_write and len(ops) > 1:
                                value_op = ops[1]
                                if value_op and value_op.isScalar():
                                    value = value_op.getScalar().getUnsignedValue()
                            
                            if is_write:
                                if offset not in registers_written:
                                    registers_written[offset] = []
                                registers_written[offset].append({
                                    'address': str(addr),
                                    'function': func_name,
                                    'value': value,
                                    'instruction': str(inst)
                                })
                                functions_using_mmio.add(func_name)
                            
                            if is_read:
                                if offset not in registers_read:
                                    registers_read[offset] = []
                                registers_read[offset].append({
                                    'address': str(addr),
                                    'function': func_name,
                                    'instruction': str(inst)
                                })
                                functions_using_mmio.add(func_name)
    
    except Exception as e:
        print("  ERROR: {}".format(e))
        import traceback
        traceback.print_exc()
    
    print("  Processed {} total instructions".format(count))
    print("  Found {} unique offset values".format(len(found_offsets)))
    
    # Generate report
    print("\n=== Register Map Report ===")
    print("\n## Registers Read:")
    print("| Offset | Hex | Count | Functions |")
    print("|--------|-----|-------|-----------|")
    
    for offset in sorted(registers_read.keys()):
        accesses = registers_read[offset]
        funcs = set(a['function'] for a in accesses)
        print("| {} | 0x{:x} | {} | {} |".format(
            offset, offset, len(accesses), ", ".join(sorted(funcs)[:3])))
    
    print("\n## Registers Written:")
    print("| Offset | Hex | Count | Functions | Values |")
    print("|--------|-----|-------|-----------|--------|")
    
    for offset in sorted(registers_written.keys()):
        accesses = registers_written[offset]
        funcs = set(a['function'] for a in accesses)
        values = set(a['value'] for a in accesses if a['value'] is not None)
        print("| {} | 0x{:x} | {} | {} | {} |".format(
            offset, offset, len(accesses), ", ".join(sorted(funcs)[:3]),
            ", ".join("0x{:x}".format(v) for v in sorted(values)[:5])))
    
    # Save to JSON
    report = {
        'registers_read': {str(k): v for k, v in registers_read.items()},
        'registers_written': {str(k): v for k, v in registers_written.items()},
        'functions_using_mmio': list(functions_using_mmio),
        'summary': {
            'total_read_offsets': len(registers_read),
            'total_write_offsets': len(registers_written),
            'total_functions': len(functions_using_mmio),
            'total_instructions': count
        }
    }
    
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    output_file = os.path.join(script_dir, "mmio_registers.json")
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    print("\nReport saved to: {}".format(output_file))
    
    print("\n=== Summary ===")
    print("Found {} unique register offsets read".format(len(registers_read)))
    print("Found {} unique register offsets written".format(len(registers_written)))
    print("Found {} functions using MMIO".format(len(functions_using_mmio)))

if __name__ == "__main__":
    main()
