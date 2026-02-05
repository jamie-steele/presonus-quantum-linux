"""
Use Ghidra's scalar search to find register offsets
This is more reliable than pattern matching
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.scalar import Scalar
import sys

# Register offsets to search for (known + common patterns)
search_offsets = [
    # Known from previous analysis
    0x0, 0x4, 0x8, 0x10, 0x14, 0x100, 0x104, 0x10300, 0x10304,
    # Common audio register patterns
    0xc, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30, 0x34, 0x38, 0x3c,
    0x40, 0x44, 0x48, 0x4c, 0x50, 0x54, 0x58, 0x5c, 0x60, 0x64, 0x68, 0x6c,
    0x70, 0x74, 0x78, 0x7c, 0x80, 0x84, 0x88, 0x8c, 0x90, 0x94, 0x98, 0x9c,
    0xa0, 0xa4, 0xa8, 0xac, 0xb0, 0xb4, 0xb8, 0xbc,
    0xc0, 0xc4, 0xcc, 0xd0, 0xd4, 0xd8, 0xdc, 0xe0, 0xe4, 0xe8, 0xec, 0xf0, 0xf4, 0xf8, 0xfc,
    # Mid-range
    0x108, 0x10c, 0x110, 0x114, 0x118, 0x11c, 0x120, 0x124, 0x128, 0x12c,
    0x130, 0x134, 0x138, 0x13c, 0x140, 0x144, 0x148, 0x14c, 0x150, 0x154, 0x158, 0x15c,
    # Higher
    0x200, 0x204, 0x208, 0x20c,
    0x300, 0x304, 0x308, 0x30c,
    # Buffer area
    0x1000, 0x1004, 0x1008, 0x100c,
    0x10308, 0x1030c
]

results = {}

def get_function_name(address):
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

print("=" * 60)
print("Scalar Search for Register Offsets")
print("=" * 60)

try:
    program = currentProgram
    print("Program: {}".format(program.getName()))
except:
    print("ERROR: currentProgram not available")
    sys.exit(1)

listing = currentProgram.getListing()
if not listing:
    print("ERROR: Program listing not available")
    sys.exit(1)

print("\nSearching for {} register offsets...\n".format(len(search_offsets)))

# Use scalar search - more reliable
for offset in search_offsets:
    found = []
    inst_iter = listing.getInstructions(True)
    
    for inst in inst_iter:
        # Check all operands for this scalar value
        num_ops = inst.getNumOperands()
        for i in range(num_ops):
            op_objs = inst.getOpObjects(i)
            if op_objs:
                for obj in op_objs:
                    if hasattr(obj, 'getScalar'):
                        scalar = obj.getScalar()
                        if scalar:
                            val = scalar.getUnsignedValue()
                            if val == offset:
                                # Check if it's in a memory operation context
                                inst_str = str(inst)
                                mnemonic = inst.getMnemonicString()
                                
                                # Only count if it's a memory operation
                                if "[" in inst_str and mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST", "LEA"]:
                                    addr = inst.getAddress()
                                    func = getFunctionContaining(addr)
                                    
                                    # Determine read/write
                                    is_write = mnemonic in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"] and i == 0
                                    is_read = mnemonic in ["MOV", "CMP", "TEST"] and i == 1
                                    
                                    # Also check instruction string
                                    if not is_write and not is_read:
                                        if "[" in inst_str:
                                            parts = inst_str.split(",")
                                            if len(parts) >= 2:
                                                if str(offset) in parts[0] or hex(offset) in parts[0].lower():
                                                    is_write = True
                                                elif str(offset) in parts[1] or hex(offset) in parts[1].lower():
                                                    is_read = True
                                    
                                    access_type = "WRITE" if is_write else ("READ" if is_read else "ACCESS")
                                    
                                    found.append({
                                        'address': str(addr),
                                        'function': func.getName() if func else "UNKNOWN",
                                        'instruction': inst_str,
                                        'type': access_type
                                    })
    
    if found:
        results[offset] = found
        reads = len([f for f in found if f['type'] == 'READ'])
        writes = len([f for f in found if f['type'] == 'WRITE'])
        print("Offset 0x{:04x}: {} total ({} reads, {} writes)".format(offset, len(found), reads, writes))

# Generate report
output_file = "registers_scalar_search.txt"
try:
    f = open(output_file, 'w')
    f.write("=== Register Offset Scalar Search ===\n\n")
    from datetime import datetime
    f.write("Generated: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    f.write("=== Summary ===\n")
    f.write("Found {} offsets with register access\n\n".format(len(results)))
    
    f.write("=== Register Map ===\n\n")
    for offset in sorted(results.keys()):
        accesses = results[offset]
        reads = [a for a in accesses if a['type'] == 'READ']
        writes = [a for a in accesses if a['type'] == 'WRITE']
        
        f.write("Offset 0x{:04x} ({}):\n".format(offset, offset))
        f.write("  Total: {} accesses ({} reads, {} writes)\n".format(len(accesses), len(reads), len(writes)))
        f.write("  Functions: {}\n".format(", ".join(set(a['function'] for a in accesses))))
        f.write("\n")
        
        # Show examples
        for acc in accesses[:10]:
            f.write("  {}: {} in {}\n".format(acc['type'], acc['instruction'], acc['function']))
        if len(accesses) > 10:
            f.write("  ... and {} more\n".format(len(accesses) - 10))
        f.write("\n")
    
    f.close()
    print("\nReport saved to: {}".format(output_file))
except Exception as e:
    print("ERROR: {}".format(e))

print("\n=== Complete ===")
print("Found {} register offsets".format(len(results)))
