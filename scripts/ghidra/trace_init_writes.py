"""
Trace MMIO writes in the Windows driver init function (FUN_140003d60).
Use this to find the init sequence needed for blue LED / audio (device not ready until then).

1. Finds FUN_140003d60 and collects every [base+offset]=value write in instruction order.
2. Writes init_writes.txt (all) and init_writes_likely.txt (offsets 0x0-0x300, 0x10300-0x10400).

Run: ./scripts/run_ghidra_analysis.sh trace_init_writes.py
"""

from ghidra.program.model.listing import InstructionIterator
import re

INIT_FUNC = "FUN_140003d60"
OFFSET_MAX = 0x20000

# Likely device MMIO range (exclude structure offsets like 0xc8, 0x1d0)
def is_likely_mmio(off):
    if off % 4 != 0:
        return False
    if 0x0 <= off <= 0x300:
        return True
    if 0x10300 <= off <= 0x10400:
        return True
    return False

def get_function(name):
    fm = currentProgram.getFunctionManager()
    for func in fm.getFunctions(True):
        if func.getName() == name:
            return func
    return None

def get_immediate(inst, op_index=1):
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

def main():
    listing = currentProgram.getListing()
    init_func = get_function(INIT_FUNC)
    if not init_func:
        print("ERROR: {} not found. Cannot trace init writes.".format(INIT_FUNC))
        return

    all_writes = []
    body = init_func.getBody()
    it = listing.getInstructions(body, True)
    for inst in it:
        mnemonic = inst.getMnemonicString()
        if mnemonic not in ["MOV", "OR", "AND", "XOR", "ADD", "SUB"]:
            continue
        inst_str = str(inst)
        if "[" not in inst_str:
            continue
        for match in re.finditer(r'\[.*?[\+\-]\s*(?:0x([0-9a-fA-F]+)|(\d+))\]', inst_str):
            try:
                g_hex, g_dec = match.group(1), match.group(2)
                offset = int(g_hex, 16) if g_hex else int(g_dec)
            except Exception:
                continue
            if offset > OFFSET_MAX or offset % 4 != 0:
                continue
            val = get_immediate(inst, 1)
            all_writes.append((init_func.getName(), str(inst.getAddress()), offset, val))
            break

    # Dedupe by (offset, value) keeping first occurrence order
    seen = set()
    unique = []
    for fn, addr, off, val in all_writes:
        key = (off, val if val is not None else "?")
        if key not in seen:
            seen.add(key)
            unique.append((fn, addr, off, val))

    import os
    try:
        base = os.path.dirname(getScriptPath())
    except Exception:
        base = os.getcwd()

    # All writes
    all_path = os.path.join(base, "init_writes.txt")
    with open(all_path, "w") as f:
        f.write("# Init path MMIO writes (FUN_140003d60) offset value\n")
        for fn, addr, off, val in unique:
            if val is not None:
                f.write("0x{:x} 0x{:x}\n".format(off, val & 0xFFFFFFFF))
            else:
                f.write("0x{:x} ?\n".format(off))
    print("Wrote: {} ({} writes)".format(all_path, len(unique)))

    # Likely device registers only
    likely = [(fn, addr, off, val) for (fn, addr, off, val) in unique if is_likely_mmio(off)]
    likely_path = os.path.join(base, "init_writes_likely.txt")
    with open(likely_path, "w") as f:
        f.write("# Init path writes to likely device regs (0x0-0x300, 0x10300-0x10400)\n")
        for fn, addr, off, val in likely:
            if val is not None:
                f.write("0x{:x} 0x{:x}\n".format(off, val & 0xFFFFFFFF))
            else:
                f.write("0x{:x} ?\n".format(off))
    print("Wrote: {} ({} writes)".format(likely_path, len(likely)))

    print("")
    print("Summary (likely device regs):")
    for fn, addr, off, val in likely:
        if val is not None:
            print("  0x{:x} 0x{:x}".format(off, val & 0xFFFFFFFF))
        else:
            print("  0x{:x} ?".format(off))
    if not likely:
        print("  (none in likely range; check init_writes.txt for full list)")

if __name__ == "__main__":
    main()
