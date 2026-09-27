# TASK-001 TCI Mailbox Recovery From macOS Traces

## Status

Closed — 2026-08-15

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

- `notes/CURRENT_STATUS.md`: canonical current evidence; it now records confirmed TCI readiness,
  stable bounded DMA, and audible stereo output.
- `driver/snd-quantum2626.c`: the task started from experimental direct MMIO writes, a synthetic
  timer-driven pointer, stereo-only S16 constraints, and no TCI/mailbox model; those limitations are
  historical and have been replaced by the implementation validated below.
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

### Initial repository observations — 2026-08-15 (superseded by this task)

- No TCI or command-mailbox abstraction was present in the repository.
- The initial driver programmed `runtime->dma_addr` directly into `0x10300`/`0x10304`, but the
  supporting Windows analysis describes those offsets as reads during initialization. Their DMA
  meaning is therefore a hypothesis, not a confirmed contract.
- The initial driver used a timer-driven synthetic position and permitted an IRQ handler to report
  elapsed periods without a proven device interrupt-status/acknowledgement contract.
- The initial ALSA surface advertised only stereo S16_LE even though the target device is
  multichannel and expected to require a richer sample/container layout.
- The initial plan searched for standalone sample-rate and format registers. The TCI lead implied
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

### macOS DriverKit static analysis — 2026-08-15

- Public-source searches found no independently reviewable completed Linux implementation or patch
  series to import. The implementation therefore uses independently expressed protocol facts from
  a current official macOS installer; it does not copy vendor code.
- The official installer contains a universal DriverKit extension, version 2.19.0, whose PCI match
  includes `0x01041c67`. Artifact hashes and the redistributable protocol notes are recorded in
  `notes/TCI_PROTOCOL.md`; binaries and decompiler output remain outside the repository in `/tmp`.
- **Static analysis:** TCI is an eight-byte-header message protocol over coherent TX/RX slot rings.
  The complete mailbox register map, producer/consumer ownership, lengths, and start/stop controls
  are now recovered.
- **Static analysis:** read-only control requests cover power (`0x3b`/`0x3c`), clock source
  (`0x33`/`0x36`), and sample rate (`0x31`/`0x35`). Sample-rate values use a compact enum rather
  than raw Hz on the wire.
- **Static analysis:** interrupt status/acknowledgement is at `0x10004`, with audio DMA at bit 8 and
  TCI RX at bit 31. The prior Linux handler's use of `0x0004` was unsupported.
- **Static analysis:** `0x10300` and `0x10304` are record/playback addresses-per-segment geometry,
  not DMA buffer address registers. Audio uses page-table registers `0x11100` through `0x1111c`,
  control `0x11000`, and position `0x10104`.
- **Static analysis:** audio page tables are chained 4 KiB pages of little-endian 64-bit
  `DMA page address | 1` entries. The hardware-reported addresses-per-segment value determines the
  number of data entries before an optional next-table-page link.
- **Observed Linux:** the local device reports 15/15 record/playback addresses per segment and
  `0x10200 = 0x00001a1a`, confirming 26 capture and 26 playback channels.

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
- **2026-08-15 — Gate PCM behind real DMA.** The previous fake pointer and speculative buffer
  writes could report progress without moving audio and targeted disproven offsets. PCM was kept
  closed until the page-table contract was recovered and now exposes only the constrained first
  implementation slice; it is not yet claimed functional.

## Changes

- Created this active task and registered it in `docs/agents/tasks/index.yml`.
- Pre-task repository hygiene removed unused locals and an ignored speculative `STATUS5` pointer
  read. This does not implement or validate TCI.
- Added `notes/TCI_PROTOCOL.md` and reconciled `notes/CURRENT_STATUS.md` and
  `notes/REGISTER_GUESSES.md` with the macOS static analysis.
- Added `scripts/ghidra/ExportNamedFunctions.java` for selective symbol-based disassembly and
  decompilation to an explicitly caller-chosen output outside the repository.
- Replaced speculative probe and fake PCM behavior with cohesive TCI ring/start/stop/control helpers,
  three bounded read-only control queries, corrected IRQ status acknowledgement, safe unwind, and a
  Quantum-2626-only PCI table.
