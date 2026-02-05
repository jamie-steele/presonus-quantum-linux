"""
Enhanced Ghidra script to find ALL register patterns in pae_quantum.sys
This script:
1. Finds MMIO base usage and traces all register access
2. Searches for sample rate/format values and traces to registers
3. Finds control register bit operations
4. Analyzes functions that use MMIO to find register patterns
5. Generates comprehensive register map
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.scalar import Scalar
from ghidra.program.model.symbol import Symbol
from ghidra.util.task import ConsoleTaskMonitor
import sys

# Results
all_register_accesses = {}  # offset -> list of accesses
mmio_base_refs = []  # References to MMIO base
functions_using_mmio = set()
sample_rate_usage = []  # Where sample rates are used
format_usage = []  # Where format values are used

def get_function_name(address):
    """Get function name containing address"""
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

def find_mmio_base_storage():
    """Find where MMIO base is stored (param_1 + 0xc8)"""
    print("=== Finding MMIO Base Storage ===")
    
    # Known: MMIO base stored at offset 0xc8 (200) in device structure
    # Look for references to this pattern
    listing = currentProgram.getListing()
    
    # Search for 0xc8 or 200 in instructions
    found_refs = []
    inst_iter = listing.getInstructions(True)
    
    for inst in inst_iter:
        inst_str = str(inst)
        # Look for patterns like [register+0xc8] or [register+200]
        if "0xc8" in inst_str.lower() or "+200" in inst_str or "-200" in inst_str:
            addr = inst.getAddress()
            func = getFunctionContaining(addr)
            found_refs.append({
                'address': str(addr),
                'function': func.getName() if func else "UNKNOWN",
                'instruction': inst_str
            })
            if func:
                functions_using_mmio.add(func.getName())
    
    print("  Found {} references to MMIO base storage (0xc8/200)".format(len(found_refs)))
    mmio_base_refs.extend(found_refs)
    return found_refs

def find_register_accesses_from_mmio_base():
    """Find all register accesses by following MMIO base usage"""
    print("\n=== Finding Register Accesses from MMIO Base ===")
    
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    count = 0
    found_accesses = []
    
    # Known offsets to look for
    known_offsets = [0x0, 0x4, 0x8, 0x10, 0x14, 0x100, 0x104, 0x10300, 0x10304]
    
    # Also look for common audio register offsets
    common_offsets = [
        0x0, 0x4, 0x8, 0xc, 0x10, 0x14, 0x18, 0x1c, 0x20,
        0x100, 0x104, 0x108, 0x10c, 0x110, 0x114,
        0x200, 0x204, 0x208, 0x20c,
        0x300, 0x304, 0x308,
        0x1000, 0x1004, 0x1008,
        0x10300, 0x10304, 0x10308, 0x1030c
    ]
    
    for inst in inst_iter:
        count += 1
        if count % 10000 == 0:
            print("  Processed {} instructions...".format(count))
        
        mnemonic = inst.getMnemonicString()
        addr = inst.getAddress()
        func = getFunctionContaining(addr)
        func_name = func.getName() if func else "UNKNOWN"
        
        inst_str = str(inst)
        
        # Look for memory operations with offsets
        if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST", "LEA"]:
            # Parse instruction string for offset patterns
            import re
            
            # Pattern: [register+0x100] or [register+256]
            hex_pattern = r'\[.*?[+\-]0x([0-9a-fA-F]+)\]'
            dec_pattern = r'\[.*?[+\-](\d+)\]'
            
            for pattern in [hex_pattern, dec_pattern]:
                matches = re.findall(pattern, inst_str, re.IGNORECASE)
                for match in matches:
                    try:
                        if '0x' in match or any(c in 'abcdef' for c in match.lower()):
                            offset = int(match, 16)
                        else:
                            offset = int(match)
                        
                        # Filter reasonable MMIO offsets (0 to 128KB)
                        if 0 <= offset <= 0x20000:
                            # Check if it's a known offset or common pattern
                            is_known = offset in known_offsets
                            is_common = offset in common_offsets
                            is_power_of_2_aligned = (offset % 4 == 0)
                            
                            if is_known or is_common or (is_power_of_2_aligned and offset < 0x1000):
                                # Determine read vs write
                                is_write = mnemonic in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"] and "[" in inst_str and inst_str.index("[") < inst_str.index("=") if "=" in inst_str else False
                                is_read = mnemonic in ["MOV", "CMP", "TEST"] and "[" in inst_str
                                
                                # Better detection: first operand is memory = write, second operand is memory = read
                                num_ops = inst.getNumOperands()
                                if num_ops >= 2:
                                    # Check operand types
                                    op0 = inst.getOpObjects(0)
                                    op1 = inst.getOpObjects(1) if num_ops > 1 else None
                                    
                                    # If first operand is memory reference, it's likely a write
                                    if op0 and len(op0) > 0:
                                        op0_str = str(op0[0])
                                        if "[" in op0_str:
                                            is_write = True
                                    
                                    # If second operand is memory reference, it's likely a read
                                    if op1 and len(op1) > 0:
                                        op1_str = str(op1[0])
                                        if "[" in op1_str:
                                            is_read = True
                                
                                access_type = "WRITE" if is_write else ("READ" if is_read else "UNKNOWN")
                                
                                if offset not in all_register_accesses:
                                    all_register_accesses[offset] = []
                                
                                all_register_accesses[offset].append({
                                    'address': str(addr),
                                    'function': func_name,
                                    'instruction': inst_str,
                                    'type': access_type,
                                    'mnemonic': mnemonic
                                })
                                
                                functions_using_mmio.add(func_name)
                                
                    except ValueError:
                        pass
    
    print("  Found {} unique register offsets".format(len(all_register_accesses)))
    return all_register_accesses

def find_sample_rate_values():
    """Find sample rate values and trace to register writes"""
    print("\n=== Finding Sample Rate Values ===")
    
    sample_rates = [44100, 48000, 88200, 96000, 176400, 192000, 22050, 24000, 32000]
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    
    found = []
    for inst in inst_iter:
        num_ops = inst.getNumOperands()
        for i in range(num_ops):
            op = inst.getOpObjects(i)
            if op:
                for obj in op:
                    if hasattr(obj, 'getScalar'):
                        scalar = obj.getScalar()
                        if scalar:
                            val = scalar.getUnsignedValue()
                            if val in sample_rates:
                                addr = inst.getAddress()
                                func = getFunctionContaining(addr)
                                found.append({
                                    'value': val,
                                    'address': str(addr),
                                    'function': func.getName() if func else "UNKNOWN",
                                    'instruction': str(inst)
                                })
                                sample_rate_usage.append({
                                    'value': val,
                                    'address': str(addr),
                                    'function': func.getName() if func else "UNKNOWN"
                                })
    
    print("  Found {} sample rate value usages".format(len(found)))
    return found

def generate_comprehensive_report():
    """Generate comprehensive register map report"""
    print("\n=== Generating Comprehensive Report ===")
    
    output_file = "all_registers.txt"
    
    try:
        f = open(output_file, 'w')
        f.write("=== Comprehensive Register Map - pae_quantum.sys ===\n\n")
        from datetime import datetime
        f.write("Generated: {}\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        f.write("\n")
        
        # Summary
        f.write("=== Summary ===\n")
        f.write("Total unique register offsets: {}\n".format(len(all_register_accesses)))
        f.write("Functions using MMIO: {}\n".format(len(functions_using_mmio)))
        f.write("Sample rate usages found: {}\n".format(len(sample_rate_usage)))
        f.write("\n")
        
        # Register accesses sorted by offset
        f.write("=== Register Accesses (sorted by offset) ===\n\n")
        sorted_offsets = sorted(all_register_accesses.keys())
        
        for offset in sorted_offsets:
            accesses = all_register_accesses[offset]
            reads = [a for a in accesses if a['type'] == 'READ']
            writes = [a for a in accesses if a['type'] == 'WRITE']
            
            f.write("Offset 0x{:04x} ({} decimal):\n".format(offset, offset))
            f.write("  Total accesses: {}\n".format(len(accesses)))
            f.write("  Reads: {}, Writes: {}\n".format(len(reads), len(writes)))
            f.write("  Functions: {}\n".format(", ".join(set(a['function'] for a in accesses))))
            f.write("\n")
            
            # Show first few examples
            for i, access in enumerate(accesses[:5]):
                f.write("  {}: {} in {}\n".format(access['type'], access['instruction'], access['function']))
            if len(accesses) > 5:
                f.write("  ... and {} more\n".format(len(accesses) - 5))
            f.write("\n")
        
        # Sample rate usage
        if sample_rate_usage:
            f.write("\n=== Sample Rate Value Usage ===\n\n")
            for usage in sample_rate_usage[:20]:  # Limit output
                f.write("{} Hz at {} in {}\n".format(usage['value'], usage['address'], usage['function']))
        
        # Functions using MMIO
        f.write("\n=== Functions Using MMIO ===\n\n")
        for func_name in sorted(functions_using_mmio):
            f.write("  {}\n".format(func_name))
        
        f.close()
        print("  Report saved to: {}".format(output_file))
        
    except Exception as e:
        print("  ERROR saving report: {}".format(e))
    
    return output_file

# Main execution
try:
    program = currentProgram
    program_name = program.getName()
except NameError:
    print("ERROR: currentProgram not available")
    sys.exit(1)

print("=" * 60)
print("Comprehensive Register Analysis")
print("=" * 60)
print("Program: {}".format(program_name))
print("")

listing = currentProgram.getListing()
if not listing:
    print("ERROR: Program listing not available")
    sys.exit(1)

# Run analysis
find_mmio_base_storage()
find_register_accesses_from_mmio_base()
find_sample_rate_values()

# Generate report
report_file = generate_comprehensive_report()

print("\n=== Analysis Complete ===")
print("Check {} for detailed results".format(report_file))
print("Found {} unique register offsets".format(len(all_register_accesses)))
