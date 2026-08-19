# Repository Map And Source Precedence

PreSonus Quantum Linux aims to support the full Quantum interface family over time. The current
out-of-tree Linux ALSA PCI driver is enabled and hardware-tested only for the Quantum 2626, a
Thunderbolt 3 interface exposed as PCI device `1c67:0104`.

The public family roadmap and support claims live in the support matrix in `README.md`. Treat the
PCI table in `driver/snd-quantum2626.c` and hardware evidence in `notes/CURRENT_STATUS.md` as the
authority for what is actually enabled and proven.

## Source Precedence

| Path | Owns |
| --- | --- |
| `driver/snd-quantum2626.c` | Actual driver implementation and module parameters. |
| `notes/CURRENT_STATUS.md` | Latest consolidated experimental status and known blockers. |
| `notes/REGISTER_GUESSES.md` | Register hypotheses, confidence, and supporting observations. |
| `notes/GHIDRA_FINDINGS_SUMMARY.md` | Consolidated static-analysis findings. |
| `docs/REVERSE_ENGINEERING_PLAN.md` | Repeatable reverse-engineering plan. |
| `docs/LINUX_TESTING.md` | Live Linux procedure; verify commands against current source before running. |
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
- The repository source exposes one S32_LE duplex PCM with fixed 128-frame periods and recovered
  native profiles: 26 channels at 44.1/48 kHz, 18 at 88.2/96 kHz, and 8 at 176.4/192 kHz. Only the
  48 kHz/26-channel profile is live-proven; the new TCI rate setter remains offline-verified.
- A five-second direct-ALSA silence run completed without an xrun and produced the exact expected
  interrupt count. Playback channels 1 and 2 were physically audible through headphone left/right.
- `notes/CHANNEL_ROUTING.md` records the statically recovered analog, S/PDIF, and ADAT channel order.
- WirePlumber publishes all 13 UCM playback sinks, and one bounded PipeWire Main stream completed
  with advancing DMA interrupts and a clean stop. YouTube playback through the desktop sink is
  physically audible through the connected headphones.
- Direct ALSA capture and bounded PipeWire duplex operation are live-proven. WirePlumber publishes
  all 26 inputs as independent mono sources, including a live-tested Line Input 5 binding.
- Non-48 kHz profiles, physical digital-I/O validation, mixer controls, MIDI, and hot-removal
  behavior remain unproven.

Re-check these claims against current source and any newer evidence before changing the driver.