- Added the smallest playback-only ALSA/page-table slice, constrained to the observed 48 kHz clock,
  26 interleaved 32-bit channels, and 128-frame periods. It allocates the vendor-required zeroed
  capture side as well as playback, uses chained page tables and the real hardware position, and
  fails closed on page-fetch or stop timeouts.
- Corrected audio interrupt-mask handling to mirror the vendor driver's zero-based software shadow
  rather than reading `0x11004`. Playback registers are now programmed before capture, stale table
  registers are cleared before coherent memory is freed, and the IRQ path retains raw status and
  position evidence for the next bounded run.
- Corrected the DMA size mapping after live IRQ telemetry exposed the packed position fields. The
  vendor `UpdateDmaPosition` path confirms that `0x11108`/`0x11118` are full-buffer frame counts,
  `0x1110c`/`0x1111c` are hardware-block frame counts, and `0x10104` packs a low-20-bit within-buffer
  offset with a high-12-bit buffer-cycle counter.
- Mirrored the vendor's TCI teardown cleanup by zeroing slot address/length registers after the
  engine stops and before coherent memory is released. Timeout diagnostics now retain mailbox
  status and all four TX/RX device/host positions without exposing DMA addresses.

## Validation

- `make -C /lib/modules/$(uname -r)/build M=$PWD/driver W=1 modules` passes against the running
  kernel headers. Only host tool metadata warnings (compiler command spelling and missing BTF
  `vmlinux`) remain.
- `git diff --check` passes.
- Kernel `checkpatch.pl --no-tree --file driver/snd-quantum2626.c` reports 0 errors and 0 warnings.
- `modinfo` reports only the `1c67:0104` PCI alias and the expected running-kernel vermagic.
- The post-first-run shadowed-mask/register-order correction also passed the same `W=1` build,
  `checkpatch.pl` (0 errors, 0 warnings), `git diff --check`, and `modinfo` checks before its bounded
  live retry.
- The subsequent full-buffer/block-frame correction passes the same static checks. Its built module
  hash was `9cf3c95c6ff1328ecba398ebd774a4a56f5aa4d178534d3075d5a8189a725db0` at the aborted
  probe gate described below; audio callbacks were never reached.
- The TCI cleanup/timeout-diagnostic artifact also passes those static checks. Its hash is
  `7e76c8b91c1edb34eda965dd857ce7e76cab0c470fababb41459380f44970ffd`; its probe-only result is
  recorded below.
- The subsequent skipped-RX-header diagnostic artifact passes the same checks and has hash
  `182412d7b9370e6c6c2e9d05da7757d949fe2c3bd259d6e55253d15eafbb3737`; its probe-only result is
  recorded below.
- The missing-TCI-RX-acknowledgement artifact passes the same checks and has hash
  `54432e11f0c54f3ea43f47fa1f3d155776306a16532767fd31b0443ebae5048d`; its probe-only result is
  recorded below.
- The bounded stale-response recovery artifact passes the same checks and has hash
  `35997003b283415d225196d7722a49817fc36da3605b964922ba747956b3c90a`; its probe-only result is
  recorded below.
- The subsequent pre-query stale-RX drain artifact passes the same checks and has hash
  `a1c7cd139fbd44a348b29cc7a9a891c6c6d5b4070bd813c2e9b819301379cc0a`; its probe-only result is
  recorded below.
- The then-current desktop-routing artifact passed the same build, `checkpatch` (0/0), `diff --check`,
  alias, and vermagic checks and has hash
  `fc345f8880d6df9eac76028be20501aefc20c6b0edac40f4679301af6f56f222`. Its only driver-source
  behavior change was correcting a misleading start log; that intermediate artifact was not loaded
  on hardware.
- Secure Boot is disabled and the physical `1c67:0104` endpoint is present and initially unbound.
- **Observed Linux:** bounded module loads succeeded, including the then-current playback artifact. The
  device reported an 8-slot, 4096-byte TCI ring, power on, clock source 1, and 48000 Hz for both
  clock and device rates.
- **Observed Linux:** that intermediate artifact registered `hw:P2626,0` as a playback endpoint on IRQ
  214. The endpoint was not opened, so page-table programming and audio DMA were not exercised.
  Unload was clean with no stop warning; the PCI function became unbound and the ALSA card vanished.
- **User-observed hardware:** the interface indicator became solid blue after the TCI probe and was
  still solid after the final unload. This is the first local ready-state indication and strongly
  connects successful initialization to the recovered TCI path; it does not by itself prove audio
  DMA.
