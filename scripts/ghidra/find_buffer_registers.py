"""
Ghidra script to find DMA buffer address registers

This script searches for:
1. AllocateCommonBuffer calls
2. Buffer address writes to MMIO
3. Buffer size/position registers
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.symbol import Symbol
from ghidra.util.task import ConsoleTaskMonitor

buffer_registers = {}  # offset -> list of accesses
dma_functions = []

def find_dma_functions():
    """Find DMA/buffer allocation functions"""
    print("=== Finding DMA/Buffer Functions ===")
    
    dma_keywords = [
        "AllocateCommonBuffer",
        "GetScatterGatherList",
        "MapTransfer",
        "AllocateContiguous",
        "MmAllocateContiguousMemory"
    ]
    
    symbol_table = currentProgram.getSymbolTable()
    
    for keyword in dma_keywords:
        symbols = list(symbol_table.getSymbols(keyword))
        if not symbols:
            # Try external symbols
            for sym in symbol_table.getExternalSymbols():
                if sym.getName() == keyword:
                    symbols = [sym]
                    break
        for sym in symbols:
            print("Found: {} at {}".format(keyword, sym.getAddress()))
            dma_functions.append({
                'name': keyword,
                'address': sym.getAddress()
            })
            
            # Find all references
            refs = getReferencesTo(sym.getAddress())
            print("  References:")
            for ref in refs:
                from_addr = ref.getFromAddress()
                func = getFunctionContaining(from_addr)
                print("    {} at {}".format(
                    func.getName() if func else "UNKNOWN", from_addr))

def find_buffer_address_writes():
    """Find where buffer addresses are written to MMIO registers"""
    print("\n=== Finding Buffer Address Writes ===")
    
    # Look for patterns like:
    # MOV [MMIO_base + offset], buffer_address
    # Where buffer_address is likely a large value (physical address)
    
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(True)
    
    for inst in inst_iter:
        mnemonic = inst.getMnemonicString()
        
        if mnemonic == "MOV":
            ops = inst.getOperands()
            if len(ops) >= 2:
                # Check if destination is MMIO (address expression)
                dest = ops[0]
                src = ops[1]
                
                if dest and dest.isAddress():
                    # Check if source is a register that might hold buffer address
                    if src and src.isRegister():
                        # This might be writing a buffer address
                        # Try to trace back to see if src holds a buffer address
                        addr = inst.getAddress()
                        func = getFunctionContaining(addr)
                        print("Potential buffer write at {} in {}: {}".format(
                            addr, func.getName() if func else "UNKNOWN", inst))

def analyze_buffer_related_functions():
    """Analyze functions that use DMA to find buffer registers"""
    print("\n=== Analyzing Buffer-Related Functions ===")
    
    # For each DMA function, trace where the buffer address goes
    for dma_func in dma_functions:
        print("\nTracing: {}".format(dma_func['name']))
        
        refs = getReferencesTo(dma_func['address'])
        for ref in refs:
            from_addr = ref.getFromAddress()
            func = getFunctionContaining(from_addr)
            
            if func:
                print("  In function: {}".format(func.getName()))
                # Analyze this function to find buffer address usage
                analyze_function_for_buffer_writes(func)

def analyze_function_for_buffer_writes(func):
    """Analyze a function to find where buffer addresses are written"""
    body = func.getBody()
    listing = currentProgram.getListing()
    inst_iter = listing.getInstructions(body, True)
    
    buffer_vars = set()
    
    # First pass: find where buffer is allocated/stored
    for inst in inst_iter:
        mnemonic = inst.getMnemonicString()
        if mnemonic == "MOV":
            ops = inst.getOperands()
            if len(ops) >= 2:
                # Check if this is storing a buffer address
                # (usually from a function return)
                src = ops[1]
                if src and src.isRegister():
                    # Might be storing buffer address
                    dest = ops[0]
                    if dest and dest.isAddress():
                        # Storing to memory - might be buffer variable
                        buffer_vars.add(str(dest))
    
    # Second pass: find where buffer variables are written to MMIO
    inst_iter = listing.getInstructions(body, True)
    for inst in inst_iter:
        mnemonic = inst.getMnemonicString()
        if mnemonic == "MOV":
            ops = inst.getOperands()
            if len(ops) >= 2:
                dest = ops[0]
                src = ops[1]
                
                # Check if writing a buffer variable to MMIO
                if dest and dest.isAddress():
                    # Extract offset if possible
                    offset = extract_mmio_offset(dest)
                    if offset is not None and src:
                        # This might be a buffer register write
                        print("    Potential buffer register at offset 0x{:x}: {}".format(
                            offset, inst))

def extract_mmio_offset(operand):
    """Extract MMIO offset from operand"""
    # This is simplified - real implementation would need to
    # analyze address expressions more carefully
    if operand and operand.isAddress():
        # Try to extract offset from address calculation
        # This would require more sophisticated analysis
        pass
    return None

def save_results():
    """Save results to JSON file"""
    import os
    import json
    
    results = {
        'dma_functions': dma_functions,
        'buffer_registers': {str(k): v for k, v in buffer_registers.items()},
        'summary': {
            'dma_functions_found': len(dma_functions),
            'buffer_registers_found': len(buffer_registers)
        }
    }
    
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    output_file = os.path.join(script_dir, "buffer_registers.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to: {}".format(output_file))

# Main execution
if __name__ == "__main__":
    print("=" * 60)
    print("DMA Buffer Register Discovery Script")
    print("=" * 60)
    
    find_dma_functions()
    find_buffer_address_writes()
    analyze_buffer_related_functions()
    save_results()
    
    print("\n=== Analysis Complete ===")
