# Quantum 2626 Linux Driver — Current Status

**Last updated:** 2026-08-15
**TL;DR:** Static analysis of the vendor's macOS DriverKit extension recovered the TCI mailbox,
audio page tables, IRQ contract, and 48 kHz channel order. The Linux module now reaches the
solid-blue ready state and exposes one fixed 48 kHz, 26-channel, S32_LE duplex PCM with 128-frame
periods. Direct ALSA playback and capture, physical headphone-left/right output, ordinary YouTube
playback, and bounded PipeWire duplex operation are live-proven. WirePlumber publishes 13 stereo
playback sinks and 26 independent mono capture sources; a standalone Line Input 5 recording was
also verified. Higher rates, mixer controls, MIDI, hot removal, and physical S/PDIF/ADAT routing
remain unproven.

## Evidence Labels

- **Observed Linux:** directly measured on this host/device.
- **Static analysis:** recovered from the x86_64 slice of the macOS DriverKit extension.
- **Implemented, unverified:** present in the Linux driver but not yet confirmed on hardware.
- **Hypothesis:** still requires static corroboration or a bounded live test.

## Current Host Baseline

- **Observed Linux:** PCI function `09:00.0` is `1c67:0104` and is bound to `snd_quantum2626`.
- **Observed Linux:** the running kernel is `7.0.11-76070011-generic` on x86_64.
- **Observed Linux:** ALSA card `P2626` exposes playback and capture device 0 on IRQ 214.
- **Observed Linux:** the installed and loaded module SHA-256 is
  `890dcde7ee8825c15492ead1e94acdfaf32be43462d645a6b070327c79ea6578`.
- **Observed Linux:** WirePlumber is active with 13 Quantum sinks and 26 mono Quantum sources; Main
  is the configured default sink at 31%.
- **Observed Linux:** Secure Boot is disabled, so an unsigned local test module is loadable after
  local sudo authentication.

## TCI Control Path

- **Static analysis:** TCI uses coherent TX/RX slot rings described by MMIO configuration at
  `0x007c` and controlled at `0x1000`.
- **Static analysis:** the eight-byte little-endian message header contains total length, channel,
  code, transaction ID, and a reserved field.
- **Static analysis:** control channel `0x31` provides power-state, clock-source, and sample-rate
  queries. See `notes/TCI_PROTOCOL.md` for the register and command tables.
- **Implemented and observed:** probe allocates/programs the mailbox rings, starts them with
  `0x1000 = 0x101`, and performs those three read-only queries with bounded timeouts.
- **Implemented and observed:** teardown stops TCI and waits before releasing coherent memory; if
  the engine does not stop, PCI bus mastering is cleared before buffers are freed.
- **Observed Linux:** bounded loads, including the current playback-capable artifact, reported 8 slots of
  4096 bytes, power on, clock source 1, clock rate 48000 Hz, and device rate 48000 Hz.
- **Observed Linux:** the final artifact registers `hw:P2626,0` for both playback and capture on IRQ
  214 and remains loaded for desktop use. Earlier registration-only gates unloaded cleanly after
  leaving PCM closed.
- **User-observed hardware:** the front-panel indicator changed to solid blue after the TCI probe
  and remained solid after the final module unload. This is the first locally observed device-ready
  indication; persistence while unbound suggests device initialization state survives TCI teardown.

## Corrected Audio-DMA Conclusions

- **Static analysis:** `0x10300` and `0x10304` report record/playback addresses-per-segment. They are
  not direct ALSA DMA-address registers.
- **Static analysis:** audio DMA uses page-table base registers at `0x11100` through `0x1111c`, main
  control at `0x11000`, and hardware position at `0x10104`.
- **Static analysis:** `0x11108`/`0x11118` contain the complete DMA buffer length in frames, while
  `0x1110c`/`0x1111c` contain the rate-adjusted hardware block length. At the current baseline those
  values must be the negotiated buffer size and 128 frames, respectively.
- **Static analysis:** position `0x10104` contains a 20-bit offset within that buffer and a 12-bit
  wrapping buffer-cycle counter. ALSA's ring pointer is the low 20-bit offset modulo buffer size.
