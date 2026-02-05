"""
Find missing registers by analyzing functions that use MMIO
Focuses on finding format/sample rate, position, and additional control registers
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator, Function
from ghidra.program.model.symbol import Symbol
import sys

# Known registers from previous analysis
KNOWN_REGISTERS = {
    0x0: "Version/ID",
    0x4: "Status1 (interrupt status?)",
    0x8: "Status2",
    0x10: "Status3",
    0x14: "Status4",
    0x100: "Control (write 0x8)",
    0x104: "Status5",
    0x10300: "Buffer0 (playback DMA)",
    0x10304: "Buffer1 (capture DMA)"
}

# Functions we know use MMIO
KNOWN_FUNCTIONS = ["FUN_140003d60", "FUN_140002e30"]

def get_function_name(address):
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

def find_functions_using_mmio_base():
    """Find functions that load MMIO base (offset 0xc8)"""
    print("=== Finding Functions Using MMIO Base ===")
    
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    
    functions_with_mmio = set()
    
    for inst in inst_iter:
        inst_str = str(inst)
        # Look for offset 0xc8 or 200 (MMIO base storage)
        if "0xc8" in inst_str.lower() or "+200" in inst_str or "-200" in inst_str:
            if "[R" in inst_str:  # Structure access, not stack
                addr = inst.getAddress()
                func = getFunctionContaining(addr)
                if func:
                    functions_with_mmio.add(func.getName())
    
    print("Found {} functions using MMIO base".format(len(functions_with_mmio)))
    return list(functions_with_mmio)

def analyze_function_for_registers(func_name):
    """Analyze a function to find register offsets it uses"""
    func_manager = currentProgram.getFunctionManager()
    func = func_manager.getFunction(func_name)
    
    if not func:
        return None
    
    body = func.getBody()
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(body, True)
    
    # Look for instructions that use known register offsets or common patterns
    register_offsets = set()
    instructions = []
    
    for inst in inst_iter:
        inst_str = str(inst)
        mnemonic = inst.getMnemonicString()
        
        # Check for known offsets
        for offset in KNOWN_REGISTERS.keys():
            hex_str = "0x{:x}".format(offset)
            if hex_str in inst_str.lower():
                register_offsets.add(offset)
                instructions.append({
                    'offset': offset,
                    'address': str(inst.getAddress()),
                    'instruction': inst_str,
                    'mnemonic': mnemonic
                })
        
        # Also look for common register offset patterns
        import re
        hex_pattern = r'\+0x([0-9a-fA-F]{1,4})\]'
        matches = re.findall(hex_pattern, inst_str, re.IGNORECASE)
        for match in matches:
            try:
                offset = int(match, 16)
                # Filter for reasonable MMIO offsets
                if 0 < offset <= 0x20000 and offset % 4 == 0:
                    # Skip if it's the MMIO base offset itself
                    if offset != 0xc8:
                        register_offsets.add(offset)
                        instructions.append({
                            'offset': offset,
                            'address': str(inst.getAddress()),
                            'instruction': inst_str,
                            'mnemonic': mnemonic
                        })
            except:
                pass
    
    return {
        'function': func_name,
        'registers': sorted(register_offsets),
        'instructions': instructions
    }

# Main
try:
    program = currentProgram
    print("=" * 60)
    print("Finding Missing Registers")
    print("=" * 60)
    print("Program: {}".format(program.getName()))
except:
    print("ERROR: currentProgram not available")
    sys.exit(1)

listing = currentProgram.getListing()
if not listing:
    print("ERROR: Program listing not available")
    sys.exit(1)

# Find functions using MMIO
mmio_functions = find_functions_using_mmio_base()

print("\n=== Analyzing MMIO Functions ===")
print("Found {} functions to analyze\n".format(len(mmio_functions)))

# Analyze each function
function_results = {}
for func_name in mmio_functions[:30]:  # Limit to first 30 to avoid timeout
    result = analyze_function_for_registers(func_name)
    if result and result['registers']:
        function_results[func_name] = result
        print("{}: Found {} register offsets".format(func_name, len(result['registers'])))

# Also analyze known functions
print("\n=== Analyzing Known Functions ===")
for func_name in KNOWN_FUNCTIONS:
    result = analyze_function_for_registers(func_name)
    if result:
        function_results[func_name] = result
        print("{}: Found {} register offsets".format(func_name, len(result['registers'])))

# Collect all unique register offsets found
all_offsets = set()
for result in function_results.values():
    all_offsets.update(result['registers'])

# Identify new (unknown) offsets
new_offsets = sorted([o for o in all_offsets if o not in KNOWN_REGISTERS.keys()])

print("\n=== Summary ===")
print("Total unique register offsets found: {}".format(len(all_offsets)))
print("Known registers: {}".format(len(KNOWN_REGISTERS)))
print("New (unknown) registers: {}".format(len(new_offsets)))

if new_offsets:
    print("\nNew register offsets to investigate:")
    for offset in new_offsets[:20]:  # Show first 20
        print("  0x{:04x} ({})".format(offset, offset))

# Generate report
output_file = "missing_registers.txt"
try:
    f = open(output_file, 'w')
    f.write("=== Missing Registers Analysis ===\n\n")
    from datetime import datetime
    f.write("Generated: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    f.write("=== Known Registers ===\n\n")
    for offset in sorted(KNOWN_REGISTERS.keys()):
        f.write("0x{:04x}: {}\n".format(offset, KNOWN_REGISTERS[offset]))
    f.write("\n")
    
    f.write("=== New Register Offsets Found ===\n\n")
    for offset in new_offsets:
        f.write("Offset 0x{:04x} ({}):\n".format(offset, offset))
        f.write("  Found in functions:\n")
        for func_name, result in function_results.items():
            if offset in result['registers']:
                f.write("    {}\n".format(func_name))
                # Show example instruction
                for inst in result['instructions']:
                    if inst['offset'] == offset:
                        f.write("      {}: {}\n".format(inst['address'], inst['instruction']))
                        break
        f.write("\n")
    
    f.write("\n=== Function Analysis ===\n\n")
    for func_name in sorted(function_results.keys()):
        result = function_results[func_name]
        f.write("=== {} ===\n".format(func_name))
        f.write("Register offsets: {}\n".format(", ".join("0x{:04x}".format(o) for o in result['registers'])))
        f.write("\n")
    
    f.close()
    print("\nReport saved to: {}".format(output_file))
except Exception as e:
    print("ERROR: {}".format(e))

print("\n=== Complete ===")
