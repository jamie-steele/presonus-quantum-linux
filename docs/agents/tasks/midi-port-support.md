# TASK-003 ALSA RawMIDI Support For The DIN MIDI Ports

## Status

Backlog

## Objective

Expose the Quantum 2626 physical DIN MIDI input and output as a standard ALSA RawMIDI device, and
prove byte-correct bidirectional operation without regressing the live-proven PCM audio path.

## Scope

- Determine whether the vendor implements MIDI through a conventional UART/FIFO, the TCI mailbox,
  a dedicated DMA path, or another interrupt-driven transport.
- Capture narrowly controlled vendor-driver behavior for known MIDI input and output byte streams.
- Implement ALSA RawMIDI input/output lifecycle, buffering, wakeups, interrupt handling, and device
  registration independently from the PCM engine.
- Validate physical DIN loopback for notes, controllers, running status, SysEx, MIDI clock, active
  sensing, and sustained bidirectional traffic.
- Validate simultaneous MIDI traffic and ordinary desktop audio against the preserved release
  baseline.

## Out Of Scope

- Changing PCM geometry, rate handling, DMA, IRQ cadence, QoS, UCM, WirePlumber, or scheduler
  policy as an incidental part of MIDI work.
- Implementing a generative sequencer, DockPipe audio packages, MIDI-to-CV orchestration, or a DAW
  integration layer; those are consumers of the standard MIDI endpoint.
- Firmware modification, broad MMIO sweeps, speculative register writes, USB MIDI support, or
  support claims for other PreSonus models without independent evidence.

## Relevant Context

- `driver/snd-quantum2626.c` currently registers PCM playback/capture but contains no RawMIDI
  implementation.
- `docs/agents/tasks/tci-mailbox-macos-trace-pivot.md` owns the recovered vendor TCI mailbox model
  and is the first reference if MIDI is multiplexed through that control transport.
- `notes/CURRENT_STATUS.md` owns the current live hardware and audio baseline.
- `docs/agents/reverse-engineering.md` and `docs/agents/hardware-testing.md` govern vendor analysis
  and live device experiments.
- Public tracking issue: `https://github.com/jamie-steele/presonus-quantum-linux/issues/16`.

## Constraints

- Preserve the exact accepted audio control state: native 44.1 kHz, 26-channel S32_LE,
  128-frame periods, 512-frame hardware buffer, playback `slowptr true`, 256-frame PipeWire
  headroom, realtime data-loop scheduling, and the driver-scoped 2-us CPU-latency request.
- Keep MIDI implementation and lifecycle independent from the shared PCM DMA engine unless vendor
  evidence proves a required coupling.
- Treat module reloads, service restarts, MIDI transmission, physical loopback, trace collection,
  and every MMIO write as separately approved live boundaries.
- Do not infer a standard UART layout from the physical DIN connectors; require vendor or trace
  evidence before naming or writing registers.
- Bound all queues and teardown paths. A stuck or malformed MIDI stream must not block IRQ handling,
  module removal, or audio period notification.

## Plan

1. Inventory the macOS DEXT and Windows driver for MIDI-facing classes, strings, callbacks, message
   codes, register offsets, and interrupt bits; classify each finding as static evidence or
   hypothesis.
2. Design a minimal vendor-driver trace using distinct known byte sequences on MIDI OUT and a
   physical MIDI OUT-to-IN loopback, avoiding broad register capture where a focused event trace is
   sufficient.
3. Identify the transport, receive/transmit readiness rules, queue depth, acknowledgement behavior,
   and device-reset lifecycle before implementing Linux writes.
4. Add one duplex ALSA RawMIDI device with bounded FIFOs and symmetric probe/remove/error unwind,
   leaving all PCM callbacks and negotiated audio behavior unchanged.
5. Validate byte-exact notes, CC, running status, bounded SysEx sizes, clock, active sensing, burst
   traffic, close/reopen, module lifecycle, and failure recovery.
6. Run simultaneous sustained MIDI input/output and ordinary 44.1 kHz desktop playback, requiring
   unchanged audio geometry, IRQ cadence, realtime scheduling, and audible cleanliness.
7. Document the confirmed MIDI transport and public usage surface, then close only after both DIN
   directions and audio non-regression are live-proven.

## Evidence And Discoveries

- **Repository inspection, 2026-08-16:** `driver/snd-quantum2626.c` contains no `snd_rawmidi`,
  RawMIDI, or MIDI implementation. Existing public/status documents list MIDI as unproven. This
  establishes a missing feature, not the underlying hardware transport.

## Decisions

- **2026-08-16:** track MIDI as a separate driver objective rather than extending TASK-002. The
  accepted audio runtime is a protected non-regression baseline, while MIDI requires distinct
  reverse engineering, kernel interfaces, physical cabling, and live validation.
- **2026-08-16:** target ALSA RawMIDI as the kernel-facing interface so DAWs, PipeWire/JACK tooling,
  modular workflows, and future DockPipe packages can consume a standard endpoint.

## Changes

- Added this backlog record and its top-level task-index entry.
- Created GitHub issue 16 as the public implementation and acceptance tracker.

## Validation

- `rg -i 'rawmidi|snd_rawmidi|midi' driver/snd-quantum2626.c` returned no implementation match.
- GitHub duplicate review found no existing MIDI issue before creating issue 16.
- `git diff --check` passes for the backlog record and index update.
- No module, service, PCM, MIDI, MMIO, or installed-system state is changed by backlog creation.

## Remaining Work

- Begin only when the user promotes TASK-003 from backlog and separately approves the first live
  trace or hardware boundary.

## Closure Summary

Open backlog item; implementation and live validation have not started.