- **Static analysis:** page tables are chains of 4 KiB coherent pages containing 64-bit
  `DMA page address | 1` entries. A link entry points to the next table page after the number of data
  entries reported by the device.
- **Observed Linux:** `0x10300`/`0x10304` report 15/15 addresses per segment and `0x10200` is
  `0x00001a1a`, meaning 26 capture and 26 playback channels.
- **Implemented:** the old timer-driven fake PCM position, speculative stream writes, and direct
  DMA-address writes to `0x10300`/`0x10304` have been removed.
- **Implemented:** one playback PCM is fixed to 48 kHz, 26 interleaved 32-bit channels,
  and 128-frame periods. It builds the recovered playback and zeroed capture page tables, programs
  the confirmed base registers, uses the hardware position for ALSA, and has bounded stop/failure
  handling.
- **Observed Linux:** the first five-second `/dev/zero` playback gate repeatedly reached page status
  `0x00000101` and raised audio interrupts. Its start/stop-only instrumentation sampled position as
  zero but did not capture transient in-IRQ values; userspace reported rapid underruns and restarted
  the stream. Every hardware stop completed, and the module was unloaded with the device unbound.
- **Static analysis:** the vendor driver never reads interrupt mask `0x11004`; it maintains a
  zero-based software shadow and writes the complete value. The Linux implementation now mirrors
  that rule, writes playback registers before capture, clears stale DMA registers before freeing
  coherent memory, and records raw IRQ/position evidence.
- **Observed Linux:** the instrumented retry captured nonzero raw positions on every recovery start,
  including `0x00400003` after four interrupts and `0x00a00001` after ten. It completed 369 bounded
  stop cycles without a stop timeout. After the same number of rapid xrun recoveries, one record-side
  page-fetch bit failed to return (`0x10308 = 0x00000100`) and ALSA exited with a prepare timeout.
  The module then unloaded cleanly and the PCI function is unbound.
- **Implemented and observed Linux:** Linux now writes the negotiated full buffer size to the
  buffer-frame registers and 128 to the block-frame registers. This directly fixes the mismatch
  revealed by the advancing 12-bit wrap counter.
- **Observed Linux:** the next approved gate stopped before playback because the first TCI power
  query timed out during probe. The driver failed closed, registered no ALSA endpoint, and was
  unloaded without retry; the PCI function is unbound. This is a control-mailbox recovery issue,
  not evidence against the untested audio buffer-length correction.
- **Static analysis/implemented:** vendor teardown zeros all TCI DMA address registers after stopping
  the mailbox. Linux now mirrors that cleanup and logs status plus TX/RX device/host positions on a
  future timeout.
- **Observed Linux:** one approved probe-only load of that cleanup artifact recovered the first power
  query without a physical reset. The next clock-source query timed out with active status
  `0x00010001`, TX positions `2/2`, and RX positions `2/2`. This proves the mailbox consumed both
  requests and produced two RX messages; Linux accepted the first response but not the second.
  No ALSA endpoint or stream was created, and unload completed with the device unbound.
- **Static analysis/implemented:** the vendor's synchronous control wait is 200 ms, so Linux's 250 ms
  bound is not shorter. Linux now logs only the channel, code, and transaction ID of a skipped RX
  header to distinguish an asynchronous event from a mismatched control response on the next probe.
- **Observed Linux:** that diagnostic probe received channel `0x31`, clock response `0x36`,
  transaction ID 1 while the new power query expected transaction ID 0. This was the delayed clock
  response from the preceding load, not an asynchronous event. The new power response then timed
  out; no ALSA endpoint appeared and unload was clean.
- **Static analysis/implemented:** Linux advanced the polled RX ring during probe but never performed
  the vendor's write-one-to-clear acknowledgement for TCI RX interrupt bit 31. The IRQ handler cannot
  do that yet because Linux requests the IRQ only after the TCI readiness queries. Polling now
  acknowledges bit 31 as soon as it observes each RX message. This directly explains a response
  remaining latched until the next module load cleared interrupt status, but requires live proof.
