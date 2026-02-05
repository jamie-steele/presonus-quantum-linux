"""
Trace all MMIO writes on the stream-start path for fast driver iteration.

1. Finds FUN_140002e30 (control 0x100 = 0x8) and every function that calls it.
2. In each of those functions, lists every MMIO-style write in instruction order:
   [base+0xOFFSET] = value (or ? if value not immediate).
3. Writes stream_start_writes.txt: one line per write "0xOFFSET 0xVAL" or "0xOFFSET ?"
   so you can paste into the Linux driver or try via module params.

Run in Ghidra: Scripts > Run Script > trace_stream_start_writes.py
Output: stream_start_writes.txt, stream_start_writes_detail.txt
"""

from ghidra.program.model.listing import InstructionIterator
from ghidra.program.model.symbol import RefType
import re

CONTROL_FUNC = "FUN_140002e30"
# RefType.CALL or UNCONDITIONAL_CALL depending on Ghidra version
CALL_REFTYPES = set([
    getattr(RefType, "UNCONDITIONAL_CALL", None),
    getattr(RefType, "CALL", None),
    getattr(RefType, "COMPUTED_CALL", None),
])
CALL_REFTYPES.discard(None)
# MMIO offsets are typically 0x0 - 0x20000, 4-byte aligned
OFFSET_MIN, OFFSET_MAX = 0x0, 0x20000

def get_function(name):
    fm = currentProgram.getFunctionManager()
    for func in fm.getFunctions(True):
        if func.getName() == name:
            return func
    return None

def get_callers(func):
    """Return set of functions that call the given function."""
    refs = currentProgram.getReferenceManager().getReferencesTo(func.getEntryPoint())
    callers = set()
    for ref in refs:
        rt = ref.getReferenceType()
        is_call = False
        if CALL_REFTYPES and rt in CALL_REFTYPES:
            is_call = True
        elif not CALL_REFTYPES:
            inst = currentProgram.getListing().getInstructionAt(ref.getFromAddress())
            if inst and inst.getMnemonicString() == "CALL":
                is_call = True
        if not is_call:
            continue
        caller = getFunctionContaining(ref.getFromAddress())
        if caller:
            callers.add(caller)
    return callers

def get_immediate(inst, op_index=1):
    """Get immediate scalar from instruction operand if present."""
    if inst.getNumOperands() <= op_index:
        return None
    op = inst.getOpObjects(op_index)
    if op and len(op) == 1:
        obj = op[0]
        if hasattr(obj, 'getValue') and callable(getattr(obj, 'getValue')):
            return obj.getValue()
        if hasattr(obj, 'getScalar'):
            s = obj.getScalar()
            if s:
                return s.getUnsignedValue()
    return None

def collect_writes_in_function(func):
    """Return list of (offset, value_or_None) in instruction order. value is int or None (?)."""
    out = []
    body = func.getBody()
    listing = currentProgram.getListing()
    it = listing.getInstructions(body, True)
    for inst in it:
        mnemonic = inst.getMnemonicString()
        if mnemonic not in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"]:
            continue
        inst_str = str(inst)
        if "[" not in inst_str:
            continue
        # [reg+0xNNN] or [reg-0xNNN]
        for match in re.finditer(r'\[.*?[\+\-]0x([0-9a-fA-F]+)\]', inst_str):
            try:
                offset = int(match.group(1), 16)
            except Exception:
                continue
            if offset > OFFSET_MAX or offset % 4 != 0:
                continue
            val = get_immediate(inst, 1)
            out.append((offset, val))
            break  # one offset per inst
    return out

def main():
    program = currentProgram
    listing = currentProgram.getListing()
    control_func = get_function(CONTROL_FUNC)
    if not control_func:
        print("ERROR: {} not found".format(CONTROL_FUNC))
        return

    # Functions to analyze: control writer + all its callers
    to_analyze = [control_func]
    to_analyze.extend(get_callers(control_func))
    # Dedupe by name
    seen = set()
    unique = []
    for f in to_analyze:
        n = f.getName()
        if n not in seen:
            seen.add(n)
            unique.append(f)

    print("=== Stream-start path: MMIO writes ===")
    print("Seed: {}; callers: {}".format(
        CONTROL_FUNC,
        [f.getName() for f in unique if f != control_func]))
    print("")

    all_writes = []  # (func_name, addr, offset, value)
    for func in unique:
        writes = collect_writes_in_function(func)
        body = func.getBody()
        it = listing.getInstructions(body, True)
        idx = 0
        for inst in it:
            mnemonic = inst.getMnemonicString()
            if mnemonic not in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"]:
                continue
            inst_str = str(inst)
            if "[" not in inst_str:
                continue
            for match in re.finditer(r'\[.*?[\+\-]0x([0-9a-fA-F]+)\]', inst_str):
                try:
                    offset = int(match.group(1), 16)
                except Exception:
                    continue
                if offset > OFFSET_MAX or offset % 4 != 0:
                    continue
                val = get_immediate(inst, 1)
                all_writes.append((func.getName(), str(inst.getAddress()), offset, val))
                idx += 1
                break

    summary_lines = []
    for fn, addr, offset, val in all_writes:
        if val is not None:
            summary_lines.append("0x{:x} 0x{:x}".format(offset, val & 0xFFFFFFFF))
        else:
            summary_lines.append("0x{:x} ?".format(offset))

    import os
    # Prefer script dir so output lands next to other ghidra outputs
    try:
        base = os.path.dirname(getScriptPath())
    except Exception:
        base = os.getcwd()
    detail_path = os.path.join(base, "stream_start_writes_detail.txt")
    summary_path = os.path.join(base, "stream_start_writes.txt")

    with open(detail_path, "w") as f:
        f.write("# Stream-start path MMIO writes (func, addr, offset, value)\n")
        for fn, addr, offset, val in all_writes:
            vs = "0x{:x}".format(val & 0xFFFFFFFF) if val is not None else "?"
            f.write("{} {} 0x{:x} {}\n".format(fn, addr, offset, vs))
    print("Wrote: {}".format(detail_path))

    with open(summary_path, "w") as f:
        f.write("# Paste into driver or try as module params (offset value)\n")
        for line in summary_lines:
            f.write(line + "\n")
    print("Wrote: {}".format(summary_path))
    print("")
    print("Summary (offset value):")
    for line in summary_lines:
        print("  {}".format(line))

if __name__ == "__main__":
    main()
