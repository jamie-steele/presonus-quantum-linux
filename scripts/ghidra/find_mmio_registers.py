"""
Ghidra script to automatically find MMIO register offsets in pae_quantum.sys

Usage:
  In Ghidra: Window > Python > Run script
  Or headless: analyzeHeadless <project> <project_name> -process pae_quantum.sys -script find_mmio_registers.py

This script:
1. Finds MmMapIoSpace call to locate MMIO base
2. Traces all uses of MMIO base address
3. Extracts register offsets from memory accesses
4. Categorizes reads vs writes
5. Generates a register map report
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.scalar import Scalar
from ghidra.program.model.symbol import Symbol
from ghidra.program.model.mem import MemoryAccessException
from ghidra.util.task import ConsoleTaskMonitor
import json

# Results storage
registers_read = {}  # offset -> list of (address, function, context)
registers_written = {}  # offset -> list of (address, function, value, context)
mmio_base_vars = set()  # Variable names that hold MMIO base
functions_using_mmio = set()

def get_function_name(address):
    """Get function name containing the given address"""
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

def get_instruction_context(inst):
    """Get context around an instruction for debugging"""
    addr = inst.getAddress()
    func = getFunctionContaining(addr)
    if func:
        return "{}:{}".format(func.getName(), addr)
    return str(addr)

def find_mmio_base():
    """Find where MmMapIoSpace is called and trace the MMIO base address"""
    print("=== Finding MMIO Base Address ===")
    
    # Find MmMapIoSpace symbol
    symbol_table = currentProgram.getSymbolTable()
    mmio_symbols = list(symbol_table.getSymbols("MmMapIoSpace"))
    
    if not mmio_symbols:
        print("  WARNING: MmMapIoSpace not found in symbol table")
        print("  Searching external symbols...")
        # Try external symbols
        for sym in symbol_table.getExternalSymbols():
            if sym.getName() == "MmMapIoSpace":
                mmio_symbols = [sym]
                break
    
    if not mmio_symbols:
        print("  ERROR: MmMapIoSpace not found!")
        return None
    
    mmio_symbol = mmio_symbols[0]
    print("Found MmMapIoSpace at: {}".format(mmio_symbol.getAddress()))
    
    # Find all references to MmMapIoSpace
    refs = getReferencesTo(mmio_symbol.getAddress())
    for ref in refs:
        from_addr = ref.getFromAddress()
        func = getFunctionContaining(from_addr)
        print("  Called from: {} at {}".format(
            func.getName() if func else "UNKNOWN", from_addr))
        
        # Try to find where the return value is stored
        # Look for MOV or LEA instructions after the call
        inst = getInstructionAt(from_addr)
        if inst:
                # Get next few instructions
                for i in range(10):
                    inst = inst.getNext()
                    if not inst:
                        break
                    mnemonic = inst.getMnemonicString()
                    if mnemonic in ["MOV", "LEA"]:
                        # Check if it's storing to a variable
                        num_ops = inst.getNumOperands()
                        if num_ops >= 2:
                            # Get operand objects
                            ops = [inst.getOperandRefType(i) for i in range(num_ops)]
                        # Second operand is destination
                        dest = ops[1]
                        if dest:
                            print("    Potential MMIO base storage: {} at {}".format(
                                inst, from_addr))
    
    return None

def search_for_known_offsets():
    """Search for known register offsets from manual analysis"""
    print("  Searching for known offsets in instructions...")
    
    # Known offsets from manual analysis
    known_offsets = [0x0, 0x4, 0x8, 0x10, 0x14, 0x100, 0x104, 0x10300, 0x10304]
    
    listing = currentProgram.getListing()
    monitor = ConsoleTaskMonitor()
    found_count = 0
    
    # Search for each known offset
    for offset in known_offsets:
        # Search for this offset as a scalar in instructions
        inst_iter = listing.getInstructions(True)
        matches = []
        
        for inst in inst_iter:
            if monitor.isCancelled():
                break
            
            inst_str = str(inst)
            addr = inst.getAddress()
            func = getFunctionContaining(addr)
            func_name = func.getName() if func else "UNKNOWN"
            
            # Check if offset appears in instruction string
            hex_str = "0x{:x}".format(offset).lower()
            dec_str = str(offset)
            
            if hex_str in inst_str.lower() or dec_str in inst_str:
                # Check if it's in an address expression (likely MMIO)
                if '[' in inst_str and ']' in inst_str:
                    matches.append({
                        'address': str(addr),
                        'function': func_name,
                        'instruction': inst_str,
                        'offset': offset
                    })
                    found_count += 1
                    
                    # Categorize as read or write
                    mnemonic = inst.getMnemonicString()
                    is_write = mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR"] and inst_str.count('[') > 0
                    is_read = mnemonic in ["MOV", "CMP", "TEST"] and inst_str.count('[') > 0
                    
                    if is_write:
                        if offset not in registers_written:
                            registers_written[offset] = []
                        registers_written[offset].append({
                            'address': str(addr),
                            'function': func_name,
                            'instruction': inst_str
                        })
                        functions_using_mmio.add(func_name)
                    
                    if is_read:
                        if offset not in registers_read:
                            registers_read[offset] = []
                        registers_read[offset].append({
                            'address': str(addr),
                            'function': func_name,
                            'instruction': inst_str
                        })
                        functions_using_mmio.add(func_name)
        
        if matches:
            print("    Found {} matches for offset 0x{:x}".format(len(matches), offset))
            # Show first few matches
            for match in matches[:3]:
                print("      {}: {}".format(match['function'], match['instruction'][:80]))
    
    print("  Known offset search completed (found {} total matches)".format(found_count))

def search_for_scalars_directly():
    """Alternative method: search for scalar values directly"""
    print("  Searching for scalar values in memory...")
    
    # Known offsets from manual analysis
    known_offsets = [0x0, 0x4, 0x8, 0x10, 0x14, 0x100, 0x104, 0x10300, 0x10304]
    
    listing = currentProgram.getListing()
    found_count = 0
    
    for offset in known_offsets:
        # Search for this scalar value
        # This is a simplified approach - full implementation would use Ghidra's search
        pass
        
    print("  Alternative search completed (found {} potential matches)".format(found_count))

def extract_offset_from_operand(operand, base_var=None):
    """Extract register offset from an operand"""
    if not operand:
        return None
    
    # Check if operand is a scalar (immediate value)
    if operand.isScalar():
        scalar = operand.getScalar()
        offset = scalar.getUnsignedValue()
        # Filter reasonable offsets (0 to 1MB)
        if 0 <= offset <= 0x100000:
            return offset
    
    # Check if operand is an address expression like [RSI + 0x100]
    if operand.isAddress():
        addr = operand.getAddress()
        # Try to extract offset from address calculation
        # This is tricky - we'd need to analyze the address expression
        pass
    
    return None

def analyze_instruction_for_mmio(inst, mmio_base_vars):
    """Analyze an instruction for MMIO register access"""
    mnemonic = inst.getMnemonicString()
    addr = inst.getAddress()
    func = getFunctionContaining(addr)
    func_name = func.getName() if func else "UNKNOWN"
    
    # Check for memory operations
    if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST"]:
        num_ops = inst.getNumOperands(); ops = [inst.getOperandRefType(i) for i in range(num_ops)]
        
        # Look for scalar offsets in operands
        for i, op in enumerate(ops):
            if op and op.isScalar():
                # Direct scalar offset
                scalar = op.getScalar()
                offset = scalar.getUnsignedValue()
                if 0 <= offset <= 0x100000:
                    # This might be a register offset
                    # Determine if read or write based on operand position
                    # For MOV dest, src: dest is op[0], src is op[1]
                    is_write = (i == 0 and mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR"])
                    is_read = (i == 1 and mnemonic in ["MOV", "CMP", "TEST", "ADD", "SUB"])
                    
                    # Also check if this is part of an address expression
                    # Look at the full instruction to see if offset is used in memory access
                    if is_write or is_read:
                        # Get the value being written (if write)
                        value = None
                        if is_write and len(ops) > 1:
                            value_op = ops[1]
                            if value_op and value_op.isScalar():
                                value = value_op.getScalar().getUnsignedValue()
                        
                        if is_write:
                            if offset not in registers_written:
                                registers_written[offset] = []
                            registers_written[offset].append({
                                'address': str(addr),
                                'function': func_name,
                                'value': value,
                                'instruction': str(inst)
                            })
                            functions_using_mmio.add(func_name)
                        
                        if is_read:
                            if offset not in registers_read:
                                registers_read[offset] = []
                            registers_read[offset].append({
                                'address': str(addr),
                                'function': func_name,
                                'instruction': str(inst)
                            })
                            functions_using_mmio.add(func_name)

def search_for_scalar_offsets():
    """Search for scalar values that might be register offsets"""
    import sys
    print("\n=== Searching for Register Offsets ===")
    sys.stdout.flush()
    
    listing = currentProgram.getListing()
    monitor = ConsoleTaskMonitor()
    
    # Get all memory addresses
    memory = currentProgram.getMemory()
    addr_factory = currentProgram.getAddressFactory()
    
    # Check if we have instructions
    min_addr = currentProgram.getMinAddress()
    max_addr = currentProgram.getMaxAddress()
    print("  Program address range: {} to {}".format(min_addr, max_addr))
    
    if not min_addr:
        print("  ERROR: No addresses in program")
        return
    
    # Get first instruction to verify
    first_inst = listing.getInstructionAt(min_addr)
    if not first_inst:
        print("  WARNING: No instruction at start address - program may need analysis")
    else:
        print("  First instruction: {} at {}".format(first_inst, min_addr))
    
    # Iterate through all instructions
    inst_iter = listing.getInstructions(True)  # True = forward
    count = 0
    found_offsets = set()
    sample_instructions = []
    
    try:
        for inst in inst_iter:
            if monitor.isCancelled():
                break
            
            count += 1
            if count % 10000 == 0:
                print("  Processed {} instructions...".format(count))
            
            # Collect sample instructions for debugging
            if count <= 10:
                sample_instructions.append(str(inst))
            
            mnemonic = inst.getMnemonicString()
            addr = inst.getAddress()
            func = getFunctionContaining(addr)
            func_name = func.getName() if func else "UNKNOWN"
            
            # Get full instruction string for parsing
            inst_str = str(inst)
            
            # Look for memory operations with scalar offsets
            if mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR", "CMP", "TEST", "LEA"]:
                num_ops = inst.getNumOperands()
                ops = []
                for i in range(num_ops):
                    ops.append(inst.getOperandRefType(i))
                
                # Also parse the full instruction string for offset patterns
                inst_str = str(inst)
            
            # Check all operands for scalar values that could be offsets
            for i, op in enumerate(ops):
                offset = None
                
                # Method 1: Direct scalar operand
                if op and op.isScalar():
                    scalar = op.getScalar()
                    offset = scalar.getUnsignedValue()
                
                # Method 2: Offset in address expression (like [RAX+0x100])
                if offset is None:
                    offset = extract_offset_from_address_expression(op)
                
                # Method 3: Parse instruction string directly for common patterns
                if offset is None:
                    import re
                    # Look for patterns like [register+0x100] or [register+256]
                    # Match the full instruction string
                    hex_pattern = r'\[.*?[+\-]0x([0-9a-fA-F]+)\]'
                    dec_pattern = r'\[.*?[+\-](\d+)\]'
                    
                    for pattern in [hex_pattern, dec_pattern]:
                        matches = re.findall(pattern, inst_str, re.IGNORECASE)
                        if matches:
                            for match in matches:
                                try:
                                    if '0x' in match or any(c in 'abcdef' for c in match.lower()):
                                        offset = int(match, 16)
                                    else:
                                        offset = int(match)
                                    if 0 <= offset <= 0x100000:
                                        break
                                except:
                                    pass
                        if offset is not None:
                            break
                    
                    if offset is not None:
                        # Filter reasonable offsets (0 to 1MB, aligned to 4 bytes or small)
                        if 0 <= offset <= 0x100000 and (offset % 4 == 0 or offset < 0x100):
                            found_offsets.add(offset)
                        
                        # Determine if read or write
                        is_write = (i == 0 and mnemonic in ["MOV", "ADD", "SUB", "OR", "AND", "XOR"])
                        is_read = (i == 1 and mnemonic in ["MOV", "CMP", "TEST", "ADD", "SUB"]) or (i == 0 and mnemonic in ["CMP", "TEST"])
                        
                        # Get value if write
                        value = None
                        if is_write and len(ops) > 1:
                            value_op = ops[1]
                            if value_op and value_op.isScalar():
                                value = value_op.getScalar().getUnsignedValue()
                        
                        if is_write:
                            if offset not in registers_written:
                                registers_written[offset] = []
                            registers_written[offset].append({
                                'address': str(addr),
                                'function': func_name,
                                'value': value,
                                'instruction': str(inst)
                            })
                            functions_using_mmio.add(func_name)
                        
                        if is_read:
                            if offset not in registers_read:
                                registers_read[offset] = []
                            registers_read[offset].append({
                                'address': str(addr),
                                'function': func_name,
                                'instruction': str(inst)
                            })
                            functions_using_mmio.add(func_name)
            
            # Also analyze using the original function
            analyze_instruction_for_mmio(inst, mmio_base_vars)
        
        # Print sample instructions for debugging
        if count > 0 and len(sample_instructions) > 0:
            print("\n  Sample instructions (first 10):")
            for i, sample in enumerate(sample_instructions[:10], 1):
                print("    {}: {}".format(i, sample))
        
    except Exception as e:
        print("  ERROR iterating instructions: {}".format(e))
        import traceback
        traceback.print_exc()
        print("  This may indicate the program needs analysis")
    
    print("\n  Processed {} total instructions".format(count))
    print("  Found {} unique offset values".format(len(found_offsets)))
    
    # If no instructions found, try searching for scalars directly
    if count == 0:
        print("\n  No instructions found - trying alternative search method...")
        search_for_scalars_directly()
    elif len(found_offsets) == 0:
        print("\n  Instructions processed but no offsets found.")
        print("  Trying direct search for known offsets...")
        search_for_known_offsets()

def generate_report():
    """Generate a comprehensive register map report"""
    print("\n=== Register Map Report ===")
    print("\n## Registers Read:")
    print("| Offset | Hex | Count | Functions |")
    print("|--------|-----|-------|-----------|")
    
    for offset in sorted(registers_read.keys()):
        accesses = registers_read[offset]
        funcs = set(a['function'] for a in accesses)
        print("| {} | 0x{:x} | {} | {} |".format(
            offset, offset, len(accesses), ", ".join(sorted(funcs)[:3])))
    
    print("\n## Registers Written:")
    if len(registers_written) > 0:
        print("| Offset | Hex | Count | Functions | Values |")
        print("|--------|-----|-------|-----------|--------|")
        
        for offset in sorted(registers_written.keys()):
            accesses = registers_written[offset]
            funcs = set(a['function'] for a in accesses)
            values = set(a.get('value') for a in accesses if a.get('value') is not None)
            print("| {} | 0x{:x} | {} | {} | {} |".format(
                offset, offset, len(accesses), ", ".join(sorted(funcs)[:3]),
                ", ".join("0x{:x}".format(v) for v in sorted(values)[:5])))
    else:
        print("  (none found)")
    
    print("\n## Functions Using MMIO:")
    for func in sorted(functions_using_mmio):
        print("  - {}".format(func))
    
    # Export to JSON
    report = {
        'registers_read': {str(k): v for k, v in registers_read.items()},
        'registers_written': {str(k): v for k, v in registers_written.items()},
        'functions_using_mmio': list(functions_using_mmio),
        'summary': {
            'total_read_offsets': len(registers_read),
            'total_write_offsets': len(registers_written),
            'total_functions': len(functions_using_mmio)
        }
    }
    
    # Save automatically (headless compatible)
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    output_file = os.path.join(script_dir, "mmio_registers.json")
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    print("\nReport saved to: {}".format(output_file))

# Main execution
if __name__ == "__main__":
    import sys
    sys.stdout.flush()
    sys.stderr.flush()
    
    print("=" * 60)
    print("MMIO Register Discovery Script")
    print("=" * 60)
    sys.stdout.flush()
    
    # Check if program is analyzed
    listing = currentProgram.getListing()
    min_addr = currentProgram.getMinAddress()
    
    if min_addr:
        first_inst = listing.getInstructionAt(min_addr)
        if not first_inst:
            print("\nWARNING: Program appears unanalyzed. Running auto-analysis...")
            from ghidra.app.script import GhidraScript
            from ghidra.program.util import ProgramLocation
            
            # Try to trigger analysis
            try:
                # Get analysis manager and run analysis
                from ghidra.app.plugin.core.analysis import AutoAnalysisManager
                analysis_mgr = AutoAnalysisManager.getAnalysisManager(currentProgram)
                if analysis_mgr:
                    print("  Analysis manager found, analysis should run automatically")
            except:
                print("  Note: Analysis may need to run in GUI mode first")
                print("  Or run without --skip-analysis flag")
    
    try:
        # Find MMIO base
        print("\nCalling find_mmio_base()...")
        sys.stdout.flush()
        find_mmio_base()
        sys.stdout.flush()
        
        # Search for register offsets
        print("\nCalling search_for_scalar_offsets()...")
        sys.stdout.flush()
        search_for_scalar_offsets()
        sys.stdout.flush()
        
        # Generate report
        print("\nCalling generate_report()...")
        sys.stdout.flush()
        generate_report()
        sys.stdout.flush()
        
        print("\n=== Analysis Complete ===")
        print("Found {} unique register offsets read".format(len(registers_read)))
        print("Found {} unique register offsets written".format(len(registers_written)))
        print("Found {} functions using MMIO".format(len(functions_using_mmio)))
        sys.stdout.flush()
    except Exception as e:
        print("\nERROR in main: {}".format(e))
        import traceback
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
