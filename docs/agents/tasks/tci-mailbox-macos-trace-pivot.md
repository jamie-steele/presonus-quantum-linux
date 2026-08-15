# TASK-001 TCI Mailbox Recovery From macOS Traces

## Status

Active

## Objective

Replace the current speculative Windows-register approach with an evidence-backed, Linux-native
implementation of the device's TCI command mailbox, initialization, clock control, and DMA path.
Use traced macOS driver behavior and publicly reviewable implementation material as the primary
technical route, then prove reliable Quantum 2626 capture and playback through direct ALSA before
expanding desktop-audio integration.

## Why This Pivot Matters

The likely missing abstraction is a TCI command mailbox rather than a handful of independent MMIO
control registers. A credible but not yet locally reproduced technical lead indicates:

- Hardware initialization depends on first making the TCI mailbox operational.
- Sample-rate and clock switching are TCI commands.
- DMA implementation becomes comparatively direct after the mailbox protocol works.
- macOS DEXT behavior can be observed through m1n1 MMIO tracing on Apple Silicon.
- Stable direct-ALSA capture and playback may be achievable before PipeWire or JACK integration.

This changes the investigation order. Windows-driver decompilation remains useful corroboration, but
it is no longer the primary source for guessing standalone register meanings.

## Scope

- Locate and review publicly available Linux patches, protocol notes, and m1n1 trace tooling relevant
  to the Quantum family. Record provenance and licensing before reusing code.
- Establish a reproducible, sanitized macOS DEXT MMIO-trace workflow without committing proprietary
  binaries, personal data, or bulk trace output.
- Recover the TCI mailbox contract: MMIO registers, message layout, command and response ownership,
  sequencing, readiness/completion signaling, timeouts, error handling, and concurrency rules.
- Identify the minimum command set for Quantum 2626 initialization, device readiness, sample-rate
  switching, stream preparation, stream start/stop, and shutdown.
- Recover the actual DMA contract: descriptors or buffers, address width, sizes, periods, channel
  layout, hardware pointer, interrupt status, and acknowledgement.
- Implement the recovered protocol behind cohesive Linux driver helpers rather than scattering raw
  mailbox/register operations across ALSA callbacks.
- Validate direct ALSA playback and capture across supported rates, buffer sizes, channels, stream
  directions, repeated start/stop, and hot removal.
- Evaluate a bounded CPU latency QoS request during active DMA if measurements show that wake latency
  causes crackling; release it on stop, close, probe failure, removal, and every unwind path.
- Keep Quantum 2626 (`1c67:0104`) as the verified model. Require explicit opt-in for related but
  unverified Quantum models until device-specific evidence exists.
- After direct ALSA is reliable, characterize PipeWire and JACK failures and determine whether they
  require driver corrections, UCM/ACP/profile data, or a separate integration task.

## Out Of Scope

- Continuing broad Windows MMIO value sweeps as the main discovery strategy.
- Copying or publishing proprietary macOS or Windows driver binaries.
- Treating decompiled code as reusable source without provenance and license review.
- Claiming support for Quantum 2, Quantum 4848, or other related PCI IDs without hardware evidence.
- Making Apple Silicon USB4 enablement a prerequisite for the initial Quantum 2626 Linux result.
- Optimizing for 32- or 64-frame operation before the protocol and a stable 128-frame baseline are
  proven.
- Running live module, MMIO, playback, capture, latency, or hot-removal tests without a separately
  confirmed live-test boundary.

## Relevant Context

- `notes/CURRENT_STATUS.md`: the local driver probes and exposes ALSA but has not reached confirmed
  readiness or produced audio.
- `driver/snd-quantum2626.c`: current implementation contains experimental direct MMIO writes, a
  synthetic timer-driven pointer, stereo-only S16 constraints, and no TCI/mailbox model.
- `notes/REGISTER_GUESSES.md` and `notes/GHIDRA_FINDINGS_SUMMARY.md`: Windows analysis recorded reads
  at `0x10300` and `0x10304`; it did not prove that these offsets accept raw ALSA DMA addresses.
- `docs/REVERSE_ENGINEERING_PLAN.md`: current plan is Windows-first and must be revised after the TCI
  contract is understood.
- `docs/agents/reverse-engineering.md`: evidence labels and artifact rules.
- `docs/agents/driver-development.md`: driver correctness and source-verification boundaries.
- `docs/agents/hardware-testing.md`: approval and evidence requirements for live tests.

## Constraints

- Preserve `TCI` as the protocol name until an authoritative source establishes its expansion and
  semantics; do not invent terminology.
- Label every protocol statement as observed, source-established, static-analysis, or hypothesis.
- Treat current writes to `0x100`, `0x10300`, and `0x10304` as unverified until reconciled with the
  mailbox and DMA contracts. Do not perform further broad writes based only on numeric resemblance.
- Use only public or locally lawful inputs, retain license headers, and keep provenance for any
  adapted implementation.
- Keep live tests narrow, reversible, and separately approved. Restore host audio and latency state
  after every test, including failures.
- Do not make system-wide C-state changes. Any power/latency mitigation must be driver-scoped,
  active-stream-only, measurable, and correctly unwound.
- Keep x86_64 hardware proof separate from arm64 compilation and Apple Silicon USB4 qualification.

## Plan

1. **Find the authoritative implementation evidence.** Locate the public patch series, repository,
   protocol description, and m1n1 tracing resources. Record versions, dates, hashes, authorship, and
   licensing without importing code yet.
2. **Build a source-to-behavior map.** Identify the public Linux driver's mailbox, initialization,
   DMA, IRQ, clock, model-detection, hot-remove, and power-latency components. Map each behavior to
   the corresponding Linux subsystem API.
