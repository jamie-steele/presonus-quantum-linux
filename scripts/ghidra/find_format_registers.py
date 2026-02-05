"""
Ghidra script to find format and sample rate registers in pae_quantum.sys

This script searches for:
1. Common sample rate values (44100, 48000, 96000, 192000, etc.)
2. Format-related constants (16-bit, 24-bit, 32-bit, channels)
3. Where these values are written to MMIO registers
4. Control register bit fields related to format/sample rate

Usage:
  In Ghidra: Window > Python > Run script
  Or headless: analyzeHeadless <project> <project_name> -process pae_quantum.sys -postScript find_format_registers.py
"""

# Ghidra script - compatible with both Jython (analyzeHeadless) and PyGhidra
from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.scalar import Scalar
from ghidra.program.model.symbol import Symbol
from ghidra.util.task import ConsoleTaskMonitor

# Jython-compatible imports
# Note: Jython has json module, but we'll use simple string output for compatibility
import sys

# Results storage
sample_rate_findings = []  # List of (value, address, function, context)
format_findings = []  # List of (value, address, function, context)
register_writes_with_values = []  # List of (offset, value, address, function)

# Common sample rates
COMMON_SAMPLE_RATES = [
    44100, 48000, 88200, 96000, 176400, 192000,
    22050, 24000, 32000, 8000, 16000, 11025, 12000
]

# Format-related constants
FORMAT_CONSTANTS = [
    16, 24, 32,  # Bit depths
    1, 2, 4, 8, 16, 24, 26, 32,  # Channel counts
    0x10, 0x18, 0x20,  # Common bit depth masks
    0x1, 0x2, 0x4, 0x8, 0x10, 0x20,  # Channel masks
]

def get_function_name(address):
    """Get function name containing the given address"""
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

def get_instruction_context(inst, context_lines=3):
    """Get context around an instruction"""
    addr = inst.getAddress()
    func = getFunctionContaining(addr)
    func_name = func.getName() if func else "UNKNOWN"
    
    # Get surrounding instructions
    context = []
    listing = currentProgram.getListing()
    
    # Get previous instructions
    prev_addr = addr
    for i in range(context_lines):
        prev_inst = listing.getInstructionBefore(prev_addr)
        if prev_inst:
            context.insert(0, str(prev_inst))
            prev_addr = prev_inst.getAddress()
        else:
            break
    
    # Current instruction
    context.append(">>> " + str(inst) + " <<<")
    
    # Get next instructions
    next_addr = addr
    for i in range(context_lines):
        next_inst = listing.getInstructionAfter(next_addr)
        if next_inst:
            context.append(str(next_inst))
            next_addr = next_inst.getAddress()
        else:
            break
    
    return {
        'function': func_name,
        'address': str(addr),
        'instructions': context
    }

def search_for_sample_rates():
    """Search for common sample rate values"""
    print("\n=== Searching for Sample Rate Values ===")
    
    listing = currentProgram.getListing()
    memory = currentProgram.getMemory()
    
    found_count = 0
    
    for rate in COMMON_SAMPLE_RATES:
        # Search for the value as a scalar
        # Also try as hex
        rate_hex = rate
        
        # Search in instructions
        inst_iter = listing.getInstructions(True)
        for inst in inst_iter:
            # Check all operands for this value
            num_ops = inst.getNumOperands()
            for i in range(num_ops):
                op = inst.getOpObjects(i)
                if op:
                    for obj in op:
                        if hasattr(obj, 'getScalar'):
                            scalar = obj.getScalar()
                            if scalar:
                                val = scalar.getUnsignedValue()
                                if val == rate:
                                    context = get_instruction_context(inst)
                                    sample_rate_findings.append({
                                        'value': rate,
                                        'context': context
                                    })
                                    found_count += 1
                                    print("  Found {} Hz at {} in {}".format(
                                        rate, context['address'], context['function']))
    
    print("  Total sample rate references found: {}".format(found_count))
    return found_count

def search_for_format_constants():
    """Search for format-related constants"""
    print("\n=== Searching for Format Constants ===")
    
    listing = currentProgram.getListing()
    found_count = 0
    
    for fmt_val in FORMAT_CONSTANTS:
        inst_iter = listing.getInstructions(True)
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
                                if val == fmt_val:
                                    # Check if this is part of a register write
                                    mnemonic = inst.getMnemonicString()
                                    if mnemonic in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"]:
                                        context = get_instruction_context(inst)
                                        format_findings.append({
                                            'value': fmt_val,
                                            'context': context
                                        })
                                        found_count += 1
                                        if found_count <= 20:  # Limit output
                                            print("  Found format constant {} at {} in {}".format(
                                                fmt_val, context['address'], context['function']))
    
    print("  Total format constant references found: {}".format(found_count))
    return found_count

def trace_value_to_register(value, max_depth=10):
    """Trace a value to see if it's written to a register"""
    print("\n=== Tracing Value {} to Registers ===".format(value))
    
    listing = currentProgram.getListing()
    found_writes = []
    
    # Find all instructions that use this value
    inst_iter = listing.getInstructions(True)
    for inst in inst_iter:
        mnemonic = inst.getMnemonicString()
        
        # Check if this instruction writes to memory (potential register write)
        if mnemonic in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"]:
            num_ops = inst.getNumOperands()
            if num_ops >= 2:
                # Check if first operand is memory (register write)
                dest_op = inst.getOpObjects(0)
                src_op = inst.getOpObjects(1)
                
                # Check if source contains our value
                has_value = False
                if src_op:
                    for obj in src_op:
                        if hasattr(obj, 'getScalar'):
                            scalar = obj.getScalar()
                            if scalar and scalar.getUnsignedValue() == value:
                                has_value = True
                                break
                
                if has_value:
                    # Check if destination is a register offset
                    if dest_op:
                        for obj in dest_op:
                            # Try to extract offset from address expression
                            # This is simplified - real analysis would need data flow
                            context = get_instruction_context(inst)
                            found_writes.append({
                                'value': value,
                                'instruction': str(inst),
                                'context': context
                            })
    
    print("  Found {} potential register writes with value {}".format(len(found_writes), value))
    return found_writes

