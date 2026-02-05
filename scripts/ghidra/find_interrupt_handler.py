"""
Find interrupt handler and analyze interrupt-related registers
Looks for IoConnectInterruptEx and traces interrupt handling
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.symbol import Symbol
import sys

interrupt_findings = []

def get_function_name(address):
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

print("=" * 60)
print("Interrupt Handler Analysis")
print("=" * 60)

try:
    program = currentProgram
    print("Program: {}".format(program.getName()))
except:
    print("ERROR: currentProgram not available")
    sys.exit(1)

listing = currentProgram.getListing()
symbol_table = currentProgram.getSymbolTable()

print("\n=== Finding IoConnectInterruptEx ===")

# Find IoConnectInterruptEx symbol
interrupt_symbols = list(symbol_table.getSymbols("IoConnectInterruptEx"))
if not interrupt_symbols:
    # Try external symbols
    for sym in symbol_table.getExternalSymbols():
        if sym.getName() == "IoConnectInterruptEx":
            interrupt_symbols = [sym]
            break

if interrupt_symbols:
    interrupt_symbol = interrupt_symbols[0]
    print("Found IoConnectInterruptEx at: {}".format(interrupt_symbol.getAddress()))
    
    # Find references to it
    refs = getReferencesTo(interrupt_symbol.getAddress())
    print("Found {} references".format(len(list(refs))))
    
    for ref in refs:
        from_addr = ref.getFromAddress()
        func = getFunctionContaining(from_addr)
        func_name = func.getName() if func else "UNKNOWN"
        
        print("\n  Called from: {} at {}".format(func_name, from_addr))
        
        # Look for the interrupt handler function pointer (usually 3rd or 4th parameter)
        # In Windows drivers, IoConnectInterruptEx takes the handler function as a parameter
        # We need to trace back to find what function is passed
        
        interrupt_findings.append({
            'caller': func_name,
            'address': str(from_addr)
        })
else:
    print("IoConnectInterruptEx not found in symbol table")

print("\n=== Searching for Interrupt-Related Registers ===")

# Look for common interrupt register patterns
# Interrupt status is often read, then acknowledged by writing back
inst_iter = listing.getInstructions(True)
interrupt_registers = {}

for inst in inst_iter:
    mnemonic = inst.getMnemonicString()
    inst_str = str(inst)
    addr = inst.getAddress()
    func = getFunctionContaining(addr)
    func_name = func.getName() if func else "UNKNOWN"
    
    # Look for read-then-write patterns (common for interrupt status)
    # Pattern: MOV reg, [base+offset] followed by MOV [base+offset], reg
    if mnemonic in ["MOV", "OR", "AND", "XOR"] and "[" in inst_str:
        import re
        hex_pattern = r'\[.*?\+0x([0-9a-fA-F]+)\]'
        matches = re.findall(hex_pattern, inst_str, re.IGNORECASE)
        
        for match in matches:
            try:
                offset = int(match, 16)
                # Common interrupt register offsets
                if offset in [0x4, 0x8, 0x10, 0x14, 0x100, 0x104, 0x108]:
                    if offset not in interrupt_registers:
                        interrupt_registers[offset] = {'reads': [], 'writes': []}
                    
                    is_write = mnemonic in ["MOV", "OR", "AND", "XOR"] and "[" in inst_str
                    is_read = mnemonic == "MOV" and "[" in inst_str
                    
                    access = {
                        'address': str(addr),
                        'function': func_name,
                        'instruction': inst_str,
                        'type': 'WRITE' if is_write else 'READ'
                    }
                    
                    if is_write:
                        interrupt_registers[offset]['writes'].append(access)
                    elif is_read:
                        interrupt_registers[offset]['reads'].append(access)
            except:
                pass

print("\n=== Interrupt Register Candidates ===")
for offset in sorted(interrupt_registers.keys()):
    reg = interrupt_registers[offset]
    reads = len(reg['reads'])
    writes = len(reg['writes'])
    print("Offset 0x{:04x}: {} reads, {} writes".format(offset, reads, writes))
    
    # If we have both reads and writes, it's likely an interrupt status register
    if reads > 0 and writes > 0:
        print("  -> Likely interrupt status register (read status, write to acknowledge)")

# Generate report
output_file = "interrupt_analysis.txt"
try:
    f = open(output_file, 'w')
    f.write("=== Interrupt Handler Analysis ===\n\n")
    from datetime import datetime
    f.write("Generated: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    f.write("=== IoConnectInterruptEx Calls ===\n\n")
    for finding in interrupt_findings:
        f.write("Called from: {} at {}\n".format(finding['caller'], finding['address']))
        f.write("\n")
    
    f.write("\n=== Interrupt Register Candidates ===\n\n")
    for offset in sorted(interrupt_registers.keys()):
        reg = interrupt_registers[offset]
        f.write("Offset 0x{:04x}:\n".format(offset))
        f.write("  Reads: {}, Writes: {}\n".format(len(reg['reads']), len(reg['writes'])))
        if len(reg['reads']) > 0 and len(reg['writes']) > 0:
            f.write("  -> Likely interrupt status/ack register\n")
        f.write("\n")
        
        # Show examples
        if reg['reads']:
            f.write("  Read examples:\n")
            for read in reg['reads'][:3]:
                f.write("    {} in {}\n".format(read['instruction'], read['function']))
        if reg['writes']:
            f.write("  Write examples:\n")
            for write in reg['writes'][:3]:
                f.write("    {} in {}\n".format(write['instruction'], write['function']))
        f.write("\n")
    
    f.close()
    print("\nReport saved to: {}".format(output_file))
except Exception as e:
    print("ERROR saving report: {}".format(e))

print("\n=== Complete ===")