3. **Define the macOS trace experiment.** Specify the exact DEXT lifecycle transitions to capture:
   attach/init, rate changes, playback/capture prepare, start, stop, and detach. Define trace
   filtering and redaction before any capture.
4. **Document the TCI transport.** Produce an evidence table for mailbox registers and message
   fields, ordering and memory barriers, request/response flow, readiness, timeouts, and recovery.
   Add focused parser/encoding tests where the contract can be tested without hardware.
5. **Reconcile current register assumptions.** Classify every direct write in the local driver as
   mailbox transport, DMA transport, corroborated non-mailbox behavior, or unsupported guess.
   Remove or disable unsupported experimental paths before the first TCI live test.
6. **Implement the minimum vertical slice.** Add Linux-native TCI helpers, initialize only the
   Quantum 2626, issue one proven clock/rate command, configure one proven DMA direction, handle the
   real interrupt/pointer path, and unwind all state safely.
7. **Prove direct ALSA behavior.** Under explicit live-test approval, start with 48 kHz and a
   conservative buffer, then cover capture and playback, all physical channels, supported sample
   rates through 192 kHz, repeated stream cycles, simultaneous directions, and hot removal.
8. **Characterize latency.** Establish a 192 kHz/128-frame baseline, measure xruns and wake latency,
   then test a scoped approximately 2 microsecond CPU latency QoS request if justified. Treat 32- and
   64-frame operation as exploratory; verify whether apparent macOS 32-frame behavior batches four
   subperiods into an effective 128-frame hardware transaction.
9. **Separate desktop integration.** Reproduce PipeWire and JACK behavior only after ALSA is stable.
   Decide from evidence whether the next work belongs in the driver, ALSA topology/UCM, ACP/profile
   metadata, or userspace configuration.
10. **Prepare upstream-quality evidence.** Reconcile canonical notes and guides, remove unsafe debug
    surfaces, document supported hardware honestly, compile on relevant architectures, and assemble
    the focused test matrix and known limitations needed for review.

## Evidence And Discoveries

### Repository observations — 2026-08-15

- No TCI or command-mailbox abstraction is present in the repository.
- The current driver programs `runtime->dma_addr` directly into `0x10300`/`0x10304`, but the
  supporting Windows analysis describes those offsets as reads during initialization. Their DMA
  meaning is therefore a hypothesis, not a confirmed contract.
- The current driver uses a timer-driven synthetic position and permits an IRQ handler to report
  elapsed periods without a proven device interrupt-status/acknowledgement contract.
- The current ALSA surface advertises only stereo S16_LE even though the target device is
  multichannel and expected to require a richer sample/container layout.
- The existing plan searches for standalone sample-rate and format registers. The TCI lead implies
  that at least clock/rate control should instead be decoded as mailbox commands.

### Technical leads requiring local or public-source verification

- TCI is a device command mailbox and the critical prerequisite for initialization.
- Sample-rate switching is performed through TCI.
- Once TCI is operating, the DMA path is comparatively small.
- Direct ALSA playback and capture can operate at 192 kHz with a 128-frame buffer.
- 32- and 64-frame Linux runs may xrun heavily; an apparent macOS 32-frame setting may represent
  four 32-frame units packaged into an effective 128-frame transaction.
- A driver-scoped request for approximately 2 microsecond CPU wake latency during DMA may prevent
  crackling on Intel systems without disabling deep idle states globally.
- Multichannel I/O, device reliability, rapid initialization, and hot removal may already be
  attainable with the correct protocol.
- PipeWire/JACK trouble may be a missing device profile or userspace integration issue rather than
  proof that direct ALSA transport is broken.

## Decisions

- **2026-08-15 — Make TCI the primary discovery path.** The current raw-register approach has not
  initialized the device, while the mailbox model explains why isolated register guesses did not
  expose clocking or a complete DMA contract.
- **2026-08-15 — Use macOS behavior as an oracle, not macOS code as a porting target.** The Linux
  implementation must use native kernel and ALSA APIs and independently documented protocol facts.
- **2026-08-15 — Keep Windows evidence as corroboration.** Existing Ghidra work remains useful for
  matching offsets and flows but no longer determines the implementation order.
- **2026-08-15 — Prove ALSA before desktop stacks.** PipeWire/JACK work must not obscure whether the
  core mailbox, clock, DMA, IRQ, and channel contracts are correct.
- **2026-08-15 — Verify only the owned model by default.** Related device IDs remain disabled or
  explicitly opt-in until tested on physical hardware.

## Changes

- Created this active task and registered it in `docs/agents/tasks/index.yml`.
- Pre-task repository hygiene removed unused locals and an ignored speculative `STATUS5` pointer
  read. This does not implement or validate TCI.
- No live hardware state or canonical technical conclusion has been changed yet.

## Validation

- Confirm the task and task index parse and link correctly.
- Confirm the task contains only technical requirements, verification leads, and repository context.
- The hygiene-only driver change must compile without the prior unused-variable warnings.
- TCI implementation and live hardware validation have not started.

## Remaining Work

- Begin Plan step 1 by locating and provenance-checking public implementation and trace resources.
- Keep this as a single-file task initially. Migrate it to a folder with `index.yml` only when
  independent protocol, implementation, or validation branches require separate ownership.

## Closure Summary

Open. Close only after the TCI-first implementation and direct-ALSA acceptance criteria are proven,
durable findings are promoted, unsafe speculative paths are removed, and remaining desktop or
cross-device work is explicitly routed.
