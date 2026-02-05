"""
Focused script to find format and sample rate registers
Searches for sample rate values and traces where they're written to MMIO
"""

from ghidra.program.model.address import Address
from ghidra.program.model.listing import Instruction, InstructionIterator
from ghidra.program.model.scalar import Scalar
import sys

# Sample rates to search for
SAMPLE_RATES = [44100, 48000, 88200, 96000, 176400, 192000, 22050, 24000, 32000, 8000, 16000, 11025, 12000]

# Format values
FORMAT_VALUES = [16, 24, 32]  # Bit depths
CHANNEL_COUNTS = [1, 2, 4, 8, 16, 24, 26, 32]  # Channel counts

results = {
    'sample_rates': [],
    'format_values': [],
    'register_writes_near_values': []
}

def get_function_name(address):
    func = getFunctionContaining(address)
    if func:
        return func.getName()
    return "UNKNOWN"

print("=" * 60)
print("Format and Sample Rate Register Analysis")
print("=" * 60)

try:
    program = currentProgram
    print("Program: {}".format(program.getName()))
except:
    print("ERROR: currentProgram not available")
    sys.exit(1)

listing = currentProgram.getListing()
if not listing:
    print("ERROR: Program listing not available")
    sys.exit(1)

print("\n=== Searching for Sample Rate Values ===")

# Search for sample rate values
for rate in SAMPLE_RATES:
    found = []
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
                            if val == rate:
                                addr = inst.getAddress()
                                func = getFunctionContaining(addr)
                                
                                # Look for nearby register writes (within 50 instructions)
                                nearby_writes = []
                                current_addr = addr
                                
                                # Search forward
                                for j in range(50):
                                    next_inst = listing.getInstructionAfter(current_addr)
                                    if not next_inst:
                                        break
                                    current_addr = next_inst.getAddress()
                                    
                                    next_str = str(next_inst)
                                    if "[" in next_str and next_inst.getMnemonicString() in ["MOV", "OR", "AND", "XOR"]:
                                        # Check if it's writing to a register offset
                                        import re
                                        hex_pattern = r'\[.*?\+0x([0-9a-fA-F]+)\]'
                                        matches = re.findall(hex_pattern, next_str, re.IGNORECASE)
                                        for match in matches:
                                            try:
                                                offset = int(match, 16)
                                                if 0 < offset <= 0x20000 and offset % 4 == 0:
                                                    nearby_writes.append({
                                                        'offset': offset,
                                                        'instruction': next_str,
                                                        'distance': j + 1,
                                                        'address': str(current_addr)
                                                    })
                                            except:
                                                pass
                                
                                found.append({
                                    'value': rate,
                                    'address': str(addr),
                                    'function': func.getName() if func else "UNKNOWN",
                                    'instruction': str(inst),
                                    'nearby_writes': nearby_writes
                                })
                                break
    
    if found:
        results['sample_rates'].extend(found)
        print("  {} Hz: Found {} usages".format(rate, len(found)))

print("\n=== Searching for Format Values ===")

# Search for format/bit depth values
for fmt_val in FORMAT_VALUES:
    found = []
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
                                addr = inst.getAddress()
                                func = getFunctionContaining(addr)
                                
                                # Check if this is near a register write
                                inst_str = str(inst)
                                if "[" in inst_str or inst.getMnemonicString() in ["MOV", "OR", "AND"]:
                                    found.append({
                                        'value': fmt_val,
                                        'address': str(addr),
                                        'function': func.getName() if func else "UNKNOWN",
                                        'instruction': inst_str
                                    })
    
    if found:
        results['format_values'].extend(found)
        print("  {} bits: Found {} usages".format(fmt_val, len(found)))

# Generate report
output_file = "format_sample_rate_registers.txt"
try:
    f = open(output_file, 'w')
    f.write("=== Format and Sample Rate Register Analysis ===\n\n")
    from datetime import datetime
    f.write("Generated: {}\n\n".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    f.write("=== Sample Rate Value Usage ===\n\n")
    for usage in results['sample_rates']:
        f.write("{} Hz at {} in {}\n".format(usage['value'], usage['address'], usage['function']))
        f.write("  Instruction: {}\n".format(usage['instruction']))
        if usage['nearby_writes']:
            f.write("  Nearby register writes:\n")
            for write in usage['nearby_writes'][:5]:  # Limit to first 5
                f.write("    Offset 0x{:04x} at distance {}: {}\n".format(
                    write['offset'], write['distance'], write['instruction']))
        f.write("\n")
    
    f.write("\n=== Format Value Usage ===\n\n")
    for usage in results['format_values'][:50]:  # Limit output
        f.write("{} bits at {} in {}\n".format(usage['value'], usage['address'], usage['function']))
        f.write("  Instruction: {}\n".format(usage['instruction']))
        f.write("\n")
    
    f.close()
    print("\nReport saved to: {}".format(output_file))
except Exception as e:
    print("ERROR saving report: {}".format(e))

print("\n=== Complete ===")
print("Found {} sample rate usages, {} format usages".format(
    len(results['sample_rates']), len(results['format_values'])))
