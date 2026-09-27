# TASK-006 PipeWire Discontinuity Discriminator Instrumentation

## Status

Closed

## Objective

Prepare and offline-prove one bounded PipeWire continuity discriminator that can separate playback
graph failure from capture-helper/analyzer backpressure without changing the accepted desktop or
driver defaults.

## Scope

- Drain PipeWire capture through a pre-started isolated process.
- Give both raw-capture and analyzed-mono stages 1 MiB pipes.
- Record scheduling state for `pw-play`, `pw-record`, their threads, and the user's PipeWire server
  data-loop threads.
- Preserve initial and changed `pw-top` ERR counters as structured JSONL evidence.
- Extend dependency-free offline fixtures and the focused loopback guide.

## Out Of Scope

- Opening playback or capture, reading the live PipeWire registry during offline validation, or
  invoking a continuity gate.
- Service, scheduler, RTKit, module, device, MMIO, routing, gain, geometry, UCM, or WirePlumber
  changes.
- Driver diagnosis or repair, cleanup, commit, push, publication, or subjective listening claims.

## Relevant Context

- `scripts/quantum2626_loopback_soak.py` owns the fail-closed analyzer and transport helpers.
- `docs/LOOPBACK_CONTINUITY_TESTING.md` owns the test and artifact contract.
- `docs/agents/tasks/closed/release-performance-hardening.md` retains the prior direct-ALSA and PipeWire
  controls.
- Immutable five-minute PipeWire evidence under
  `/tmp/quantum2626-loopback-pipewire-post-defaults-calibration-20260818-8` completed at exact
  44.1-kHz/26-channel/S32_LE/128/512 ALSA geometry but recorded 29 discontinuities. The output sink
  and `pw-play` counters advanced while the capture source remained at zero; `pw-record` evidence is
  confounded by the old synchronous analyzer pipeline.

## Constraints

- Preserve playback-first ordering, the exact selected endpoints, 256-frame PipeWire quantum, and
  all accepted desktop defaults.
- A future live run must fail before geometry admission if 1 MiB pipe sizing or required scheduling
  telemetry is unavailable.
- Treat ERR counters as graph scheduling evidence, not automatic ALSA or driver xruns.
- Preserve all unrelated tracked, untracked, ignored, and generated checkout state.

## Plan

1. Isolate PipeWire capture and enlarge both pipeline stages.
2. Add bounded helper-thread, server-data-loop, and ERR-transition telemetry.
3. Add offline fixtures for geometry, capacity, parsing, and transition semantics.
4. Update the focused guide and run terminal offline verification.
5. Stop before preparing or entering any live gate.

## Evidence And Discoveries

- **Observed artifact, 2026-08-19:** the preceding run's 64 KiB mono PipeWire capture pipe held only
  0.372 seconds at 44.1-kHz S32_LE. Offline replay averaged about 114 ms per global search versus
  92.9 ms per analysis block, so dense reacquisition could accumulate capture-helper backpressure.
- **Design, 2026-08-19:** two 1 MiB stages each hold 5.944 seconds of mono capture, exceeding the
  analyzer's 1.486-second fail-closed maximum-loss window.
- **Offline verification, 2026-08-19:** the final self-test passed three consecutive times. Mono
  PipeWire passthrough retained exact samples through the isolated extractor and both pipes read
  back as 1,048,576 bytes. Helper-thread and server-data-loop schemas, exact `pw-top` parsing, and
  initial/change ERR semantics passed without reading the PipeWire registry or opening audio.
- **Immutable replay, 2026-08-19:** the corrected script replayed all 29 prior event captures
  read-only with the same nine globally locked phase jumps and 20 globally reacquired correlation
  drops. Re-parsing the preserved raw `pw-top` log found all four exact roles, 36 initial/change
  records, and terminal errors 41/0/27/24 for playback node, capture node, `pw-play`, and
  `pw-record`. The three source artifact hashes remained exact.
- **Read-only host correction, 2026-08-19:** gate preparation found that this PipeWire build names
  its server scheduling thread `pw-data-loop`, while the offline matcher admitted only
  `data-loop*`. The matcher now accepts both exact server naming forms only when owned by the
  same-user `pipewire` process. Offline fixtures reject client-owned and lookalike names, and live
  read-only discovery recovers the host thread without opening either audio direction.
