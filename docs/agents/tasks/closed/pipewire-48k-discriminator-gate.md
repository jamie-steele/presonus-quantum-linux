# TASK-007 Native-48-kHz PipeWire Discriminator Gate

## Status

Closed; the remaining legacy discriminator gate was superseded on 2026-09-27
by the move to the upstream RFC driver. The completed offline harness repair
remains useful, but this old baseline and proposed invocation are no longer queued.
No live gate was completed by this closure. The sections below preserve the
original experiment and evidence, not current execution instructions.

## Objective

Extend the completed TASK-006 instrumentation to the selected native-48-kHz desktop baseline, then
prepare and seal exactly one five-minute PipeWire Line Outputs 3-4 to Line Input 3 discriminator at
-30 dBFS. Stop for separate exact approval before opening either audio direction.

## Scope

- Preserve the existing 44.1-kHz default and immutable replay behavior.
- Accept an explicit live rate of 44100 or 48000 and pass it consistently to both helpers and ALSA
  geometry validation.
- Preserve the exact 26-channel S32_LE, 128-frame period, 512-frame buffer, selected endpoints,
  physical route, gain, scheduler policy, service, module, UCM, and WirePlumber state.
- Re-run the complete offline instrumentation proof, then seal a fresh output path and exact live
  invocation only when all fail-closed prerequisites pass.

## Out Of Scope

- Weakening the required 1 MiB PipeWire capture-isolation stage.
- Starting playback or capture before separate exact gate approval.
- Service restart, scheduler or RTKit mutation, module/device action, routing/gain change, UCM or
  WirePlumber change, retry, fallback, cleanup, commit, push, PR, or long soak.

## Completed Checkpoints

- **Source extension, 2026-08-19:** `run --rate` now accepts only 44100 or 48000, selects that rate
  for PipeWire and direct-ALSA helper commands, validates both hardware directions against it, and
  records it in start and summary artifacts. The default remains 44100.
- **Focused offline proof, 2026-08-19:** Python compilation passes. A dependency-free contract
  check accepts both 48-kHz helper pairs, parses 48000, and rejects 96000. Immutable read-only
  replay still classifies all 29 retained TASK-004 captures. `git diff --check` passes.
- **Read-only live readiness, 2026-08-19:** the PipeWire graph is fixed at 48000 with allowed rates
  `[ 48000 ]`, both Quantum PCMs are closed, and the graph has zero active audio streams. No audio,
  service, configuration, or device mutation occurred.

## Resolved Host Boundary

The complete self-test fails before audio or artifact creation because `F_SETPIPE_SZ` currently
permits 65,536, 131,072, and 262,144 bytes but returns `EPERM` for 524,288 and 1,048,576 bytes. The
kernel advertises a 1,048,576-byte maximum and an unlimited hard user-page limit, so this is a
current host/resource admission failure rather than a requested-size typo. The discriminator keeps
the established 1 MiB requirement because 256 KiB provides only the exact sixteen-block
fail-closed window at 48 kHz, without the required isolation margin.

At the time of these audits, no V2 controller or gate packet was sealed and no future artifact path
was consumed.

A second exact 1,048,576-byte admission check after the user cleared applications returned the
same `EPERM`. Zero-stream/closed-PCM readiness therefore does not clear this boundary. No complete
self-test, output artifact, helper, or audio stream began during either audit.

## Approved Isolation Repair

The user explicitly approved replacing the oversized PipeWire kernel-pipe dependency. PipeWire
capture now uses one preallocated, bounded 1 MiB userspace byte ring inside the already-isolated
extractor process. The surrounding kernel pipes remain ordinary transport edges; the reader thread
drains the raw mono stream into the ring while the extractor's main thread forwards it to the
analyzer. Direct ALSA is unchanged.

The focused fixture fills the ring to exactly 1,048,576 bytes, blocks rather than exceeding that
bound, crosses multiple wrap points, preserves every byte, and propagates reader failure. Three
consecutive `self-test --transport pipewire` runs pass with 44.1/48-kHz rate coverage and a
5.461333-second 48-kHz isolation margin. Immutable replay still classifies all 29 prior captures.
The earlier pipe-capacity blocker is resolved for this PipeWire objective without weakening the
1 MiB isolation requirement.

## Historical Next Checkpoint (Retired)

Revalidate the current 48-kHz graph, zero-stream and closed-PCM state, exact endpoints, physical
route prerequisite, owned source/docs, installed defaults, scheduler policy, services, module, and
absence of `/tmp/quantum2626-loopback-pipewire-instrumented-discriminator-20260819-2`. Then seal one exact native-48-kHz five-minute invocation, run its
non-consuming preflight, and stop at `waiting_for_gate` for separate exact approval.

## Closure Summary

Closed as superseded on 2026-09-27. Retain the tested instrumentation; retire the
unexecuted gate tied to the old driver/session baseline. A future continuity test
must be justified by a current upstream or desktop-integration issue and scoped
from fresh evidence, rather than resuming this historical invocation.
