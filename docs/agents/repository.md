# Repository Map And Source Precedence

Quantum2626 develops an out-of-tree Linux ALSA PCI driver for the PreSonus Quantum 2626. The
primary known device is a Thunderbolt 3 interface exposed as PCI device `1c67:0104`.

## Source Precedence

| Path | Owns |
| --- | --- |
| `driver/snd-quantum2626.c` | Actual driver implementation and module parameters. |
| `notes/CURRENT_STATUS.md` | Latest consolidated experimental status and known blockers. |
| `notes/REGISTER_GUESSES.md` | Register hypotheses, confidence, and supporting observations. |
| `notes/GHIDRA_FINDINGS_SUMMARY.md` | Consolidated static-analysis findings. |
| `docs/REVERSE_ENGINEERING_PLAN.md` | Repeatable reverse-engineering plan. |
| `docs/LINUX_TESTING_GUIDE.md` | Live Linux procedure; verify commands against current source before running. |
| `README.md` | Public project overview; detailed status may lag the focused notes. |
| `driver/README.md` | Driver build and usage overview; implementation descriptions may lag the C source. |

## Areas

| Path | Purpose |
| --- | --- |
| `driver/` | Out-of-tree ALSA PCI driver source and kernel-module build. |
| `driver-reference/` | Local Windows driver reference material and metadata; proprietary binaries are ignored. |
| `scripts/ghidra/` | Ghidra analysis scripts and selected analysis outputs. |
| `scripts/` | Linux device tests, Windows collection, and reverse-engineering helpers. |
| `notes/` | Durable findings, experiment summaries, and selected text evidence. |
| `docs/` | Human-facing plans, runbooks, and testing guides. |
| `samples/` | Small audio fixtures for explicitly authorized playback tests. |

## Current State

As of the consolidated status dated 2026-02-05 in `notes/CURRENT_STATUS.md`:

- The module probes the device, maps BAR0, registers ALSA PCM, and obtains an IRQ path.
- The current source contains experimental initialization, DMA-address, and stream-control writes.
- The device has not reached a confirmed ready state and no audio has been produced.
- The complete initialization, routing, DMA, and interrupt-status contracts remain unconfirmed.

Re-check these claims against current source and any newer evidence before changing the driver.
