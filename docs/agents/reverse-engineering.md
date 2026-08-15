# Reverse Engineering

Use repository evidence to separate what the Windows driver appears to do from what the Quantum
2626 hardware has actually been observed doing.

## Canonical Inputs

- `docs/REVERSE_ENGINEERING_PLAN.md`: staged workflow.
- `notes/GHIDRA_FINDINGS_SUMMARY.md`: consolidated findings.
- `notes/REGISTER_GUESSES.md`: register table and confidence.
- `notes/CURRENT_STATUS.md`: latest overall conclusion.
- `scripts/ghidra/`: repeatable analysis scripts.
- `driver-reference/pae_quantum.inf`: device and service metadata.

Treat proprietary Windows binaries and Ghidra project state as local reference material. Do not add,
copy, publish, or rewrite them as part of ordinary repository work.

## Evidence Labels

Every material register or initialization claim should identify one of these evidence classes:

- `observed-windows`: captured while the vendor stack operated the device;
- `observed-linux`: captured from the device or Linux driver;
- `static-analysis`: inferred from disassembly/decompilation;
- `hypothesis`: plausible but not yet confirmed.

Record the function or script, offset, access width, value or mask, execution phase, and capture date
when known. A structure-field access that numerically resembles a BAR offset is not an MMIO access
without base/provenance evidence.

## Change Rules

- Prefer improving a repeatable analysis script over preserving an unexplained one-off output.
- Keep generated bulk output and large traces out of Git. Promote only concise, sanitized findings.
- When confidence changes, reconcile `notes/REGISTER_GUESSES.md` and the relevant summary.
- Driver experiments based on new findings must remain narrow and must use the live-test approval
  boundary in `docs/agents/hardware-testing.md`.