def search_for_register_writes_near_values():
    """Find register writes that happen near sample rate/format value usage"""
    print("\n=== Finding Register Writes Near Format/Sample Rate Values ===")
    
    listing = currentProgram.getListing()
    all_findings = []
    
    # Combine all interesting values
    interesting_values = COMMON_SAMPLE_RATES + FORMAT_CONSTANTS
    
    for value in interesting_values:
        # Find instructions using this value
        inst_iter = listing.getInstructions(True)
        for inst in inst_iter:
            # Check if instruction uses this value
            num_ops = inst.getNumOperands()
            uses_value = False
            for i in range(num_ops):
                op = inst.getOpObjects(i)
                if op:
                    for obj in op:
                        if hasattr(obj, 'getScalar'):
                            scalar = obj.getScalar()
                            if scalar and scalar.getUnsignedValue() == value:
                                uses_value = True
                                break
                if uses_value:
                    break
            
            if uses_value:
                # Look for register writes in nearby instructions (within 20 instructions)
                addr = inst.getAddress()
                func = getFunctionContaining(addr)
                if func:
                    # Search forward and backward for register writes
                    search_range = 20
                    current_addr = addr
                    
                    # Search forward
                    for i in range(search_range):
                        next_inst = listing.getInstructionAfter(current_addr)
                        if not next_inst:
                            break
                        current_addr = next_inst.getAddress()
                        
                        # Check if this is a register write
                        mnemonic = next_inst.getMnemonicString()
                        if mnemonic in ["MOV", "OR", "AND", "XOR"]:
                            num_ops = next_inst.getNumOperands()
                            if num_ops >= 2:
                                # Check if writing to memory (potential register)
                                dest_op = next_inst.getOpObjects(0)
                                if dest_op:
                                    # Try to extract offset
                                    context = get_instruction_context(next_inst)
                                    all_findings.append({
                                        'value': value,
                                        'nearby_write': str(next_inst),
                                        'context': context,
                                        'distance': i + 1
                                    })
                                        if len(all_findings) <= 30:  # Limit output
                                            print("  Value {} used, nearby write at {} (distance {})".format(
                                                value, context['address'], i + 1))
    
    print("  Total register writes near format/sample rate values: {}".format(len(all_findings)))
    return all_findings

def generate_report():
    """Generate a report of findings"""
    print("\n=== Generating Report ===")
    
    # Save to file (simple text format for Jython compatibility)
    output_file = "format_registers.txt"
    try:
        f = open(output_file, 'w')
        f.write("=== Format and Sample Rate Register Analysis ===\n\n")
        f.write("Sample Rate References: {}\n".format(len(sample_rate_findings)))
        f.write("Format Constant References: {}\n\n".format(len(format_findings)))
        
        f.write("=== Sample Rate Findings ===\n")
        for i, finding in enumerate(sample_rate_findings[:50]):  # Limit output
            ctx = finding['context']
            f.write("\n{}. Value: {} Hz\n".format(i+1, finding['value']))
            f.write("   Function: {}\n".format(ctx['function']))
            f.write("   Address: {}\n".format(ctx['address']))
            f.write("   Instructions:\n")
            for inst in ctx['instructions']:
                f.write("     {}\n".format(inst))
        
        f.write("\n=== Format Constant Findings (first 50) ===\n")
        for i, finding in enumerate(format_findings[:50]):
            ctx = finding['context']
            f.write("\n{}. Value: {}\n".format(i+1, finding['value']))
            f.write("   Function: {}\n".format(ctx['function']))
            f.write("   Address: {}\n".format(ctx['address']))
            f.write("   Instruction: {}\n".format(ctx['instructions'][0] if ctx['instructions'] else 'N/A'))
        
        f.close()
        print("  Report saved to: {}".format(output_file))
    except Exception as e:
        print("  ERROR saving report: {}".format(e))
    
    # Print summary
    print("\n=== Summary ===")
    print("  Sample rate references: {}".format(len(sample_rate_findings)))
    print("  Format constant references: {}".format(len(format_findings)))
    
    return {
        'sample_rate_count': len(sample_rate_findings),
        'format_count': len(format_findings)
    }

# Main execution - works with both PyGhidra CLI and analyzeHeadless
# PyGhidra automatically provides currentProgram
try:
    # Check if currentProgram is available (PyGhidra/analyzeHeadless)
    program = currentProgram
    program_name = program.getName()
except NameError:
    print("ERROR: currentProgram not available. This script must be run from Ghidra.")
    print("Make sure you're using: python -m pyghidra <binary> <script>")
    sys.exit(1)

print("=" * 60)
print("Finding Format and Sample Rate Registers")
print("=" * 60)
print("Program: {}".format(program_name))
print("")

# Check if program is analyzed
listing = currentProgram.getListing()
if not listing:
    print("ERROR: Program listing not available")
    print("The program may need to be analyzed first.")
else:
    # Run searches
    search_for_sample_rates()
    search_for_format_constants()
    search_for_register_writes_near_values()
    
    # Generate report
    report = generate_report()
    
    print("\n=== Analysis Complete ===")
    print("Check format_registers.txt for detailed results")