- **Post-closure rate-selection extension, 2026-08-19:** the desktop baseline later moved to native
  48 kHz for a listening A/B. The live harness now accepts an explicit `--rate` of 44100 or 48000,
  passes that rate to both PipeWire or direct-ALSA helpers, and validates both hardware directions
  against the same selected rate. The default remains 44100 so retained 44.1-kHz commands and
  immutable event replay behavior do not change. Offline fixtures cover both generated 48-kHz
  helper command pairs and calculate the two 1 MiB capture-stage margins at both supported rates.
  The focused rate contract and immutable replay pass; the complete self-test is currently blocked
  before completion by the host pipe-capacity boundary recorded in TASK-007. This extension does
  not switch the graph or open audio.
- **Post-closure PipeWire isolation repair, 2026-08-19:** two repeated host checks permitted kernel
  pipes only through 256 KiB even with zero active audio streams and closed PCMs. With explicit user
  approval, PipeWire capture now uses a preallocated, bounded 1 MiB userspace byte ring inside the
  isolated extractor; direct ALSA keeps its existing kernel-pipe contract. The focused fixture
  fills the ring exactly, crosses multiple wrap points, preserves every byte, propagates reader
  failure, and reports its admitted capacity before live helper startup. Three consecutive
  PipeWire-focused self-tests pass at both supported rate contracts, and immutable replay still
  classifies all 29 retained captures. No audio stream or live artifact was created.

## Decisions

- Use the existing isolated extractor for both transports. PipeWire passes mono channel zero
  unchanged; direct ALSA retains 26-channel channel-two extraction.
- Record every helper thread and only same-user `pipewire` threads named `data-loop*` or exactly
  `pw-data-loop`; do not infer scheduling from the process main thread alone.
- Add `pw-errors.jsonl` for initial and changed counters while retaining the raw filtered `pw-top`
  log as the audit source.

## Changes

- `scripts/quantum2626_loopback_soak.py`: use the isolated extractor for both transports; require
  1 MiB PipeWire userspace isolation or the existing direct-ALSA kernel pipes; record and validate
  every helper thread and pre-discovered PipeWire server data loop; emit structured ERR transitions;
  retain terminal instrumentation state in the summary; accept an explicit live rate of 44100 or
  48000 while preserving 44100 as the default.
- `docs/LOOPBACK_CONTINUITY_TESTING.md`: document the new pipeline, artifacts, scheduling contract,
  and interpretation limits.
- `docs/agents/tasks/index.yml`: register and close TASK-006 while preserving the existing TASK-003
  addition.
- `docs/agents/tasks/closed/pipewire-discontinuity-instrumentation.md`: record this objective and proof.

## Validation

- `python3 -m py_compile scripts/quantum2626_loopback_soak.py` — pass.
- `python3 scripts/quantum2626_loopback_soak.py self-test` — three consecutive terminal passes.
- `python3 scripts/quantum2626_loopback_soak.py self-test --transport pipewire` after the
  userspace-ring repair — three consecutive terminal passes.
- `python3 scripts/quantum2626_loopback_soak.py replay --artifact-dir
  /tmp/quantum2626-loopback-pipewire-post-defaults-calibration-20260818-8` — pass, 29 captures.
- Existing-artifact parser exercise — pass, four exact roles and 36 transition records.
- YAML parse of `docs/agents/tasks/index.yml` — pass with TASK-006 present.
- `git diff --check` plus trailing-whitespace scan of the three untracked owned files — pass.
- Live playback/capture, registry inspection, service/module/device actions, and subjective
  listening were intentionally skipped.

## Remaining Work

- A live five-minute discriminator remains a separately approved one-shot gate after review of the
  exact command, new artifact path, physical-route confirmation, and protected anchors. No gate is
  prepared or authorized by this closed offline task.

## Closure Summary

Closed 2026-08-19. The PipeWire capture path is isolated from analyzer timing by an exact 1 MiB
stage, and directional evidence includes exact helper threads, PipeWire server data loops, and
structured ERR transitions. Offline proof is complete; no live state was touched and no gate
authority was used.
