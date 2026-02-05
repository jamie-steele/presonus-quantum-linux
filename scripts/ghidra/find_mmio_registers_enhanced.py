"""
Enhanced MMIO register finder - focuses on actual MMIO access patterns
Looks for MMIO base + offset patterns, not stack operations
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.scalar import Scalar
from ghidra.program.model.symbol import Symbol
from ghidra.util.task import ConsoleTaskMonitor
import sys
import re

# Results - only positive offsets (MMIO registers)
mmio_registers = {}  # offset -> list of accesses
mmio_base_usage = []  # Where MMIO base is used

def get_function_name(address):
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

def find_mmio_base_usage():
    """Find where MMIO base (stored at offset 0xc8) is loaded and used"""
    print("=== Finding MMIO Base Usage ===")
    
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    
    # Look for instructions that load MMIO base (from offset 0xc8)
    # Pattern: MOV register, [base + 0xc8] or MOV register, [base + 200]
    mmio_base_loads = []
    
    for inst in inst_iter:
        mnemonic = inst.getMnemonicString()
        if mnemonic in ["MOV", "LEA"]:
            inst_str = str(inst)
            # Look for 0xc8 or 200 in the source operand
            if "0xc8" in inst_str.lower() or "+200" in inst_str or "-200" in inst_str:
                # Check if it's loading from structure (not stack)
                if "[R" in inst_str or "[RCX" in inst_str or "[RDX" in inst_str or "[RSI" in inst_str or "[RDI" in inst_str:
                    addr = inst.getAddress()
                    func = getFunctionContaining(addr)
                    mmio_base_loads.append({
                        'address': str(addr),
                        'function': func.getName() if func else "UNKNOWN",
                        'instruction': inst_str
                    })
    
    print("  Found {} MMIO base loads".format(len(mmio_base_loads)))
    mmio_base_usage.extend(mmio_base_loads)
    return mmio_base_loads

def find_register_accesses_positive_only():
    """Find register accesses - only positive offsets (MMIO registers)"""
    print("\n=== Finding MMIO Register Accesses (positive offsets only) ===")
    
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    count = 0
    
    # Known MMIO offsets from previous analysis
    known_offsets = [0x0, 0x4, 0x8, 0x10, 0x14, 0x100, 0x104, 0x10300, 0x10304]
    
    # Common MMIO register offsets (4-byte aligned, positive)
    common_offsets = set([
        0x0, 0x4, 0x8, 0xc, 0x10, 0x14, 0x18, 0x1c, 0x20, 0x24, 0x28, 0x2c, 0x30, 0x34, 0x38, 0x3c,
        0x40, 0x44, 0x48, 0x4c, 0x50, 0x54, 0x58, 0x5c, 0x60, 0x64, 0x68, 0x6c, 0x70, 0x74, 0x78, 0x7c,
        0x80, 0x84, 0x88, 0x8c, 0x90, 0x94, 0x98, 0x9c, 0xa0, 0xa4, 0xa8, 0xac, 0xb0, 0xb4, 0xb8, 0xbc,
        0xc0, 0xc4, 0xc8, 0xcc, 0xd0, 0xd4, 0xd8, 0xdc, 0xe0, 0xe4, 0xe8, 0xec, 0xf0, 0xf4, 0xf8, 0xfc,
        0x100, 0x104, 0x108, 0x10c, 0x110, 0x114, 0x118, 0x11c,
        0x200, 0x204, 0x208, 0x20c,
        0x300, 0x304,
        0x1000, 0x1004, 0x1008,
        0x10300, 0x10304, 0x10308, 0x1030c
    ])
    
    for inst in inst_iter:
        count += 1
        if count % 20000 == 0:
            print("  Processed {} instructions...".format(count))
        
        mnemonic = inst.getMnemonicString()
        addr = inst.getAddress()
        func = getFunctionContaining(addr)
        func_name = func.getName() if func else "UNKNOWN"
        
        inst_str = str(inst)
        
        # Only look at memory operations
        if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST"]:
            # Parse for positive hex offsets only
            # Pattern: [register+0x100] or [register+256] (positive only)
            hex_pattern = r'\[.*?\+0x([0-9a-fA-F]+)\]'
            dec_pattern = r'\[.*?\+(\d+)\]'
            
            for pattern in [hex_pattern, dec_pattern]:
                matches = re.findall(pattern, inst_str, re.IGNORECASE)
                for match in matches:
                    try:
                        if '0x' in match or any(c in 'abcdef' for c in match.lower()):
                            offset = int(match, 16)
                        else:
                            offset = int(match)
                        
                        # ONLY positive offsets, 4-byte aligned, reasonable range
                        if offset > 0 and offset % 4 == 0 and offset <= 0x20000:
                            # Prefer known offsets or common patterns
                            if offset in known_offsets or offset in common_offsets or offset < 0x200:
                                # Determine read vs write
                                num_ops = inst.getNumOperands()
                                is_write = False
                                is_read = False
                                
                                if num_ops >= 2:
                                    op0 = inst.getOpObjects(0)
                                    op1 = inst.getOpObjects(1) if num_ops > 1 else None
                                    
                                    # Check if first operand contains the offset (write)
                                    if op0 and len(op0) > 0:
                                        op0_str = str(op0[0])
                                        if str(offset) in op0_str or hex(offset) in op0_str.lower():
                                            is_write = True
                                    
                                    # Check if second operand contains the offset (read)
                                    if op1 and len(op1) > 0:
                                        op1_str = str(op1[0])
                                        if str(offset) in op1_str or hex(offset) in op1_str.lower():
                                            is_read = True
                                
                                # Also check instruction string pattern
                                if not is_write and not is_read:
                                    # MOV [reg+offset], value = write
                                    if mnemonic == "MOV" and "[" in inst_str:
                                        parts = inst_str.split(",")
                                        if len(parts) >= 2:
                                            if str(offset) in parts[0] or hex(offset) in parts[0].lower():
                                                is_write = True
                                            elif str(offset) in parts[1] or hex(offset) in parts[1].lower():
                                                is_read = True
                                
                                access_type = "WRITE" if is_write else ("READ" if is_read else "ACCESS")
                                
                                if offset not in mmio_registers:
                                    mmio_registers[offset] = []
                                
                                mmio_registers[offset].append({
                                    'address': str(addr),
                                    'function': func_name,
                                    'instruction': inst_str,
                                    'type': access_type
                                })
                                
                    except ValueError:
                        pass
    
    print("  Found {} unique MMIO register offsets".format(len(mmio_registers)))
    return mmio_registers

def generate_report():
    """Generate register map report"""
    print("\n=== Generating Report ===")
    
    output_file = "mmio_registers_enhanced.txt"
    
    try:
        f = open(output_file, 'w')
        f.write("=== Enhanced MMIO Register Map ===\n\n")
        from datetime import datetime
        f.write("Generated: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        f.write("\n")
        
        f.write("=== Summary ===\n")
        f.write("Total unique register offsets: {}\n".format(len(mmio_registers)))
        f.write("\n")
        
        # Sort by offset
        sorted_offsets = sorted(mmio_registers.keys())
        
        f.write("=== Register Map (sorted by offset) ===\n\n")
        for offset in sorted_offsets:
            accesses = mmio_registers[offset]
            reads = [a for a in accesses if a['type'] == 'READ']
            writes = [a for a in accesses if a['type'] == 'WRITE']
            access = [a for a in accesses if a['type'] == 'ACCESS']
            
            f.write("Offset 0x{:04x} ({} decimal):\n".format(offset, offset))
            f.write("  Total: {} accesses ({} reads, {} writes, {} unknown)\n".format(
                len(accesses), len(reads), len(writes), len(access)))
            f.write("  Functions: {}\n".format(", ".join(set(a['function'] for a in accesses))))
            f.write("\n")
            
            # Show examples
            for i, acc in enumerate(accesses[:10]):
                f.write("  {}: {}\n".format(acc['type'], acc['instruction']))
                f.write("      in {}\n".format(acc['function']))
            if len(accesses) > 10:
                f.write("  ... and {} more\n".format(len(accesses) - 10))
            f.write("\n")
        
        f.close()
        print("  Report saved to: {}".format(output_file))
        
    except Exception as e:
        print("  ERROR: {}".format(e))
    
    return output_file

# Main
try:
    program = currentProgram
    program_name = program.getName()
except NameError:
    print("ERROR: currentProgram not available")
    sys.exit(1)

print("=" * 60)
print("Enhanced MMIO Register Analysis")
print("=" * 60)
print("Program: {}".format(program_name))
print("")

listing = currentProgram.getListing()
if not listing:
    print("ERROR: Program listing not available")
    sys.exit(1)

find_mmio_base_usage()
find_register_accesses_positive_only()
report_file = generate_report()

print("\n=== Complete ===")
print("Found {} MMIO register offsets".format(len(mmio_registers)))
print("Report: {}".format(report_file))
