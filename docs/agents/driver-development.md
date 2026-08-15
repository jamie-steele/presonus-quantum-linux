# Driver Development

Load this guide for edits under `driver/` or for claims about the current kernel-module behavior.

## Read First

1. `notes/CURRENT_STATUS.md`
2. `driver/snd-quantum2626.c`
3. `notes/REGISTER_GUESSES.md` when changing MMIO behavior
4. `driver/README.md` for the operator-facing build surface
5. `docs/LINUX_TESTING_GUIDE.md` only when live testing is in scope

The C source wins when older prose describes the implementation differently. If a change makes a
canonical status or usage document stale, update that document in the same slice when practical.

## Boundaries

- Preserve PCI enable/request/map and unwind symmetry across probe, failure, and remove paths.
- Treat DMA addresses, buffer sizes, period accounting, IRQ acknowledgement, and ALSA callback
  lifetime as correctness-sensitive. Do not infer safe behavior from a successful module build.
- Keep experimental MMIO offsets and values named, documented, and tied to evidence. Avoid broad
  register loops or writes to offsets observed only as structure fields in decompiled code.
- Preserve module parameters used by existing scripts unless an intentional compatibility change is
  requested and the scripts/docs are updated together.
- Do not mix source edits with unapproved module loading, service interruption, playback, capture,
  or device writes.

## Verification

Run the narrowest applicable checks and report environmental limitations:

```bash
git diff --check
make -C driver
```

Compilation requires matching kernel headers. A missing or mismatched host kernel build tree is an
environment limitation, not a reason to alter driver behavior. Live verification is separately
routed through `docs/agents/hardware-testing.md`.

