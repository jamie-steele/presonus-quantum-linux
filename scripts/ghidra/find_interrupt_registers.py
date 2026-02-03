"""
Ghidra script to find interrupt status and acknowledge registers

This script:
1. Finds interrupt handler functions
2. Analyzes interrupt handlers for register reads/writes
3. Identifies interrupt status and acknowledge registers
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.symbol import Symbol
from ghidra.util.task import ConsoleTaskMonitor

interrupt_handlers = []
interrupt_registers = {
    'status': [],  # Registers read to check interrupt status
    'ack': []      # Registers written to acknowledge interrupts
}

def find_interrupt_handlers():
    """Find interrupt handler functions"""
    print("=== Finding Interrupt Handlers ===")
    
    # Find IoConnectInterruptEx
    symbol_table = currentProgram.getSymbolTable()
    symbols = list(symbol_table.getSymbols("IoConnectInterruptEx"))
    
    if not symbols:
        print("  IoConnectInterruptEx not found in symbol table")
        # Try external symbols
        for sym in symbol_table.getExternalSymbols():
            if sym.getName() == "IoConnectInterruptEx":
                symbols = [sym]
                break
    
    if not symbols:
        print("  IoConnectInterruptEx not found")
        return
    
    io_connect = symbols[0]
    print("Found IoConnectInterruptEx at: {}".format(io_connect.getAddress()))
    
    # Find all references
    refs = getReferencesTo(io_connect.getAddress())
    for ref in refs:
        from_addr = ref.getFromAddress()
        func = getFunctionContaining(from_addr)
        
        if func:
            print("  Called from: {} at {}".format(func.getName(), from_addr))
            
            # Analyze the function to find the interrupt handler parameter
            analyze_interrupt_setup(func, from_addr)

def analyze_interrupt_setup(func, call_addr):
    """Analyze function that sets up interrupt to find handler"""
    print("\n  Analyzing interrupt setup in: {}".format(func.getName()))
    
    # Look for the interrupt handler function pointer
    # Usually passed as a parameter or set in a structure before IoConnectInterruptEx
    
    listing = currentProgram.getListing()
    body = func.getBody()
    inst_iter = listing.getInstructions(body, True)
    
    # Look backwards from the call to find handler setup
    call_inst = getInstructionAt(call_addr)
    if not call_inst:
        return
    
    # Check instructions before the call
    for i in range(20):
        prev_inst = call_inst.getPrevious()
        if not prev_inst:
            break
        
        mnemonic = prev_inst.getMnemonicString()
        
        # Look for LEA or MOV that might set handler address
        if mnemonic in ["LEA", "MOV"]:
            ops = prev_inst.getOperands()
            if len(ops) >= 2:
                # Check if this is loading a function address
                src = ops[1]
                if src and src.isAddress():
                    target_func = getFunctionAt(src.getAddress())
                    if target_func:
                        print("    Found potential interrupt handler: {} at {}".format(
                            target_func.getName(), src.getAddress()))
                        interrupt_handlers.append({
                            'function': target_func,
                            'setup_function': func,
                            'address': src.getAddress()
                        })
        
        call_inst = prev_inst

def analyze_interrupt_handler(handler_func):
    """Analyze an interrupt handler to find register accesses"""
    print("\n=== Analyzing Interrupt Handler: {} ===".format(handler_func.getName()))
    
    listing = currentProgram.getListing()
    body = handler_func.getBody()
    inst_iter = listing.getInstructions(body, True)
    
    reads = []
    writes = []
    
    for inst in inst_iter:
        mnemonic = inst.getMnemonicString()
        addr = inst.getAddress()
        
        # Look for memory reads (interrupt status)
        if mnemonic in ["MOV", "CMP", "TEST", "AND", "OR"]:
            ops = inst.getOperands()
            
            # Check for reads from MMIO
            if len(ops) >= 2:
                src = ops[1]
                if src and src.isAddress():
                    # This might be reading interrupt status
                    offset = extract_mmio_offset(src)
                    if offset is not None:
                        reads.append({
                            'offset': offset,
                            'address': addr,
                            'instruction': str(inst)
                        })
                        print("  Read from offset 0x{:x} at {}: {}".format(
                            offset, addr, inst))
        
        # Look for memory writes (interrupt acknowledge)
        if mnemonic in ["MOV", "OR", "AND", "XOR"]:
            ops = inst.getOperands()
            
            if len(ops) >= 2:
                dest = ops[0]
                if dest and dest.isAddress():
                    # This might be writing to acknowledge register
                    offset = extract_mmio_offset(dest)
                    if offset is not None:
                        value = None
                        if len(ops) > 1:
                            src = ops[1]
                            if src and src.isScalar():
                                value = src.getScalar().getUnsignedValue()
                        
                        writes.append({
                            'offset': offset,
                            'value': value,
                            'address': addr,
                            'instruction': str(inst)
                        })
                        print("  Write to offset 0x{:x} (value: {}) at {}: {}".format(
                            offset, value, addr, inst))
    
    # Categorize registers
    # Status registers are typically read early in handler
    # Ack registers are typically written after handling
    if reads:
        print("\n  Potential interrupt status registers:")
        for read in reads[:5]:  # First few reads
            interrupt_registers['status'].append(read)
            print("    Offset 0x{:x}".format(read['offset']))
    
    if writes:
        print("\n  Potential interrupt acknowledge registers:")
        for write in writes:
            interrupt_registers['ack'].append(write)
            print("    Offset 0x{:x} (write value: {})".format(
                write['offset'], write['value']))

def extract_mmio_offset(operand):
    """Extract MMIO offset from operand (simplified)"""
    # This would need more sophisticated analysis
    # For now, return None - would need to trace MMIO base variable
    return None

def save_results():
    """Save results to JSON file"""
    import os
    import json
    
    results = {
        'interrupt_handlers': [
            {
                'function': h['function'].getName() if h.get('function') else 'UNKNOWN',
                'address': str(h.get('address', '')),
                'setup_function': h['setup_function'].getName() if h.get('setup_function') else 'UNKNOWN'
            }
            for h in interrupt_handlers
        ],
        'interrupt_registers': {
            'status': interrupt_registers['status'],
            'ack': interrupt_registers['ack']
        },
        'summary': {
            'handlers_found': len(interrupt_handlers),
            'status_registers': len(interrupt_registers['status']),
            'ack_registers': len(interrupt_registers['ack'])
        }
    }
    
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    output_file = os.path.join(script_dir, "interrupt_registers.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to: {}".format(output_file))

# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("Interrupt Register Discovery Script")
    print("=" * 60)
    
    find_interrupt_handlers()
    
    # Analyze each interrupt handler
    for handler_info in interrupt_handlers:
        if handler_info.get('function'):
            analyze_interrupt_handler(handler_info['function'])
    
    save_results()
    
    print("\n=== Summary ===")
    print("Found {} interrupt handlers".format(len(interrupt_handlers)))
    print("Found {} potential status registers".format(len(interrupt_registers['status'])))
    print("Found {} potential ack registers".format(len(interrupt_registers['ack'])))
