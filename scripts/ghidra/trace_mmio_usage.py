"""
Trace MMIO base usage through the codebase
Uses cross-references to find all places MMIO base is used
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator, Function
from ghidra.program.model.symbol import Symbol
import sys

# Known: MMIO base stored at offset 0xc8 in device structure
# Known: FUN_140003d60 loads MMIO base and uses it
# Strategy: Find where offset 0xc8 is used, then trace that variable to register accesses

def get_function_name(address):
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

def find_mmio_base_loads():
    """Find where MMIO base (offset 0xc8) is loaded"""
    print("=== Finding MMIO Base Loads (offset 0xc8) ===")
    
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    
    base_loads = []
    
    for inst in inst_iter:
        inst_str = str(inst)
        mnemonic = inst.getMnemonicString()
        
        # Look for loading from offset 0xc8 or 200
        if mnemonic in ["MOV", "LEA"] and ("0xc8" in inst_str.lower() or "+200" in inst_str or "-200" in inst_str):
            # Make sure it's loading from structure, not stack
            if "[R" in inst_str or "[RCX" in inst_str or "[RDX" in inst_str:
                addr = inst.getAddress()
                func = getFunctionContaining(addr)
                
                base_loads.append({
                    'address': str(addr),
                    'function': func.getName() if func else "UNKNOWN",
                    'instruction': inst_str
                })
    
    print("Found {} MMIO base loads".format(len(base_loads)))
    return base_loads

def find_known_function_registers():
    """Analyze known functions using manual pattern matching"""
    print("\n=== Analyzing Known Functions ===")
    
    # Known from previous analysis
    known_functions = {
        "FUN_140003d60": {
            'description': 'Device initialization',
            'known_registers': [0x0, 0x4, 0x8, 0x10, 0x14, 0x104, 0x10300, 0x10304],
            'known_writes': []
        },
        "FUN_140002e30": {
            'description': 'Control register write',
            'known_registers': [],
            'known_writes': [(0x100, 0x8)]
        }
    }
    
    func_manager = currentProgram.getFunctionManager()
    results = {}
    
    for func_name, info in known_functions.items():
        func = func_manager.getFunction(func_name)
        if func:
            print("\nAnalyzing: {} - {}".format(func_name, info['description']))
            
            body = func.getBody()
            listing = currentProgram.getListing()
            inst_iter = listing.getInstructions(body, True)
            
            found_registers = {}
            
            # Search for known offsets in this function
            for inst in inst_iter:
                inst_str = str(inst)
                
                # Check for each known register offset
                for offset in info['known_registers']:
                    hex_str = "0x{:x}".format(offset)
                    if hex_str in inst_str.lower():
                        if offset not in found_registers:
                            found_registers[offset] = []
                        found_registers[offset].append({
                            'address': str(inst.getAddress()),
                            'instruction': inst_str
                        })
                
                # Check for known writes
                for offset, value in info['known_writes']:
                    hex_str = "0x{:x}".format(offset)
                    val_str = "0x{:x}".format(value)
                    if hex_str in inst_str.lower() and val_str in inst_str.lower():
                        if offset not in found_registers:
                            found_registers[offset] = []
                        found_registers[offset].append({
                            'address': str(inst.getAddress()),
                            'instruction': inst_str,
                            'value': value
                        })
            
            results[func_name] = {
                'function': func,
                'found_registers': found_registers,
                'known': info
            }
            
            print("  Found {} register offsets".format(len(found_registers)))
            for offset in sorted(found_registers.keys()):
                print("    Offset 0x{:04x}: {} accesses".format(offset, len(found_registers[offset])))
        else:
            print("Function {} not found".format(func_name))
    
    return results

def search_for_common_offsets():
    """Search for common register offsets across entire binary"""
    print("\n=== Searching for Common Register Offsets ===")
    
    # Focus on offsets we know exist and common audio register patterns
    search_offsets = [
        0x0, 0x4, 0x8, 0xc, 0x10, 0x14, 0x18, 0x1c,
        0x100, 0x104, 0x108, 0x10c,
        0x200, 0x204,
        0x10300, 0x10304, 0x10308
    ]
    
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    
    offset_usage = {}
    
    print("Searching {} offsets...".format(len(search_offsets)))
    
    for offset in search_offsets:
        hex_str = "0x{:x}".format(offset)
        found = []
        
        for inst in inst_iter:
            inst_str = str(inst)
            if hex_str in inst_str.lower() and "[" in inst_str:
                mnemonic = inst.getMnemonicString()
                if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST"]:
                    addr = inst.getAddress()
                    func = getFunctionContaining(addr)
                    
                    found.append({
                        'address': str(addr),
                        'function': func.getName() if func else "UNKNOWN",
                        'instruction': inst_str,
                        'mnemonic': mnemonic
                    })
        
        if found:
            offset_usage[offset] = found
            print("  Offset 0x{:04x}: {} accesses".format(offset, len(found)))
    
    return offset_usage

# Main
try:
    program = currentProgram
    print("=" * 60)
    print("MMIO Usage Tracing")
    print("=" * 60)
    print("Program: {}".format(program.getName()))
except:
    print("ERROR: currentProgram not available")
    sys.exit(1)

listing = currentProgram.getListing()
if not listing:
    print("ERROR: Program listing not available")
    sys.exit(1)

# Run analysis
base_loads = find_mmio_base_loads()
function_results = find_known_function_registers()
offset_usage = search_for_common_offsets()

# Generate report
output_file = "mmio_trace_results.txt"
try:
    f = open(output_file, 'w')
    f.write("=== MMIO Usage Trace Results ===\n\n")
    from datetime import datetime
    f.write("Generated: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    f.write("=== MMIO Base Loads (offset 0xc8) ===\n\n")
    for load in base_loads[:20]:  # Limit output
        f.write("{} in {}: {}\n".format(load['address'], load['function'], load['instruction']))
    f.write("\n")
    
    f.write("=== Known Function Analysis ===\n\n")
    for func_name, result in function_results.items():
        f.write("=== {} ===\n".format(func_name))
        f.write("Description: {}\n".format(result['known']['description']))
        f.write("\n")
        
        found = result['found_registers']
        if found:
            f.write("Register Accesses Found:\n")
            for offset in sorted(found.keys()):
                accesses = found[offset]
                f.write("  Offset 0x{:04x}: {} accesses\n".format(offset, len(accesses)))
                for acc in accesses[:3]:
                    f.write("    {}: {}\n".format(acc['address'], acc['instruction']))
        else:
            f.write("No register accesses found (pattern matching may need improvement)\n")
        f.write("\n")
    
    f.write("\n=== Common Offset Usage ===\n\n")
    for offset in sorted(offset_usage.keys()):
        accesses = offset_usage[offset]
        f.write("Offset 0x{:04x}: {} accesses\n".format(offset, len(accesses)))
        f.write("  Functions: {}\n".format(", ".join(set(a['function'] for a in accesses))))
        f.write("  Examples:\n")
        for acc in accesses[:5]:
            f.write("    {} in {}: {}\n".format(acc['address'], acc['function'], acc['instruction']))
        f.write("\n")
    
    f.close()
    print("\nReport saved to: {}".format(output_file))
except Exception as e:
    print("ERROR: {}".format(e))

print("\n=== Complete ===")
print("Found {} MMIO base loads".format(len(base_loads)))
print("Analyzed {} known functions".format(len(function_results)))
print("Found {} offsets with usage".format(len(offset_usage)))