- **Observed Linux:** one explicitly approved five-second digital-silence run fetched both page
  tables (`0x10308 = 0x00000101`) and raised audio interrupts. ALSA repeatedly recovered from rapid
  underruns. Start/stop-only instrumentation sampled `0x10104` as zero, but did not sample it inside
  the IRQ. All hardware stops completed, then the module unloaded and the PCI function was unbound.
- **Observed Linux:** the separately approved instrumented retry proved DMA movement. Raw positions
  included `0x00400003` after four interrupts and `0x00a00001` after ten, with bit 8 as the only raw
  IRQ source. ALSA performed 369 prepare/start/stop recovery cycles; all 369 stops completed and none
  timed out. The recovery storm eventually produced one page-fetch timeout at `0x00000100`, after
  which userspace exited and the module was unloaded. The PCI function is again unbound.
- **Static conclusion from combined evidence:** Linux incorrectly wrote 128 to both the full-buffer
  and block-frame registers. The hardware therefore advanced and wrapped its cycle counter every
  128 frames while ALSA owned a 256-frame ring. The source now writes the negotiated buffer frames
  to the former and 128 to the latter. Its first gate did not get past TCI probe, so that attempt did
  not validate the correction; the later post-power-cycle result below does.
- **Observed Linux:** the following approved gate did not reach playback. The exact corrected module
  began TCI setup, but its first read-only power query timed out; probe returned `-110`, no ALSA PCM
  appeared, and no stream command ran. The module was unloaded without a probe retry, leaving the
  PCI function unbound. This does not validate or invalidate the buffer-length correction.
- **Observed Linux:** a separately approved probe-only load of the cleanup artifact recovered the
  power query without a physical reset. Clock-source then timed out with active status `0x00010001`
  and synchronized TX/RX device/host positions of `2/2`. The hardware consumed both requests and
  produced two RX messages, but Linux accepted only the first as its matching response. No ALSA PCM
  or stream was created; unload was clean and the function is unbound.
- **Static analysis:** the vendor synchronous control wait is 200 ms, versus Linux's 250 ms, ruling
  out a shorter Linux timeout as the direct cause. Header-only skipped-RX diagnostics are now added
  to classify an asynchronous event versus a code/transaction mismatch on a future probe.
- **Observed Linux:** the diagnostic probe classified the message as channel `0x31`, response code
  `0x36`, transaction ID 1 while a new power request expected transaction ID 0. It was the delayed
  clock-source response from the preceding load. The current power response did not arrive before
  timeout; no PCM appeared, and unload remained clean.
- **Static conclusion:** the polling probe advanced RX ownership but did not acknowledge TCI RX
  interrupt bit 31. Since IRQ registration occurs only after the three readiness queries, the IRQ
  handler could not clear it. The vendor acknowledges this source for each RX interrupt. Linux now
  writes the bit-31 W1C as soon as polling observes an RX message; this is the leading explanation
  for responses remaining latched until the next load's initial status clear.
- **Observed Linux:** the acknowledgement probe accepted power, then skipped another delayed power
  response (`0x3c`, transaction ID 0) while clock transaction ID 1 was pending. The stale header was
  acknowledged, but the expected clock response did not arrive within the original deadline. No PCM
  appeared, and the clean unload left the device unbound.
- **Implemented then retired:** one diagnostic artifact seeded TCI transaction IDs from kernel
  ticks to prevent predictable cross-load matches and reset the bounded response window after a
  skipped stale/event response.
- **Observed Linux:** the seeded probe skipped a delayed clock response with transaction ID 1 while
  its power request used ID 33369, but no current power response arrived. It did not recover the
  mailbox, so the seeding experiment was retired pending a clearer cross-load result.
- **Implemented, bounded probe did not recover:** TCI transactions again start at zero. Before issuing a query, Linux
  drains and acknowledges stale RX headers until 250 ms of quiet, capped at one second and one ring.
  The normal queries begin only after that bounded drain; per-query stale skipping remains guarded.
- **Observed Linux:** the approved drain probe reached its quiet interval without seeing a pending
  RX entry. Only after Linux submitted the new power query with transaction ID 0 did the prior
  seeded probe's power response (`0x3c`, transaction ID 33369) appear. Linux acknowledged and
  skipped it, then the current power query timed out with status `0x00010001`, TX positions `1/1`,
  and RX positions `1/1`. No ALSA endpoint appeared; unload was clean and the device is unbound.