- **Observed Linux:** the acknowledgement probe accepted a power response, then skipped another
  delayed power response (`0x3c`, transaction ID 0) while waiting for clock transaction ID 1. It
  acknowledged the stale header, but the expected clock response did not arrive before the original
  shared deadline. No PCM appeared; unload remained clean and the device is unbound.
- **Implemented then retired:** one diagnostic artifact seeded each TCI transaction sequence from
  kernel ticks and granted a fresh bounded response window after an acknowledged stale/event header.
- **Observed Linux:** the seeded-transaction probe skipped a delayed clock response with transaction
  ID 1 while its power query used ID 33369, but received no current response. This did not recover
  the mailbox, so the seeding experiment was retired pending a clearer cross-load result.
- **Implemented, bounded probe did not recover:** transaction IDs again start at zero. Before sending any query, Linux
  now drains and acknowledges header-only stale RX entries until the ring stays quiet for 250 ms,
  capped at one second and one ring of messages. Only then does it issue the normal readiness
  sequence; the existing per-query stale skip remains as a second bounded guard.
- **Observed Linux:** the approved drain probe saw no RX entry during that quiet interval. After the
  new power request (transaction ID 0), the prior seeded probe's power response (`0x3c`, transaction
  ID 33369) appeared. Linux acknowledged and skipped it, but the current power response timed out
  with active status `0x00010001` and synchronized TX/RX positions `1/1`. Probe failed closed, no
  ALSA card appeared, unload was clean, and the PCI function is unbound.
- **Static conclusion from the bounded probe series:** the pending response is not exposed to a
  passive startup drain in the current device state; later request activity releases it. Repeating
  the same load-only experiment would advance rather than clear that cross-load pipeline. The
  returned transaction ID 33369 also proves that the device accepted the seeded nonzero ID, so a
  required zero-based sequence is no longer the leading hypothesis.
- **Observed Linux:** after a user-controlled full interface power cycle, a separately approved
  probe of the same artifact completed cleanly with no stale header. It reported power on, clock
  source 1, and 48000 Hz clock/device rates, then registered ALSA card `P2626` on IRQ 214. PCM
  remained closed. Immediate unload succeeded; the module is absent, the PCI function is unbound,
  and the temporary ALSA card is gone.
- **Conclusion:** the full device power cycle cleared the retained cross-load mailbox condition.
  The failure is therefore separate from the audio buffer-length correction, though its exact
  persistence mechanism remains unresolved.
- **Observed Linux:** one separately approved five-second `/dev/zero` playback used direct
  `hw:P2626,0` at 48000 Hz, 26-channel S32_LE, 128-frame periods, and a 256-frame buffer. ALSA
  prepared 26624 bytes, both page-table fetch bits asserted (`0x00000101`), and `aplay` exited 0
  without underrun or recovery output. The driver counted exactly 1875 audio interrupts, matching
  `48000 / 128 * 5`, and stopped from packed position `0x3a900083` without a timeout. PCM closed,
  immediate unload succeeded, and the host returned to module-absent/device-unbound/ALSA-absent.
- **Static analysis:** the macOS DEXT playback table begins with `Main Out Left` and `Main Out
  Right`, and its compact 2626 route labels are `Main Out L/Line Out 1/HP Out L` and the matching
  right channel. Playback channels 1-2 are therefore the narrow pair for a Main/Headphone test; all
  other 24 DMA channels must remain zero.
- **Observed Linux:** one approved `speaker-test` invocation targeted playback channel 1 with a
  440 Hz sine at 1% digital scale and a four-second hard cap; the other 25 channels were zero.
  ALSA negotiated exactly 128/256 frames, page status reached `0x00000101`, and the bounded run
  produced 1499 IRQs plus packed position `0x2ed00082` with no xrun or stop timeout. Exit 124 was the
  intentional outer time cap. PCM closed and immediate unload restored the safe baseline. The user
  did not hear this first run because the headphone level was too low.
