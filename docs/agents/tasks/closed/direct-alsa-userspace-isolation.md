# TASK-011 Direct-ALSA Userspace Isolation

## Status

Closed; offline implementation and terminal verification completed without opening audio.

## Objective

Replace the direct-ALSA loopback harness's three oversized kernel-pipe dependencies with bounded
1 MiB userspace playback and capture isolation, while preserving its exact transport commands,
26-channel S32_LE mapping, selected rate, 128/512 geometry, RTKit option, and PipeWire behavior.

## Scope

- Pre-fill and drain an exact 1 MiB byte ring inside the existing isolated direct-ALSA playback
  feeder process.
- Use the existing exact 1 MiB extractor ring for direct-ALSA channel-two capture as well as the
  unchanged PipeWire mono path.
- Keep surrounding kernel pipes as read-only-measured transport edges with no enlargement request.
- Prove byte preservation, exact capacity, bounded blocking, failure propagation, 44.1/48-kHz
  margins, command geometry, and transport-specific behavior with offline fixtures.

## Out Of Scope

- Opening playback or capture, reading or changing the live graph, or creating a live artifact.
- Service, module, UCM, WirePlumber, scheduler, RTKit, routing, gain, or device mutation.
- Reusing any prior live gate, preparing or invoking a successor gate, cleanup, commit, push, or PR.

## Invariants

- PipeWire retains its isolated feeder and exact 1 MiB mono extractor ring.
- Direct ALSA retains `hw:P2626,0`, 26-channel S32_LE, zero-based channel two, 128-frame periods,
  512-frame buffers, mmap, fatal errors, and selected 44100 or 48000 rate.
- `--rtkit-helper-priority` continues to target only the ALSA playback and capture helpers; feeder
  and extractor scheduling behavior is unchanged.
- The default live rate remains 44100; offline coverage includes both supported live rates.

## Implementation

- `BoundedByteBuffer` is now transport-neutral and remains preallocated and capacity-enforcing.
- The direct-ALSA feeder creates its ring after the existing safe fork, fills it exactly, reports
  the admitted capacity to the parent, then drains it to the unchanged `aplay` stdin.
- Both capture transports request the extractor's exact ring. Its reader thread continuously drains
  raw input and writes selected mono samples while its main thread forwards them to the analyzer.
- No live path calls `F_SETPIPE_SZ`; native pipe capacities are recorded alongside userspace
  capacities in pipeline evidence.

## Offline Evidence

- The generic ring fixture reaches its exact bound, blocks without exceeding it, crosses wrap
  points, preserves all bytes, and propagates a reader failure.
- The direct-ALSA extractor fixture preserves channel two from exact 26-channel S32_LE input through
  the admitted 1 MiB capture ring; all other playback channels remain silent.
- The direct-ALSA feeder fixture admits and pre-fills its exact 1 MiB playback ring, then emits the
  deterministic repeated payload byte-for-byte through a native pipe.
- At 48 kHz, 1 MiB retains 0.210051 seconds of 26-channel playback and 5.461333 seconds of mono
  capture. The latter exceeds the 1.365333-second sixteen-block fail-closed analysis window.
- Helper command fixtures preserve 44.1/48-kHz selection and exact 26-channel S32_LE 128/512
  direct-ALSA geometry.

## Validation

- `python3 -m py_compile scripts/quantum2626_loopback_soak.py` — pass.
- `python3 scripts/quantum2626_loopback_soak.py self-test` — pass with exact 1 MiB direct-ALSA
  playback/capture rings and native 64 KiB surrounding pipes.
- `python3 scripts/quantum2626_loopback_soak.py self-test --transport pipewire` — pass; unchanged
  PipeWire userspace capture isolation remains exact.
- `python3 scripts/quantum2626_loopback_soak.py self-test --transport alsa` — pass; 44.1/48-kHz
  commands, geometry, capacity, byte preservation, and margins are exact.
- Read-only replay of all 29 retained TASK-006 captures — pass with nine globally locked phase
  jumps and twenty globally reacquired correlation drops.
- YAML parse of `docs/agents/tasks/index.yml` and `git diff --check` — pass.
- Live playback/capture, registry inspection, and every service, device, configuration, scheduler,
  routing, and gain action were intentionally skipped.

## Remaining Boundary

After offline verification and closure, any direct-ALSA playback/capture run is a fresh live action
requiring its own bounded gate and explicit approval. This task grants no live authority.

## Closure Summary

Closed 2026-08-19. Direct ALSA no longer depends on oversized kernel-pipe admission: its existing
isolated feeder and extractor now admit exact bounded 1 MiB userspace rings before a live pipeline
could reach geometry validation. PipeWire behavior, helper commands, rate/default contracts,
channel mapping, 128/512 geometry, and RTKit scope remain unchanged. No live gate was prepared or
invoked.
