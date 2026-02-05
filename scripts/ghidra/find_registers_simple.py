"""
Simple register finder - searches for known offsets and common patterns
Uses scalar search which is more reliable
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.scalar import Scalar
import sys

# Known offsets from previous analysis
known_offsets = [0x0, 0x4, 0x8, 0x10, 0x14, 0x100, 0x104, 0x10300, 0x10304]

# Common audio register offsets to search for
search_offsets = [
    # Low registers
    0x0, 0x4, 0x8, 0xc, 0x10, 0x14, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30, 0x34, 0x38, 0x3c,
    0x40, 0x44, 0x48, 0x4c, 0x50, 0x54, 0x58, 0x5c, 0x60, 0x64, 0x68, 0x6c, 0x70, 0x74, 0x78, 0x7c,
    0x80, 0x84, 0x88, 0x8c, 0x90, 0x94, 0x98, 0x9c, 0xa0, 0xa4, 0xa8, 0xac, 0xb0, 0xb4, 0xb8, 0xbc,
    0xc0, 0xc4, 0xc8, 0xcc, 0xd0, 0xd4, 0xd8, 0xdc, 0xe0, 0xe4, 0xe8, 0xec, 0xf0, 0xf4, 0xf8, 0xfc,
    # Mid registers
    0x100, 0x104, 0x108, 0x10c, 0x110, 0x114, 0x118, 0x11c, 0x120, 0x124, 0x128, 0x12c,
    0x130, 0x134, 0x138, 0x13c, 0x140, 0x144, 0x148, 0x14c, 0x150, 0x154, 0x158, 0x15c,
    # Higher registers
    0x200, 0x204, 0x208, 0x20c,
    0x300, 0x304, 0x308, 0x30c,
    # Buffer registers
    0x1000, 0x1004, 0x1008, 0x100c,
    0x10300, 0x10304, 0x10308, 0x1030c
]

results = {}  # offset -> list of findings

def get_function_name(address):
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

print("=" * 60)
print("Simple Register Offset Search")
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

print("\nSearching for {} register offsets...".format(len(search_offsets)))
print("")

# Search for each offset
for offset in search_offsets:
    found = []
    inst_iter = listing.getInstructions(True)
    
    for inst in inst_iter:
        inst_str = str(inst)
        mnemonic = inst.getMnemonicString()
        
        # Check if offset appears in instruction
        # Look for hex and decimal forms
        hex_str = "0x{:x}".format(offset)
        hex_str_upper = hex_str.upper()
        dec_str = str(offset)
        
        if hex_str in inst_str.lower() or dec_str in inst_str:
            # Make sure it's in a memory operation context
            if "[" in inst_str and mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST", "LEA"]:
                addr = inst.getAddress()
                func = getFunctionContaining(addr)
                
                # Determine read/write
                is_write = mnemonic in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"] and "[" in inst_str
                is_read = mnemonic in ["MOV", "CMP", "TEST"] and "[" in inst_str
                
                access_type = "WRITE" if is_write else ("READ" if is_read else "ACCESS")
                
                found.append({
                    'address': str(addr),
                    'function': func.getName() if func else "UNKNOWN",
                    'instruction': inst_str,
                    'type': access_type
                })
    
    if found:
        results[offset] = found
        print("Offset 0x{:04x}: Found {} accesses".format(offset, len(found)))

print("\n=== Summary ===")
print("Found {} offsets with register access".format(len(results)))

# Generate report
output_file = "registers_simple.txt"
try:
    f = open(output_file, 'w')
    f.write("=== Simple Register Search Results ===\n\n")
    from datetime import datetime
    f.write("Generated: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    sorted_offsets = sorted(results.keys())
    for offset in sorted_offsets:
        accesses = results[offset]
        reads = [a for a in accesses if a['type'] == 'READ']
        writes = [a for a in accesses if a['type'] == 'WRITE']
        
        f.write("Offset 0x{:04x} ({}): {} accesses ({} reads, {} writes)\n".format(
            offset, offset, len(accesses), len(reads), len(writes)))
        f.write("  Functions: {}\n".format(", ".join(set(a['function'] for a in accesses))))
        for acc in accesses[:5]:
            f.write("  {}: {} in {}\n".format(acc['type'], acc['instruction'], acc['function']))
        if len(accesses) > 5:
            f.write("  ... and {} more\n".format(len(accesses) - 5))
        f.write("\n")
    
    f.close()
    print("Report saved to: {}".format(output_file))
except Exception as e:
    print("ERROR saving report: {}".format(e))

print("\n=== Complete ===")