- **Static conclusion from the bounded probe series:** the delayed response is not visible to a
  passive post-start drain in the current device state. It is released only after later request
  activity, so repeated load-only recovery experiments would just advance the same cross-load
  response pipeline. The seeded response also proves the device accepted a nonzero transaction ID;
  zero-based sequencing was not the cause of that probe's timeout.
- **Observed Linux:** after a user-controlled full interface power cycle, one separately approved
  probe of the same `a1c7cd...` artifact completed all three TCI queries without a stale header:
  power on, clock source 1, and 48000 Hz clock/device rates. ALSA card `P2626` registered on IRQ 214,
  its PCM remained closed, and the module was immediately unloaded. The module is absent, the PCI
  function is unbound, and the Quantum ALSA card is absent again.
- **Conclusion:** the full device power cycle cleared the retained cross-load mailbox condition.
  This isolates that failure from the audio buffer-length correction, but does not yet establish
  why the device retained the response pipeline across software teardown.
- **Observed Linux:** one separately approved five-second `/dev/zero` playback then used direct
  `hw:P2626,0` at 48000 Hz, 26-channel S32_LE, 128-frame periods, and a 256-frame buffer. Preparation
  reported 26624 bytes and page status `0x00000101`. `aplay` exited 0 with no underrun/recovery
  output; the driver counted exactly 1875 IRQs, the expected `48000 / 128 * 5`, and stopped cleanly
  from packed position `0x3a900083`. PCM closed, immediate unload succeeded, and the host returned
  to module-absent/device-unbound/ALSA-absent. This validates the corrected buffer/block mapping for
  the bounded 48 kHz digital-silence case.