- **Observed Linux and user-observed hardware:** after the user slightly raised only the headphone
  level, one separately approved repeat used the identical channel, signal, amplitude, and hard
  cap. It produced 1498 IRQs, reached packed position `0x2ed00002`, and again stopped without an
  xrun or timeout. The user clearly heard the tone. Immediate unload returned to the confirmed
  module-absent/device-unbound/ALSA-absent baseline. This proves playback channel 1 reaches the
  physical headphone-left output; the DEXT statically aliases that channel to Main left/Line Out 1.
- **Observed Linux and user-observed hardware:** one separately approved identical test targeted
  playback channel 2. ALSA again negotiated 128/256 frames; 1498 IRQs fired, packed position reached
  `0x2ed00000`, and stop completed without an xrun or timeout. The user heard the tone on the right.
  Immediate unload restored the safe baseline. This proves playback channel 2 reaches the physical
  headphone-right output; the DEXT statically aliases it to Main right/Line Out 2. This completes
  the bounded headphone-stereo routing check.

## Channel Tables And Desktop Routing

- **Static analysis:** the exact 44.1/48 kHz playback order is analog outputs 1-8, S/PDIF 1-2, then
  ADAT 1-16. The 88.2/96 kHz profile retains only ADAT 1-8, while the 176.4/192 kHz profile contains
  only the eight analog channels. Capture follows the corresponding input order. The sanitized
  tables and zero-based bindings are recorded in `notes/CHANNEL_ROUTING.md`.
- **Implemented and live-proven:** `alsa/ucm2/P2626/HiFi.conf` exposes Main, Line 3-4, Line 5-6,
  Line 7-8, S/PDIF 1-2, and eight ADAT stereo pairs over one shared `dshare` stream. A shared
  `dsnoop` stream exposes every capture channel independently as 26 mono sources from
  Mic/Instrument Input 1 through ADAT Input 16. Both directions are fixed to the live-proven
  48 kHz, S32_LE, 26-channel, 128/256-frame contract; higher-rate endpoints remain intentionally
  absent.
- **Offline validation:** an isolated ALSA UCM2 parser enumerated the HiFi verb, all 13 playback
  devices, and all 26 mono capture devices. The staged `make install-ucm` output matched the tracked
  inputs byte-for-byte. This alone does not prove capture transport, PipeWire source discovery,
  simultaneous opens, digital lock, or physical input; the transport and desktop cases were then
  tested live as recorded below.
- **Observed Linux:** the exact module artifact and three UCM files were installed byte-for-byte.
  One module load completed the TCI handshake at 48 kHz and registered card `P2626` on IRQ 214.
  WirePlumber did not react to the late ALSA hotplug until it was restarted once; after that restart
  PipeWire published the Quantum device and all 13 intended named sinks. The existing default sink
  remained the Poly BT700.
- **Observed Linux:** one short stereo fixture was sent through the PipeWire Main / Line 1-2 /
  Headphones sink at 3% stream volume while the sink was at 31%. `pw-play` exited 0. The kernel
  prepared the exact 26624-byte, 256-frame buffer with 128-frame blocks and page status
  `0x00000101`, advanced through 1,941 audio IRQs, and stopped cleanly from position `0x3ca00080`.
  PCM status returned to `closed`; no kernel xrun or timeout was reported. The short low-volume
  fixture was not used as the physical acceptance result.
- **User-observed hardware:** immediately afterward, ordinary YouTube playback routed through the
  Quantum PipeWire sink was clearly audible through the connected headphones. This confirms the
  normal desktop-application path from PipeWire through UCM/dshare, the 26-channel ALSA PCM, and the
  physical Main/Headphone pair.
- **Observed Linux:** initial WirePlumber enumeration briefly prepared/started/stopped the shared
  PCM for multiple endpoints, including zero-IRQ starts. Every observed stop was bounded and no
  page-fetch or stop timeout occurred.
- **Implemented and observed:** the driver registers one 26-channel capture substream
  alongside playback. Configured directions use their ALSA runtime DMA buffers; an inactive
  direction receives a bounded coherent dummy buffer because the hardware engine always runs both
  page-table sides. One IRQ advances every active substream, while start/stop bookkeeping keeps one
  direction running when the other stops. Both directions must use the same buffer geometry.
