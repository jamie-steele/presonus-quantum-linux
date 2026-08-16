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
| `alsa/` | UCM desktop routing for the currently proven playback geometry. |
| `driver-reference/` | Local Windows driver reference material and metadata; proprietary binaries are ignored. |
| `scripts/ghidra/` | Ghidra analysis scripts and selected analysis outputs. |
| `scripts/` | Linux device tests, Windows collection, and reverse-engineering helpers. |
| `notes/` | Durable findings, experiment summaries, and selected text evidence. |
| `docs/` | Human-facing plans, runbooks, and testing guides. |
| `samples/` | Small audio fixtures for explicitly authorized playback tests. |

## Current State

As of the consolidated status dated 2026-08-15 in `notes/CURRENT_STATUS.md`:

- The module performs a bounded TCI mailbox startup and read-only readiness handshake for the
  verified `1c67:0104` device.
- It exposes one fixed 48 kHz, 26-channel, S32_LE playback PCM with 128-frame periods and real
  page-table DMA, IRQ, and hardware-position handling.
- A five-second direct-ALSA silence run completed without an xrun and produced the exact expected
  interrupt count. Playback channels 1 and 2 were physically audible through headphone left/right.
- `notes/CHANNEL_ROUTING.md` records the statically recovered analog, S/PDIF, and ADAT channel order.
- WirePlumber publishes all 13 UCM playback sinks, and one bounded PipeWire Main stream completed
  with advancing DMA interrupts and a clean stop. YouTube playback through the desktop sink is
  physically audible through the connected headphones.
- Capture, high sample rates, physical digital-output validation, and hot-removal behavior remain
  unproven.

Re-check these claims against current source and any newer evidence before changing the driver.