- **Static analysis:** the DEXT's 2626 playback table begins with `Main Out Left` and `Main Out
  Right`; its compact route labels explicitly combine `Main Out L/Line Out 1/HP Out L` and the
  corresponding right path. The narrow audible check should therefore target playback channel 1
  only and force the remaining 25 channels to zero.
- **Observed Linux:** one approved `speaker-test` invocation targeted channel 1 with a 440 Hz sine
  at 1% digital scale and a four-second hard cap, while keeping the other 25 channels zero. ALSA
  negotiated the exact 128/256-frame geometry; page status reached `0x00000101`, 1499 IRQs fired,
  packed position reached `0x2ed00082`, and stop completed without an xrun or timeout. Exit 124 was
  the intentional outer cap. PCM closed and immediate unload returned to the safe baseline. The
  user did not hear this first run because the headphone level was too low.
- **Observed Linux and user-observed hardware:** after the user slightly raised only the headphone
  level, one separately approved identical repeat produced 1498 IRQs, reached packed position
  `0x2ed00002`, and stopped without an xrun or timeout. The user clearly heard the tone. Immediate
  unload restored module-absent/device-unbound/ALSA-absent. This proves channel 1 reaches the
  physical headphone-left path and is the first confirmed audible Linux playback result; the DEXT
  statically aliases that DMA channel to Main left/Line Out 1.
- **Observed Linux and user-observed hardware:** one separately approved identical test targeted
  channel 2. ALSA again negotiated 128/256 frames; 1498 IRQs fired, packed position reached
  `0x2ed00000`, and stop completed without an xrun or timeout. The user heard the tone on the right.
  Immediate unload restored the safe baseline. This proves the physical headphone-right route and
  completes the bounded headphone-stereo check; the DEXT statically aliases that DMA channel to
  Main right/Line Out 2. The rear Main jacks were not independently listened to.
- **Static analysis:** bounded export of the DEXT's named Quantum 2626 model tables recovered the
  complete rate-dependent channel profiles. At 44.1/48 kHz playback is analog 1-8, S/PDIF 1-2,
  then ADAT 1-16; at 88.2/96 kHz ADAT contracts to 1-8; at 176.4/192 kHz only analog 1-8 remains.
  Capture uses the corresponding Mic/Instrument, Line, S/PDIF, and ADAT order. The proprietary
  analysis product remains under `/tmp`; `notes/CHANNEL_ROUTING.md` contains only the sanitized
  resulting table.
- **Implemented offline, unverified on hardware:** the new UCM profile exposes 13 stereo playback
  endpoints through one 48 kHz, 26-channel S32_LE `dshare` slave fixed to 128/256 frames. An isolated
  UCM2 parser run enumerated the HiFi verb and all 13 devices, and `make install-ucm` reproduced the
  three tracked configuration files byte-for-byte in a temporary staged root.
- **Observed Linux:** the exact module and UCM bytes were installed. One module load completed TCI
  readiness at 48 kHz and registered `P2626`; after one WirePlumber restart, PipeWire published the
  Quantum device plus all 13 named playback sinks. One low-volume fixture targeted the Main sink,
  `pw-play` exited 0, hardware DMA advanced through 1,941 IRQs, and stop completed from packed
  position `0x3ca00080` with PCM closed and no kernel xrun or timeout. The short fixture was not used
  for physical acceptance.
- **User-observed hardware:** subsequent ordinary YouTube playback routed through the Quantum
  PipeWire sink was clearly audible through the connected headphones. This confirms the complete
  normal desktop path through PipeWire, UCM/dshare, the 26-channel ALSA transport, and the physical
  Main/Headphone stereo pair.
- **Implemented and live-proven:** the driver registers a 26-channel capture substream, builds
  the record page table from its ALSA runtime buffer, advances both active directions from the shared
  hardware IRQ, and keeps independent direction start/stop state over the hardware's joint DMA
  engine. Inactive directions retain bounded coherent dummy buffers. The UCM profile adds one shared
  `dsnoop` PCM and 26 named mono sources covering Mic/Instrument, Line, S/PDIF, and ADAT 1-16.
- **Offline validation:** the duplex artifact passes `W=1`, `checkpatch` (0/0), `diff --check`, and
  has hash `890dcde7ee8825c15492ead1e94acdfaf32be43462d645a6b070327c79ea6578`. Isolated UCM parsing
  enumerates all 13 sinks and all 26 mono sources with the intended first/last bindings.
- **Observed Linux:** a five-second direct 26-channel capture exited 0 with the exact expected
  1,875 IRQs and changing data on connected/noisy analog and ADAT lanes. PipeWire profile probing
  exposed and drove a joint-engine reconfiguration fix; afterward WirePlumber published 13 sinks
  and the initial 13 paired sources. A bounded Mic/Instrument 1-2 recording then ran concurrently
  with Main playback, contained changing samples on both channels, and both directions stopped
  cleanly without an xrun or timeout. The exact final hash above remains installed and loaded;
  WirePlumber is active.
- **Observed Linux:** the capture UCM was subsequently refined to expose every input independently,
  removing the Windows-style stereo-pair annoyance. WirePlumber now publishes 26 mono sources. A
  bounded `Line Input 5` recording opened only binding 4, produced changing mono samples, preserved
  active playback, and reported no kernel fault marker.

## Remaining Work

- **Implemented and live desktop discovery validated:** ALSA UCM exposes Main, three additional
  analog pairs, S/PDIF, and all eight 48 kHz ADAT pairs through one shared 26-channel `dshare`
  stream with the driver's exact 128/256-frame geometry. PipeWire discovers all 13 endpoints and a
  Main stream advances and stops cleanly. Multiple simultaneous `dshare` endpoints and physical
  digital output remain separately approved live integration gates.
- **Completed:** direct capture, all 26 mono PipeWire sources, and bounded playback/capture
  concurrency.
- Add rate switching and rate-dependent channel constraints before exposing the statically recovered
  96 kHz or 192 kHz profiles.
- Keep this as a single-file task initially. Migrate it to a folder with `index.yml` only when
  independent protocol, implementation, or validation branches require separate ownership.

## Closure Summary

Closed on 2026-08-15. The task achieved its baseline objective: the TCI-first driver reaches device
readiness, direct 48 kHz ALSA playback and capture are stable, Main/Headphone playback is physically
audible, PipeWire publishes 13 playback sinks and 26 mono capture sources, and bounded desktop
duplex operation is proven. Durable protocol, routing, status, and hardware evidence is recorded in
the canonical notes.

Deferred follow-up is intentionally not part of this commit's completion claim: sample-rate
switching, physical S/PDIF/ADAT validation, mixer controls, MIDI, hot removal, latency tuning, JACK,
additional hardware models, packaging, release policy, and upstream submission preparation.