- **Offline validation:** the duplex artifact builds with `W=1`, passes kernel `checkpatch` with
  0 errors and 0 warnings, and has SHA-256
  `890dcde7ee8825c15492ead1e94acdfaf32be43462d645a6b070327c79ea6578`. The UCM parser enumerates
  all 13 playback sinks and 26 one-channel capture sources, from Mic/Instrument Input 1 through
  ADAT Input 16. `LineInput5` reports one channel and binds only zero-based channel 4.
- **Observed Linux:** a five-second direct `hw:P2626,0` capture exited 0, wrote the exact expected
  24,960,044-byte 48 kHz/S32_LE/26-channel WAV, delivered exactly 1,875 period IRQs, and stopped
  cleanly. Analog channels 1-8 and ADAT channels 1-8 contained changing samples; unconnected
  S/PDIF and ADAT 9-16 were zero. This proves capture transport, not physical input labels.
- **Observed Linux:** PipeWire's ACP probe initially exposed a real joint-engine lifecycle defect:
  playback was running when capture `HW_PARAMS` arrived, and the driver returned `EBUSY`. The final
  artifact pauses the shared engine, rebuilds both DMA tables, and resumes the already-running
  direction. ACP then accepted the HiFi profile. The current mono UCM profile publishes all 13
  sinks and all 26 sources.
- **Observed Linux:** a bounded PipeWire test started Main playback, added Mic/Instrument 1-2
  capture while playback was active, recorded changing samples on both channels, removed capture,
  and continued playback. The joint reconfiguration prepared directions `0x3`; all operations were
  bounded, both PCM states returned to `closed`, and no xrun or timeout was reported. The exact
  installed and loaded module hash is the offline-validated hash above. WirePlumber is active and
  Main was restored to 31% volume.
- **Observed Linux:** after the capture endpoints were split from stereo pairs into mono sources,
  WirePlumber published exactly 26 one-channel Quantum sources without a module reload. A bounded
  `Line Input 5` PipeWire capture produced a 48 kHz/S32_LE mono WAV with 94,316 sample changes in
  the inspected 96,000-sample window. It binds only hardware channel 5 (zero-based 4). Main
  remained at 31%, active playback was preserved, and no kernel fault marker appeared.

## What Is Proven Today

- The module builds against the running kernel headers with `W=1`.
- Its PCI alias is intentionally limited to the owned/tested Quantum 2626 (`1c67:0104`).
- The device accepts the recovered TCI ring setup and returns correctly correlated control
  responses on Linux. This proves the mailbox/control slice, not audio transport.
- The same probe produced the physical solid-blue ready indication that the prior speculative
  initialization attempts never achieved.
- Direct ALSA playback transport is stable for the bounded 48 kHz digital-silence case: both page
  tables fetched, audio IRQ bit 8 fired at the exact expected period rate, the packed hardware
  position advanced, userspace completed without an xrun, and stop was bounded.
- Playback channels 1 and 2 produce physically audible output on the Quantum 2626 headphone-left
  and -right paths at a controlled low level. Static DEXT labels place Main/Line 1-2 on the same
  DMA pair, but the rear Main jacks have not been independently listened to.
- Direct 26-channel ALSA capture and named PipeWire mono capture both deliver changing samples.
  PipeWire playback and capture can run concurrently through the shared hardware DMA engine.
- The source contains no vendor binary or decompiler output. The proprietary installer, extracted
  extension, and analysis products remain outside the repository under `/tmp`.

## Immediate Next Steps

1. Apply a known signal to each analog input and connect a clock-compatible S/PDIF/ADAT sender to
   validate physical source identity, digital lock, and every advertised input channel.
2. With a clock-compatible receiver connected, validate S/PDIF and ADAT output pairs individually
   and then validate concurrent `dshare` endpoints. Do not infer physical digital lock from a
   parsed profile.
3. Implement rate switching as a later driver slice. Do not advertise 96/192 kHz, latency QoS, hot
   removal, or JACK support from the current fixed-rate result.
