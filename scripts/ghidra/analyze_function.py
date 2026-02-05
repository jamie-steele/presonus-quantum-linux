"""
Analyze a specific function to find register access patterns
Can be used to analyze interrupt handler, stream control, etc.
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator, Function
import sys
import re

def get_function_by_name(func_name):
    """Find function by name"""
    func_manager = currentProgram.getFunctionManager()
    functions = func_manager.getFunctions(True)  # True = forward iteration
    
    for func in functions:
        if func.getName() == func_name:
            return func
    
    return None

def analyze_function(func):
    """Analyze a function for register access"""
    if not func:
        return None
    
    body = func.getBody()
    listing = currentProgram.getListing()
    
    registers = {}
    
    inst_iter = listing.getInstructions(body, True)
    
    for inst in inst_iter:
        mnemonic = inst.getMnemonicString()
        inst_str = str(inst)
        addr = inst.getAddress()
        
        # Look for register offsets
        if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST"] and "[" in inst_str:
            hex_pattern = r'\[.*?\+0x([0-9a-fA-F]+)\]'
            matches = re.findall(hex_pattern, inst_str, re.IGNORECASE)
            
            for match in matches:
                try:
                    offset = int(match, 16)
                    if 0 < offset <= 0x20000 and offset % 4 == 0:
                        if offset not in registers:
                            registers[offset] = {'reads': [], 'writes': []}
                        
                        is_write = mnemonic in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"]
                        is_read = mnemonic in ["MOV", "CMP", "TEST"]
                        
                        access = {
                            'address': str(addr),
                            'instruction': inst_str,
                            'type': 'WRITE' if is_write else 'READ'
                        }
                        
                        if is_write:
                            registers[offset]['writes'].append(access)
                        elif is_read:
                            registers[offset]['reads'].append(access)
                except:
                    pass
    
    return {
        'name': func.getName(),
        'address': str(func.getEntryPoint()),
        'registers': registers
    }

# Main
try:
    program = currentProgram
    print("=" * 60)
    print("Function Analysis")
    print("=" * 60)
except:
    print("ERROR: currentProgram not available")
    sys.exit(1)

# Analyze key functions
functions_to_analyze = [
    "FUN_140003d60",  # Initialization
    "FUN_140002e30",  # Control register write
    "FUN_14000d410",  # Possible interrupt handler
]

print("\n=== Analyzing Key Functions ===\n")

results = {}

for func_name in functions_to_analyze:
    func = get_function_by_name(func_name)
    if func:
        print("Analyzing: {}".format(func_name))
        result = analyze_function(func)
        if result:
            results[func_name] = result
            regs = result['registers']
            print("  Found {} register offsets".format(len(regs)))
            for offset in sorted(regs.keys()):
                reads = len(regs[offset]['reads'])
                writes = len(regs[offset]['writes'])
                print("    Offset 0x{:04x}: {} reads, {} writes".format(offset, reads, writes))
    else:
        print("Function {} not found".format(func_name))

# Also try to find interrupt handler from IoConnectInterruptEx
print("\n=== Finding Interrupt Handler ===")
symbol_table = currentProgram.getSymbolTable()
interrupt_symbols = list(symbol_table.getSymbols("IoConnectInterruptEx"))
if not interrupt_symbols:
    for sym in symbol_table.getExternalSymbols():
        if sym.getName() == "IoConnectInterruptEx":
            interrupt_symbols = [sym]
            break

if interrupt_symbols:
    refs = getReferencesTo(interrupt_symbols[0].getAddress())
    for ref in refs:
        from_addr = ref.getFromAddress()
        func = getFunctionContaining(from_addr)
        if func:
            func_name = func.getName()
            print("IoConnectInterruptEx called from: {}".format(func_name))
            
            # Analyze this function to find the handler parameter
            # The handler is usually passed as a parameter before the call
            # Look for function pointers or addresses near the call
            
            # Also analyze the function that calls it
            if func_name not in results:
                result = analyze_function(func)
                if result:
                    results[func_name] = result

# Generate report
output_file = "function_analysis.txt"
try:
    f = open(output_file, 'w')
    f.write("=== Function Analysis ===\n\n")
    from datetime import datetime
    f.write("Generated: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    for func_name in sorted(results.keys()):
        result = results[func_name]
        f.write("=== {} ===\n".format(func_name))
        f.write("Address: {}\n\n".format(result['address']))
        
        regs = result['registers']
        if regs:
            f.write("Register Accesses:\n\n")
            for offset in sorted(regs.keys()):
                reads = regs[offset]['reads']
                writes = regs[offset]['writes']
                f.write("Offset 0x{:04x}:\n".format(offset))
                f.write("  Reads: {}, Writes: {}\n".format(len(reads), len(writes)))
                
                if reads:
                    f.write("  Read examples:\n")
                    for read in reads[:5]:
                        f.write("    {}: {}\n".format(read['address'], read['instruction']))
                
                if writes:
                    f.write("  Write examples:\n")
                    for write in writes[:5]:
                        f.write("    {}: {}\n".format(write['address'], write['instruction']))
                f.write("\n")
        else:
            f.write("No register accesses found\n")
        f.write("\n")
    
    f.close()
    print("\nReport saved to: {}".format(output_file))
except Exception as e:
    print("ERROR: {}".format(e))

print("\n=== Complete ===")
