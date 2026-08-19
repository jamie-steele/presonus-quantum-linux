# TASK-002 Release Performance Hardening

## Status

Native 44.1 kHz desktop playback is live-proven at 26-channel S32_LE, 128-frame periods, and a
512-frame hardware buffer. Playback-only `slowptr true`, 256 frames of PipeWire headroom, and the
System76 Scheduler exception materially reduce the fault, but occasional pops remained. A bounded
2-us `/dev/cpu_dma_latency` A/B then produced the first user-observed pop-free interval: “I didnt
hear a single pop its clear af.” Releasing the request restored deep-idle counter activity, proving
the intervention was active and reversible. The source now tightens ALSA's existing per-substream
CPU-latency request to 2 us after a successful Quantum PCM prepare. The exact cleanly built
candidate has now been installed and loaded, with all five audio
units and the 13/26 endpoint graph restored. Ordinary playback immediately reproduced crackle even
though the 2-us request demonstrably suppressed deep idle and every transport/scheduling invariant
remained clean. The exact QoS-only discriminator is now installed and loaded: PipeWire returned to
32 resolution bits while 44.1 kHz, 128/512 hardware geometry, headroom, endpoint inventory, and
realtime scheduling remain fixed. User-started playback is immediately clean and received the
strongest acceptance yet. A later NeuralRack test exposed a distinct native-44.1 duplex lifecycle
failure: capture-first startup silenced playback, capture teardown restored playback with crackle,
and a complete playback-only close/reopen restored clean audio. Preserve the accepted playback
configuration while fixing live duplex reconfiguration separately. A narrow offline candidate now
replaces one-sided live DMA-table rebuilds with persistent fixed playback/capture buffers, ALSA
synchronized-start handling, and a late-direction wait for the next hardware-ring wrap. The exact
refined build is installed and loaded, and playback returned at native 44.1 kHz/128/512. Desktop
recovery is incomplete: all 13 sinks returned, but WirePlumber aborted one audio adapter and none
of the 26 capture sources are currently published. Preserve this state pending a separately
authorized recovery. A later approved WirePlumber-only restart entered the known pending-linkable
wedge. A separately approved restart of all five audio units restored registry responsiveness, but
the graph still contains 13 sinks and zero sources. Both PCMs remain available and capture discovery
repeatedly reaches exact 44.1 kHz/128/512 prepare/start/stop before WirePlumber aborts the adapter.
The compatibility A/B that removes only synchronized-start metadata and grouped trigger completion
while retaining stable buffers and wrap alignment is now installed and loaded. Its exact activation
again produced 13 sinks and zero sources, rejecting synchronized-start handling as the cause of the
capture-adapter failure. More importantly, capture discovery emitted an IOMMU DMA-write fault from
PCI `09:00.0` to address zero. Playback remains live at native 44.1 kHz/128/512 and capture is
closed. The source now addresses that exact teardown window by mapping the fixed maximum ALSA
playback/capture allocations once and retaining both DMA page tables and their MMIO addresses across
`hw_free`, rate changes, and rapid discovery probes; active buffer geometry remains independently
programmed at prepare. The candidate builds cleanly and is installed and loaded. Its separately
authorized activation loaded the exact artifact and restarted all five
audio units. The same capture-probe storm completed without another DMAR/IOMMU, stop, or page-table
fault, validating the narrow lifetime correction, but WirePlumber again destroyed one audio adapter
and the stable graph remains 13 sinks/0 sources. Playback is live at 44.1 kHz/128/512 and capture is
closed. User listening then found a new weird static artifact. Geometry, IRQ cadence, and fault logs
remain clean, isolating the full-maximum-buffer page-table extent as the leading regression variable.
Reject this runtime candidate. The source now keeps the coherent table allocation persistent while
populating and linking only active-buffer pages; geometry changes repopulate the same allocation.
The corrected artifact builds cleanly and is installed and loaded. Its separately authorized
activation loaded the exact
active-page artifact and restarted all five audio units. Playback returned at native 44.1 kHz/128/512
without a DMA/IOMMU, stop, or page-table fault. Initial user listening reports “sounds pretty good
now,” followed by sustained ordinary gaming use with “no pops at all” and “super stable.” The
maximum-map static regression and earlier intermittent pops are not reproduced in this interval. WirePlumber
had only published 13 sinks/0 sources at the activation controller's bounded 10-second checkpoint.
A later direct read-only snapshot, without another restart or module action, found the complete
13-sink/26-source graph. Capture publication therefore recovers after a longer settle; capture
remains closed and native-44.1 duplex audio is not yet validated. No further live action is
authorized. A later separately approved direct-ALSA scheduling comparison completed five minutes
at native 44.1-kHz/26-channel/S32_LE/128/512 duplex geometry with the helper processes continuously
at RR/20, zero xruns, and zero captured continuity events. Together with the spent `-6` arm, this
supports retaining the System76 Scheduler exceptions for `aplay` and `arecord` as part of the
conservative host defaults; it does not prove PipeWire or audible-playback acceptance.

## Objective

Establish a repeatable performance baseline and ship measured, stable desktop-audio defaults that
avoid persistent or startup corruption under ordinary playback and duplex use without regressing
the proven fixed 48 kHz transport.

## Scope

- Measure settled and startup playback behavior through direct ALSA and PipeWire.
- Measure xruns, graph errors, IRQ cadence, CPU load, startup behavior, and end-to-end latency where
  a safe physical loopback can provide repeatable evidence.
- Evaluate UCM `dshare`/`dsnoop` buffer geometry and PipeWire/WirePlumber node behavior.
- Investigate shared-engine disruption when capture is discovered, opened, reconfigured, or closed
  while playback is active.
- Tune driver or desktop integration only when a measured bottleneck identifies the correct layer.
- Define conservative release defaults and separately documented low-latency experiments if useful.

## Out Of Scope

- Advertising or implementing 96/192 kHz support without a separate sample-rate-switching task.
- Mixer controls, MIDI, hot removal, or unrelated register exploration.
- Claiming sub-millisecond or professional real-time performance without repeatable measurement.
- Broad MMIO changes or speculative DMA rewrites.

## Relevant Context

- `notes/CURRENT_STATUS.md` owns current hardware and runtime evidence.
- `driver/snd-quantum2626.c` owns the fixed PCM constraints and shared audio-engine lifecycle.
- `alsa/ucm2/P2626/HiFi.conf` contains the second candidate: both shared directions
  retain 128-frame periods and request exactly four periods through alsa-lib's direct-plugin
  `periods` field. The installed UCM now matches these bytes; actual hardware geometry remains
  unknown until playback opens the PCM.
- `docs/agents/tasks/tci-mailbox-macos-trace-pivot.md` records the functional playback, capture, and
  duplex implementation completed by TASK-001.
- The validated installed module hash on 2026-08-15 is
  `890dcde7ee8825c15492ead1e94acdfaf32be43462d645a6b070327c79ea6578`.

## Constraints

- Preserve the known-working 48 kHz, 26-channel, S32_LE transport as the control case.
- Treat service restarts, module changes, playback, capture, and loopback as separately bounded live
  tests under `docs/agents/hardware-testing.md`.
- Keep output levels controlled and do not assume physical S/PDIF/ADAT routing is proven.
- Distinguish intervention-induced graph transients from defects reproduced during untouched use.
- Do not optimize for a synthetic latency number at the expense of reliable desktop playback.

## Plan

1. Capture an untouched settled baseline for direct ALSA and PipeWire playback: negotiated geometry,
   IRQ cadence, graph errors, kernel faults, CPU load, and audible result.
2. Capture startup and capture-open transitions separately, including WirePlumber probing and shared
   playback/capture engine reconfiguration.
3. Compare conservative UCM buffer candidates while retaining the 128-frame hardware period; start
   with 4, 8, and 16 periods and measure stability and latency rather than selecting by intuition.
4. Determine whether desktop policy can avoid unnecessary always-active capture/monitor graphs and
   repeated zero-IRQ probe starts without hiding any of the 26 independent inputs.
5. If artifacts survive clean desktop buffering, instrument the driver narrowly around period data,
   hardware position, and duplex transitions before changing the DMA implementation.
6. Run a repeatable physical loopback latency test when the user approves the cabling and level.
7. Select and document release defaults, repeat the full functional matrix, and remove unmeasured
   performance claims.

## Evidence And Discoveries

- **Observed Linux, 2026-08-15 untouched 256-frame checkpoint:** the checkout remained at
  `184677a979b825a539867b36da4b31b77a29ecce`, the installed UCM still matched the tracked
  `3fa8c219efc6754e886b9637b6cf0d8b60d7628265c75509aa39cbe6ab464b29` profile, and the loaded
  module still matched
  `890dcde7ee8825c15492ead1e94acdfaf32be43462d645a6b070327c79ea6578`. All 13 playback sinks and
  26 mono capture sources remained present. While ordinary Firefox playback and the GNOME Settings
  capture/monitor graph were active, both ALSA directions stayed RUNNING at 48 kHz, 26-channel
  S32_LE with 128-frame periods and 256-frame buffers. Main stayed at a 48 kHz/128-frame PipeWire
  graph and its cumulative error counter remained 16 across 24 samples; Firefox remained 14 and
  the active Line Input 5 node remained 30 after the first sample. The GNOME Settings client moved
  from 124 to 126 early in the observation and then settled, so client startup/monitor errors are
  retained separately from stable device-node counters. After `pw-top`'s initial zero row, Main's
  scheduling ratios stayed at W/Q 0.00--0.03 and B/Q 0.00--0.01; Line Input 5 stayed at W/Q
  0.00--0.06 and B/Q 0.00. The device delivered 1,125 interrupts in 3.004 seconds (approximately
  374.5 per second), and the recent kernel journal contained no Quantum xrun, timeout, DMA, or fault
  marker. The configured Main soft volume was observed at 100%, a user-state change from the earlier
  31% snapshot that TASK-002 did not make. No new user-audible verdict was solicited during this
  read-only checkpoint; the prior post-intervention result remains the audible 256-frame evidence.
- **Offline validation, 2026-08-15 512-frame candidate:** an exact candidate derived from the
  tracked profile changes only the two playback/capture `buffer_size` values from 256 to 512 while
  preserving both `period_size 128` values. Its SHA-256 is
  `db4d09cbb70b8eefd40b45286a1c5b0a7d83171099b5abc0bcad143080c23192`. A staged install retained
  the other two tracked UCM files byte-for-byte, and isolated ALSA UCM parsing enumerated all 13
  playback PCMs and 26 capture PCMs. This is offline evidence only.
- **Observed Linux, 2026-08-15 invalid 512-frame UCM-only trial:** after the user installed the exact
  `db4d09cb...3192` candidate, read-back matched it byte-for-byte and only PipeWire, PipeWire Pulse,
  and WirePlumber were restarted. All 13 sinks and 26 sources returned, Main remained the default,
  and browser streams reconnected. The candidate did not activate the requested geometry:
  PipeWire reported `api.alsa.period-num = 2`, `/proc/asound` reported the playback hardware at
  128/256 frames, and every kernel prepare logged `buffer_frames=256`. A fresh playback IPC segment
  was created after restart, excluding retained pre-restart shared memory as the cause. The live
  result is therefore a no-op candidate, not 512-frame performance evidence; capture/duplex and an
  audible A/B verdict were intentionally not collected against unchanged geometry. In a short
  settled safety sample, Main remained at 48 kHz/128 frames with its error counter fixed at 15,
  W/Q 0.00--0.05, and B/Q 0.00--0.01 after the sampler's initial inactive row. The device delivered
  3,753 interrupts in 10.009 seconds (approximately 375 per second), with 13/26 endpoints still
  present and no persistent corruption observed. The user then reported that the settled audio was
  "sounding really good." Because every live read-back still showed 128/256 frames, this audible
  result supports the clean post-restart 256-frame runtime state, not the ineffective 512-byte-file
  candidate. After this invalid trial, the installed file was restored to the preserved tracked
  256-frame bytes and read back with the original `3fa8c219...64b29` hash. The user-audio services
  had not yet been restarted again, so post-restart rollback proof remained pending.
- **Observed Linux and user-observed hardware, 2026-08-15 settled transient:** after initially
  reporting that playback was "sounding really good," the user heard it go weird for about a
  second and then return to sounding great without any intervention at that moment. The immediate
  snapshot still showed RUNNING 48 kHz, 26-channel S32_LE, 128/256-frame hardware. Main and Firefox
  had both advanced from 15 to 20 cumulative PipeWire errors. The nearest relevant user-audio log
  in the bounded five-minute window was one PipeWire `out of buffers on port 0 2` entry at 23:17;
  no matching Quantum kernel xrun, timeout, DMA, or fault marker appeared. Because the exact event
  time was not instrumented, the log entry and audible artifact are correlated window evidence,
  not proven one-to-one causation. Main and Firefox then held at 20 errors across the next 12
  samples while the user reported recovered audio. This is evidence of a brief, self-resolving
  settled desktop-graph transient at the actual 256-frame runtime, not persistent corruption and
  not a 512-frame result.
- **Observed Linux and user-observed hardware, 2026-08-15 rollback restart:** immediately before
  restart, tracked, installed, and preserved rollback UCM files all matched the original
  `3fa8c219...64b29` hash; module, PCI, HEAD, and dirty-tree anchors were unchanged. Restarting only
  PipeWire, PipeWire Pulse, and WirePlumber returned all 13 sinks and 26 sources immediately. Main
  reopened RUNNING at 48 kHz, 26-channel S32_LE and 128/256 frames, and the user initially reported
  that it sounded "even better." Main showed zero cumulative errors across the next 24 samples,
  W/Q 0.00--0.03, and B/Q 0.00--0.01; 8,253 IRQs arrived in 22.007 seconds, approximately 375 per
  second. That clean sample was then invalidated as terminal settled acceptance by two PipeWire
  `out of buffers` entries at 23:26:07 and 23:26:16 followed by three dshare `snd_pcm_mmap_commit`
  `Broken pipe` entries at 23:26:24. An immediate snapshot showed Main at seven cumulative errors
  and Brave at six while hardware playback remained RUNNING at 128/256; no matching Quantum kernel
  xrun, timeout, DMA, or fault marker appeared. The user then confirmed "lots of pops and glitches"
  plus a brief warbling interval. Capture/duplex was not reopened after these faults. Rollback byte
  and runtime agreement is proven, but stable 256-frame desktop playback acceptance failed both
  objectively and audibly: repeated PipeWire buffer starvation is now a confirmed live hard stop.
- **Observed Linux and source inspection, 2026-08-15 read-only scheduling diagnosis:** the bounded
  journal shows RTKit granting the new PipeWire, PipeWire Pulse, and WirePlumber data-loop threads
  realtime priority 20 at 23:24:50. The first new PipeWire `out of buffers` entry followed at
  23:26:07, with another at 23:26:16 and dshare `Broken pipe` entries beginning at 23:26:24. The
  same live data-loop thread IDs now report `SCHED_OTHER` with realtime priority zero; their service
  limits are `LimitRTPRIO=0` and `LimitRTTIME=infinity`, so PipeWire depends on its documented
  RTKit fallback for realtime scheduling. The active System76 Scheduler has no `/etc` override and
  uses the distribution profile's 60-second process refresh. Inspection of exact installed-package
  source commit `8651bbf` shows that an omitted `sched=` property defaults each profile to
  `SCHED_OTHER`, every refresh reapplies each selected profile to every task/thread, and the active
  `sound-server` rule for `/usr/bin/pipewire` and `/usr/bin/pipewire-pulse` omits `sched=`. Thus the
  active scheduler code path requests `SCHED_OTHER` for the very data-loop threads that RTKit first
  promotes. The Main node remained the 48 kHz, 128-frame graph driver over ALSA period count 2, and
  browser streams requested much larger 900/1024-frame client latencies; nothing in this read-only
  pass changed UCM, services, the module, or hardware state.
- **High-confidence inference, 2026-08-15:** System76 Scheduler's periodic profile application is
  the mechanism that removes the PipeWire data-loop realtime class after service startup and is a
  likely contributor to the later starvation/broken-pipe bursts. Source, configuration, initial
  RTKit grants, and current thread state establish the conflict, but no scheduling-class sample was
  captured at the exact demotion or first audible fault. Treat one-to-one causation as unproven
  until a separately authorized checkpoint samples the class across the 60-second boundary.
- **Observed Linux and user-observed hardware, 2026-08-15 recovered state:** without another
  intervention, the user subsequently reported that playback sounded excellent. An immediate
  eight-sample read-only `pw-top` window kept Main RUNNING at 48 kHz/128 frames with its cumulative
  error counter fixed at 27, W/Q 0.00--0.03, and B/Q 0.00--0.01; Brave also stayed fixed at 27
  errors while requesting 1024 frames. The preceding two-minute journal contained one additional
  `out of buffers` entry at 23:35:44 and no dshare broken pipe. This proves the fault remains
  bursty and self-recovering: non-realtime scheduling is a material risk/conflict but is not alone
  sufficient to make every playback interval audibly bad.
- **Observed Linux, 2026-08-15 failed scheduler-isolation checkpoint:** an additive System76
  Scheduler exception for `/usr/bin/pipewire`, `/usr/bin/pipewire-pulse`, and
  `/usr/bin/wireplumber` was staged as exact candidate SHA-256
  `46eb1724e07207bd77205745225641406ac7a73aa44b40fec395fa1934fe6e85`. The pre-test `/etc`
  scheduler override directory was absent; the user installed only this file and read-back matched
  the candidate. After scheduler reload and the authorized restart of only PipeWire, PipeWire
  Pulse, and WirePlumber at 23:43:03, all three data loops were `SCHED_RR` priority 20 rather than
  the previously observed `SCHED_OTHER`. The exclusion also returned the three process main
  threads to nice 0, proving the staged comment that service policy would retain the prior
  System76-applied niceness was incorrect. However, `wpctl status` and the bounded PipeWire
  registry query did not return, no Quantum endpoints could be confirmed, ALSA device 0 was
  closed, and WirePlumber reported one pending linkable not activated after 20 seconds. This
  crossed the missing-endpoint hard stop before the planned two-refresh timing sample or audible
  test; do not reuse this candidate unchanged.
- **Observed Linux, 2026-08-15 failed rollback:** the user moved the exact installed scheduler file
  to the task-owned `.failed-live` path, whose hash still matches `46eb1724...6e85`, and removed the
  now-empty `/etc/system76-scheduler` hierarchy, restoring its prior absence. Scheduler reload and a
  rollback restart of only the same three user services completed at 23:47:40, but the bounded
  PipeWire registry query still returned no inventory and WirePlumber again reported one pending
  linkable after 20 seconds. The PCI function remains `1c67:0104`, bound to `snd_quantum2626`; ALSA
  card `P2626` remains present on IRQ 214; and the installed module still hashes to
  `890dcde7...6578`. Thus protected driver/device identity and exact scheduler configuration
  rollback are intact, but desktop endpoint/runtime recovery failed. No further restart, UCM,
  module, or hardware action is authorized from this blocked state.
- **Observed Linux, 2026-08-15 post-failure localization:** PipeWire, PipeWire Pulse, and
  WirePlumber remain running without service restarts or CPU spin, but Pulse clients block and the
  user reported that YouTube would not load video. The PipeWire core can enumerate the five ALSA
  card devices, including `alsa_card.pci-0000_09_00.0`, but exposes only the dummy audio sink and
  no ALSA audio nodes. On termination of the first failed instance, WirePlumber identified the
  indefinitely pending object as `WpSiAudioAdapter`; the rollback instance reproduced the same
  20-second activation timeout. WirePlumber holds two `controlC4` descriptors while no process
  holds a Quantum playback or capture PCM. Quantum UCM parsing still enumerates 13 playback and 26
  capture PCMs, direct ALSA control queries complete, and no task-owned dshare/dsnoop System V IPC
  key remains. The two restart probes reached the driver and completed bounded playback, duplex,
  and capture prepare/start/stop transitions; every stop completed, and the kernel journal has no
  Quantum xrun, DMA timeout, fault, warning, or oops. The original scheduler classes and niceness
  were reapplied after rollback. This localizes the current crash to PipeWire/WirePlumber ALSA-node
  adapter activation rather than an active PCM transport or kernel-module crash. An interaction
  with the Quantum UCM/driver topology is still possible and is not exonerated without a clean
  recovery plus narrower startup tracing.
- **Observed Linux, 2026-08-16 post-reboot recovery:** a user-initiated full host reboot restored a
  responsive PipeWire registry without another partial service restart. PipeWire, PipeWire Pulse,
  and WirePlumber are active with zero service restarts; all 13 Quantum playback sinks and 26 mono
  capture sources are present, with Main and Input 5 restored as defaults. PCI `1c67:0104` is bound
  to `snd_quantum2626`; tracked and installed UCM files still match `3fa8c219...64b29`; the
  installed module still matches `890dcde7...6578`; and the scheduler override hierarchy remains
  absent. After the first 60-second scheduler refresh, the three audio data loops are again
  `SCHED_OTHER` with the original System76 niceness, confirming exact runtime-policy rollback. Both
  Quantum PCM directions were closed at the checkpoint, and current-boot user-audio logs contain
  no pending-linkable, activation, out-of-buffers, broken-pipe, or xrun marker.
- **Observed Linux, 2026-08-16 fresh-boot probe amplification:** during initial desktop discovery,
  the driver logged 82 playback-only, 160 capture-only, and two duplex prepares, plus 240
  start/resume operations. Of the corresponding stops, 234 completed with zero IRQs and six short
  runs completed with three to seven IRQs. Every prepare retained 256-frame buffers and 128-frame
  blocks, and no Quantum timeout, xrun, DMA fault, warning, BUG, or oops appeared. The graph still
  converged successfully and left both PCMs closed. This proves the current 13/26 UCM topology
  amplifies desktop startup into hundreds of shared-engine probe transitions. It is a concrete
  startup-risk seam and plausible contributor to the earlier nondeterministic adapter wedge, but
  that causal link remains inferred rather than proven.
- **Observed Linux and user-observed hardware, 2026-08-16 untouched post-reboot playback:** after
  the user started YouTube Music in the PWA, they reported many audible pops. Playback was RUNNING
  at the protected 48 kHz, 26-channel, S32_LE, 128/256-frame ALSA geometry while capture remained
  closed. The hardware delivered 1,129 interrupts in approximately three seconds, consistent with
  the expected 375 per second, and the kernel log contained no matching Quantum timeout, xrun, DMA
  fault, warning, BUG, or oops. At the same time the PipeWire graph ran at 44.1 kHz with a 64-frame
  quantum while the Main adapter remained at 48 kHz; Main's cumulative error counter advanced
  during both bounded samples and the Firefox stream also accumulated errors. The user journal
  contained 40 dshare `snd_pcm_mmap_commit` `Broken pipe` entries in the bounded playback window.
  This reproduces the release-blocking desktop fault after a clean reboot without a candidate,
  restart, capture open, or module change. It localizes the observed failure above the continuing
  hardware IRQ/PCM transport, but does not by itself prove whether scheduling, the two-period
  buffer, resampling, or their interaction is the root cause.
- **Observed Linux and user-observed hardware, 2026-08-16 continuing fault burst:** the user later
  described the recurring pops as sounding like vinyl. During that report, Main was still RUNNING
  at a 44.1 kHz/64-frame graph around its 48 kHz adapter and had accumulated 97 errors; Firefox had
  accumulated two. The counters stayed fixed across an eight-sample window, while the preceding
  three minutes contained three new pairs of dshare `snd_pcm_mmap_commit` `Broken pipe` errors at
  00:13:58, 00:14:19, and 00:14:41. ALSA remained at 48 kHz, 26-channel S32_LE and 128/256 frames,
  capture remained closed, and IRQ 213 advanced by exactly 1,125 in approximately three seconds.
  No matching kernel marker appeared. The fault is therefore bursty but repeatedly self-recurring
  during ordinary playback; a quiet short counter sample does not establish settled acceptance.
- **Static standards comparison, 2026-08-16:** the Linux ALSA driver contract and the upstream RME
  HDSPM and FireWire AMDTP implementations use the same basic transport shape as the Quantum
  driver: one raw multichannel PCM, hardware-pointer reporting, period-boundary
  `snd_pcm_period_elapsed()` notification, and explicit shared-direction coordination. AMDTP adds
  explicit `SNDRV_PCM_POS_XRUN`/`snd_pcm_stop_xrun()` reporting when its transport itself detects a
  stream failure; the current Quantum evidence contains no corresponding hardware failure that
  would justify adding a speculative fault detector or DMA rewrite. The current fixed 48 kHz,
  26-channel, S32_LE constraints, 128-frame period, integer-period buffer, hardware pointer, and
  IRQ notification follow the documented ALSA model. Driver-side sync-group semantics remain a
  possible later cleanup, not an evidenced cause of the current playback broken pipes.
- **Static desktop-audio comparison, 2026-08-16:** upstream ALSA UCM already provides the
  `SplitPCM`/`SplitPCMDevice` pattern used by MOTU, GoXLR, Flow8, Steinberg, and other multichannel
  devices. It exposes one raw hardware PCM to a capable session manager and describes virtual
  channel slices, falling back to `dshare`/`dsnoop` for older consumers. The Quantum profile
  currently reimplements only that fallback as 13 direct dshare sinks and 26 direct dsnoop
  sources. WirePlumber 0.5.8 added native `SplitPCM` loopback handling, but this host has
  WirePlumber 0.4.17. Its installed ALSA UCM and alsa-lib are 1.2.8, whose split macro stops at
  hardware channel 23; upstream expanded it to 32 hardware channels in 1.2.13 and requires newer
  Syntax 7 support. The distribution repositories currently offer no newer candidate. Therefore
  replacing the Quantum profile with upstream `SplitPCM` on the current host would omit channels
  24-25 and would still use the legacy direct-plugin fallback; it is not a safe immediate edit.
- **Static PipeWire comparison, 2026-08-16:** PipeWire documents the non-batch ALSA hardware buffer
  as `api.alsa.period-size * api.alsa.period-num`. The active Quantum node advertised 128 frames and
  two periods, exactly matching the observed 256-frame hardware buffer and explaining why the
  UCM-only 512 candidate was ineffective. The host's packaged PipeWire configuration explicitly
  allows rates from 44.1 through 384 kHz, and PipeWire documents that allowed graph rates may switch
  while devices are idle; a fixed 48 kHz ALSA node is then resampled when the graph selects 44.1
  kHz. This is standard behavior, not proof that resampling caused the pops. A valid current-stack
  512 checkpoint must align both UCM `buffer_size = 512` and a Quantum-only
  `api.alsa.period-num = 4` session-manager rule while retaining the 128-frame period. That new
  persistent rule is outside the already consumed UCM-only trial and requires an exact reversible
  checkpoint before installation.
- **Observed Linux, 2026-08-16 failed paired 512-frame checkpoint:** the exact preserved rollback
  UCM was copied before installation and hashes to `3fa8c219...64b29`. The staged 512 profile
  retained the prior sealed `db4d09cb...3192` hash, changed only both buffer sizes, and parsed
  offline as all 13 playback plus 26 capture endpoints. A new Quantum-only WirePlumber 0.4 rule,
  hash `dd3fd0ed...94840`, requested `api.alsa.period-size = 128` and
  `api.alsa.period-num = 4` for both `quantum2626_stereo_out:*` and
  `quantum2626_mono_in:*` paths. The installed files read back byte-for-byte and only PipeWire,
  PipeWire Pulse, and WirePlumber were restarted at 00:23:30. The registry initially returned all
  13/26 endpoints and Firefox reconnected, but the rule did not activate: Main still reported
  `api.alsa.period-num = 2` and ALSA/driver read-back remained 128/256 frames. The session then
  emitted a dense series of dshare `snd_pcm_mmap_commit` `Broken pipe` errors from 00:23:36 through
  00:23:46, later another broken pipe and an `out of buffers` event. This is another invalid
  512-frame trial with no performance or audible evidence about 512 frames.
- **Observed Linux and user-observed host, 2026-08-16 failed rollback:** rollback restored the exact
  installed/tracked `3fa8c219...64b29` UCM and removed only the new WirePlumber rule, restoring its
  prior absence. After restarting only the same three user services at 00:24:52, all services
  reported active/running with zero systemd restarts, but `wpctl status` timed out after 20 seconds
  and WirePlumber reported `1 pending linkable(s) not activated in 20sec`. ALSA card `P2626` remains
  present and closed on IRQ 213, PCI `1c67:0104` remains bound to `snd_quantum2626`, and built plus
  installed module hashes still match `890dcde7...6578`; no kernel timeout, xrun, DMA fault, BUG,
  or oops appeared. The user confirmed that the checkpoint had crashed the desktop audio path.
  Configuration rollback is exact but runtime rollback verification failed, triggering the hard
  stop. The sealed artifacts remain under `/tmp/quantum2626-task002-512.66BPQi` for inspection;
  do not reuse the rule unchanged.
- **Observed Linux and user-observed host, 2026-08-16 non-reboot recovery:** with exact protected
  configuration already restored, read-only localization showed the PipeWire core could enumerate
  the Quantum ALSA card but exposed only a dummy audio sink; WirePlumber held `controlC0`, no
  process held either Quantum PCM, no Quantum dshare/dsnoop shared-memory segment remained, and
  PipeWire plus PipeWire Pulse were alive in normal poll waits. A WirePlumber-only stop/start first
  reproduced the pending-adapter stall. Bounded foreground debug then showed the Firefox audio
  adapter activating while a second adapter remained pending; because that debug process had a
  25-second timeout, endpoints briefly worked and then disappeared when it exited, matching the
  user's observation. The persistent WirePlumber service was then started without restarting
  PipeWire, Pulse, applications, the module, or the host. `wpctl` immediately returned all 13
  Quantum playback and 26 capture endpoints with Main and Input 5 defaults. A following 25-second
  WirePlumber journal window contained no pending-linkable message, and a final registry query
  retained the complete 13/26 inventory. The non-reboot desktop recovery succeeded. Playback was
  closed by the user, so no post-recovery audible or settled-error result is claimed.
- **Static driver review plus observed correlation, 2026-08-16:** the current driver has a real
  transition-path performance deficiency. `hw_params` and `hw_free` stop, rebuild, reprogram, and
  resume the complete joint playback/capture DMA engine when the other direction changes while one
  direction is running. The final ALSA trigger stop also calls `quantum_audio_stop()`, which masks
  the IRQ, polls hardware with up to 100 ten-microsecond busy waits, and logs the stop from the
  atomic trigger path. Those operations are bounded, but they are much heavier than ALSA's expected
  minimal trigger and become material when the legacy 39-node topology produces hundreds of probe
  transitions. They plausibly contribute to startup, discovery, and capture-open glitches and
  should be refined before release. They do not explain the measured settled vinyl-like crackle:
  the exact 00:13:30--00:15:10 user-audible window contained repeated PipeWire dshare broken pipes
  but no driver DMA prepare/start/stop/reconfiguration event, while the already recorded hardware
  cadence remained 375 IRQs per second. A steady-state IRQ/pointer defect is still possible but is
  not supported by current evidence; proving one requires longer direct-ALSA isolation and narrow
  position-delta instrumentation, not a speculative DMA rewrite.
- **Read-only decision checkpoint and offline validation, 2026-08-16:** branch `js/dev`, HEAD
  `184677a979b825a539867b36da4b31b77a29ecce`, the clean index, and all inherited dirty paths were
  unchanged before implementation. PCI `1c67:0104` remained bound to `snd-quantum2626`; ALSA card
  `P2626` was present on IRQ 213; built and installed modules still matched
  `890dcde7...6578`; loaded `srcversion` remained `6CDB07D137537DE2CEB3797`; and tracked plus
  installed UCM still matched `3fa8c219...64b29`. A read-only registry query returned all 13
  Quantum sinks and 26 sources with Main and Line Input 5 as defaults and Firefox actively routed
  to Main. The failed four-period rule matched `api.alsa.path`, but its preserved debug log carries
  the UCM identity in `node.name`. The replacement rule's two globs matched all 13 playback and 26
  capture node names from that log, with no unmatched Quantum node. The selected tracked UCM now
  has SHA-256 `db4d09cbb70b8eefd40b45286a1c5b0a7d83171099b5abc0bcad143080c23192`; the new
  WirePlumber 0.4 rule has SHA-256
  `8fa704fa556eaf83941fb0862dc0d04b32fa2a002035f98af3b1905ec8d3bd6d`. This proves a coherent,
  correctly targeted offline candidate, not that four periods activate live or stop the crackle.
- **Consumed install-gate failure, 2026-08-16:** gate `TASK-002-INSTALL-512-V1` passed its sealed
  preflight and invoked exactly once
  `/usr/bin/sudo /usr/bin/bash /tmp/quantum2626-task002-install.Y6hd58/install-exact-candidate.sh`.
  `sudo` exited 1 before controller execution because the host execution channel had no interactive
  terminal or askpass path. The controller retains SHA-256 `63d73cbe...4954`, but the gate authority
  is consumed and the invocation must never be retried. Bounded read-back reconfirmed the installed
  UCM at rollback hash `3fa8c219...6429`, mode 0644, and the candidate WirePlumber rule absent. No
  service, runtime, module, device, repository, cleanup, or rollback action occurred. A future gate
  must use a fresh sealed controller and have the user invoke its exact command in an interactive
  host terminal; this is the only available mechanism that supplies `sudo` a TTY without exposing
  authentication material to the objective controller.
- **Completed install gate, 2026-08-16:** gate `TASK-002-INSTALL-512-V2` sealed a fresh controller
  at `/tmp/quantum2626-task002-install-512-v2/install-exact-candidate.sh` with SHA-256
  `63d73cbee07b1b8a4afd1bf4d340c93c9554506a973e0c61e0a1dfc090d14954`. Repository, source,
  installed-control, and clean-index preflight passed. A non-interactive sudo credential probe
  failed before invocation and did not consume the gate; the exact approved command was then
  invoked once in GNOME Terminal so authentication remained on the host. It exited 0. Read-back
  proves the installed UCM SHA-256 is
  `db4d09cbb70b8eefd40b45286a1c5b0a7d83171099b5abc0bcad143080c23192` and the installed
  WirePlumber rule SHA-256 is
  `8fa704fa556eaf83941fb0862dc0d04b32fa2a002035f98af3b1905ec8d3bd6d`; both are mode 0644.
  Attempt count is one and authority is consumed. No restart, reboot, playback, capture,
  module/device action, runtime read-back, cleanup, or rollback occurred.
- **Completed activation gate, 2026-08-16:** gate `TASK-002-ACTIVATE-512-V1` revalidated the exact
  installed candidate hashes and modes, PCI/ALSA identity, three active user audio services, clean
  index, and the existing 13/26 endpoint inventory. It invoked exactly once
  `/usr/bin/systemctl --user restart pipewire.service pipewire-pulse.service wireplumber.service`
  and exited 0. All three services returned active, exact PipeWire node counting returned 13 Quantum
  sinks and 26 Quantum sources, and Main's activated properties advertise
  `api.alsa.period-size = 128` plus `api.alsa.period-num = 4`. Both hardware PCM directions were
  closed, so this proves policy activation and endpoint recovery but not ALSA 128/512 geometry,
  playback stability, or audible improvement. No playback, capture, module/device action, reboot,
  cleanup, or rollback occurred. Attempt count is one and authority is consumed.
- **Observed Linux and user-observed hardware, 2026-08-16 failed playback verification:** after the
  user started playback, they reported it was "a bit better" but still had the odd crackle. Immediate
  ALSA read-back showed RUNNING 48 kHz, 26-channel S32_LE playback with a 128-frame period and
  256-frame buffer; capture remained closed. This crosses the unexpected-geometry hard stop: the
  corrected rule advertises four periods at the PipeWire node but did not produce a 512-frame
  hardware buffer. The audible result therefore belongs to another post-restart 256-frame runtime,
  not to 512 frames. No further error sampling, restart, repair, rollback, capture, module/device
  action, or runtime mutation followed the hard stop.
- **Static source diagnosis and offline repair candidate, 2026-08-16:** the loaded driver is not the
  period-count limiter: `quantum_pcm_hw` permits 2 through 64 periods at the fixed 128-frame period.
  The active playback dshare IPC segment used key `0x405b0` (configured key plus UID), was created
  after the service restart, and remained attached, excluding retained pre-restart IPC geometry.
  While playback ran, Main and ALSA both resolved back to period count 2 and 128/256 hardware.
  Exact installed alsa-lib 1.2.8 source documents `periods` as the direct-plugin field used when
  neither buffer size nor buffer time is specified. Its initialization code handles `buffer_size`
  with `snd_pcm_hw_params_set_buffer_size_near()` before fixing period size, whereas the `periods`
  path fixes period size first and then calls `snd_pcm_hw_params_set_periods_near()`. The repository
  candidate therefore replaces both UCM `buffer_size 512` entries with `periods 4` and retains the
  WirePlumber `api.alsa.period-num = 4` rule. The new UCM hash is
  `8a837fcc14c4cc23ada9fc9df2f14da87b94cd4ddaf5296cd89e74b021da4bed`; the installed UCM remains
  the failed `db4d09cb...3192` bytes. This is a source-grounded offline candidate, not live proof.
- **Completed periods-based install and activation gates, 2026-08-16:** gate
  `TASK-002-INSTALL-PERIODS4-V1` sealed controller SHA-256
  `b0359a8c55e27097c6e482752c2c46364ce815109a25afd814ba424a0ad08ae4`, passed source/control/hash
  preflight, and invoked its exact UCM-only install once in an interactive host terminal. It exited
  0; read-back proved installed UCM SHA-256
  `8a837fcc14c4cc23ada9fc9df2f14da87b94cd4ddaf5296cd89e74b021da4bed` at mode 0644 and retained
  WirePlumber SHA-256 `8fa704fa...d6d` at mode 0644. After objective classification, gate
  `TASK-002-ACTIVATE-PERIODS4-V1` revalidated installed bytes, device identity, active services,
  13/26 endpoints, and pre-restart 128/256 control geometry, then invoked exactly once
  `/usr/bin/systemctl --user restart pipewire.service pipewire-pulse.service wireplumber.service`.
  It exited 0; all services and 13/26 endpoints returned. Playback stayed closed for the bounded
  30-second read-back, so no hardware-geometry or audible claim is available. Each gate consumed
  one attempt. No retry, playback/capture opening, module/device action, repair, cleanup, rollback,
  or additional runtime mutation occurred.
- **Observed Linux and user-observed hardware, 2026-08-16 failed periods-based playback
  verification:** after the user started playback, they reported that it seemed good. Direct
  read-back nevertheless showed Main at `api.alsa.period-size = 128` and
  `api.alsa.period-num = 2`; ALSA playback was RUNNING at 48 kHz, 26-channel S32_LE with a 128-frame
  period and 256-frame buffer, while capture remained closed. Thus replacing `buffer_size 512` with
  `periods 4` did not change live geometry. The audible observation is another clean interval at
  128/256, not 512-frame acceptance. No further diagnostics or runtime mutation followed the
  unexpected-geometry hard stop.
- **Static PipeWire negotiation diagnosis, 2026-08-16:** exact source for the installed PipeWire
  `1.0.2~1707732619~22.04~b8b871b` build parses `api.alsa.period-num` into
  `default_period_num`, passes that requested count to `snd_pcm_hw_params_set_periods_near()`, and
  calculates `buffer_frames` from the count ALSA returns. Its node-info path then publishes
  `buffer_frames / period_frames` as the active `api.alsa.period-num`. The pre-open value `4` and
  post-open value `2` therefore show that the rule reached PipeWire but ALSA's direct-plugin/slave
  constraints negotiated the request down to two periods. PipeWire does not hard-force two. No
  runtime mutation occurred; the current good-sounding 128/256 session was preserved.
- **Read-only user-setting exclusion, 2026-08-16:** the user's PipeWire and WirePlumber
  configuration directories contain no files, no user ALSA configuration or user-systemd override
  sets period geometry, and system ALSA keeps `defaults.pcm.dmix.max_periods` at automatic (`0`).
  Live PipeWire settings report `clock.force-quantum = 0` and `clock.force-rate = 0` with no
  period-count metadata override. The installed Quantum-only rule remains the sole explicit count
  and requests `4`, so a conventional user setting does not explain the negotiated `2`.
- **Direct-plugin boundary localization, 2026-08-16:** isolated `_alibcfg` read-back proves the UCM
  loader expands both direct-plugin slaves with `period_size 128` and `periods 4`. A read-only
  attachment to the active playback dshare System V segment independently showed its saved hardware
  interval and copied slave state both fixed at 128-frame periods, two periods, and a 256-frame
  buffer. This moves the failure boundary into dshare's first-instance hardware-slave initialization;
  no PipeWire client request can expand beyond the already-created 256-frame slave. No new PCM was
  opened and the running session was not changed.
- **Prepared but not invoked constraint probe, 2026-08-16:** a temporary helper at
  `/tmp/quantum2626-task002-hw-constraint-v1/probe-hw-constraint` has SHA-256
  `b8e6c1b85c9cbb11730f041a55dc27e7b2c3a7d908f9058ae543a05cb7a6a30f` and source SHA-256
  `3bbb75159afa523eac153b4c363ee3cda33dff181ba5ea7de4e0a26f8d7e7a71`. It opens playback
  `hw:P2626,0` nonblocking, refines but does not apply exact 48 kHz/26-channel/S32_LE/128-by-4
  constraints, prints the resulting buffer size, and closes without prepare or start. Invocation is
  a separately authorized playback-open boundary and must wait until the existing PCM is closed.
- **Constraint-probe preflight stopped unconsumed, 2026-08-16:** after explicit user approval, the
  sealed source and binary hashes matched, but `/proc/asound/P2626/pcm0p/sub0/hw_params` remained
  open at 128/256 throughout a 15-second suspend wait. The helper was not invoked, attempt count
  remains zero, and the approval remains unconsumed. Require a closed PCM before using it.
- **`TASK-002-HW-CONSTRAINT-V1` consumed failed, 2026-08-16:** after the user reported readiness,
  immediate preflight matched both sealed hashes and found playback closed. The exact helper was
  then invoked once and exited 1 before PCM open: `snd_pcm_open()` reported that ALSA could not get
  the card index for `P2626` and returned `No such device`. Bounded read-back showed `/dev/snd`
  unavailable in the sandboxed execution context while host-visible `/proc/asound/cards` still
  listed `P2626` as card 0, PCI `09:00.0` remained bound to `snd-quantum2626`, and playback remained
  closed. Attempt count is one and authority is consumed; no parameter apply, prepare, DMA start,
  retry, repair, or runtime mutation occurred. A host-level invocation requires a fresh approval.
- **`TASK-002-HW-CONSTRAINT-HOST-V1` consumed with failed verification, 2026-08-16:** fresh user
  approval authorized one host-level invocation. Preflight matched the sealed hashes, found playback
  closed, and confirmed host `/dev/snd/controlC0` visibility. The exact helper reached `hw:P2626,0`
  but exited 1 with `constraint: Invalid argument` while refining the fixed geometry plus exactly
  four periods. Read-back found playback closed and no new Quantum prepare, DMA, xrun, timeout, or
  fault event. No parameters were applied and DMA was not started. The coarse v1 error label cannot
  separate `set_periods(4)` from the following single-value buffer query, so do not overstate which
  call failed and do not retry this consumed gate.
- **Prepared but uninvoked range probe, 2026-08-16:** corrected helper v2 at
  `/tmp/quantum2626-task002-hw-constraint-v2/probe-hw-constraint` has source SHA-256
  `b34bebd517ad097fe02b4a62ddca291cdc202b6c73792f2b84c9e853e003a9b2` and binary SHA-256
  `9a81a6ea4eb68ccb2adda85a4f5d67bfe123ebb4aebb4e76d80c3709fbc727df`. It labels each
  constraint call, prints allowed period and buffer ranges after the fixed base geometry, tests
  exact four-period support, and uses min/max buffer queries. It still does not apply hw_params,
  prepare, or start DMA. Any host invocation is another separately approved playback-open gate.
- **Observed Linux, 2026-08-15:** the active Main sink reports an S32_LE 48 kHz endpoint with a
  128-frame period and 256-frame ALSA buffer. In settled playback, PipeWire ran Main at 48 kHz and
  128 frames with zero graph errors across 24 samples.
- **Observed Linux, 2026-08-15:** the hardware IRQ increased by 1,127 over approximately three
  seconds, consistent with the expected 375 interrupts per second.
- **Observed Linux and user-observed hardware, 2026-08-15:** forced live PipeWire rate/quantum
  renegotiation sounded bad. A subsequent user-audio service restart produced an initial audible
  artifact that resolved by itself. Because both occurred during intervention, neither yet proves an
  untouched steady-state driver defect.
- **Observed Linux, 2026-08-15:** WirePlumber/GNOME Settings can keep Main playback and Line Input 5
  capture graphs active simultaneously. Kernel logs show capture discovery causing many zero-IRQ
  starts/stops and later a bounded duplex reconfiguration while playback remains active.
- **Observed Linux, 2026-08-15:** `/proc/asound` reports the hardware PCM at 48 kHz, 26-channel
  S32_LE, 128/256 frames. Through the shared ALSA plugin it also reports `appl_ptr = 0` with a large
  negative delay while audible playback continues, so raw kernel PCM delay fields are not a valid
  end-to-end latency measurement for this UCM path.

## Decisions

- **2026-08-15:** do not publish a low-latency or release-performance claim from the functional
  bring-up evidence. Establish repeatable measurements first.
- **2026-08-15:** evaluate a conservative desktop buffer separately from any optional low-latency
  profile; the two-period buffer is a testable suspect, not yet a confirmed root cause.
- **2026-08-15:** changing only UCM `dshare`/`dsnoop` `buffer_size` did not change PipeWire or
  hardware geometry. Do not count that trial as a 512-frame result or proceed to 1024. Restore the
  tracked 256-frame file, then identify and validate the actual desktop period-count control seam
  before repeating 512.
- **2026-08-15:** do not interpret the recurrent 256-frame failures as buffer-size evidence while
  the active desktop scheduler is periodically replacing PipeWire's RTKit-granted realtime policy
  with `SCHED_OTHER`. Isolate and measure that control-plane conflict before resuming the buffer
  matrix.
- **2026-08-16:** do not change the kernel transport in response to the current PipeWire broken
  pipes. Its observable IRQ cadence and PCM geometry remain healthy and its PCM contract matches
  established multichannel drivers at the level relevant to this fault.
- **2026-08-16:** use upstream `SplitPCM` rather than extending the hand-built endpoint topology,
  but only after a compatible WirePlumber and ALSA UCM/alsa-lib stack is available for all 26
  channels. Treat any system audio-stack migration as a separate, preflighted boundary.
- **2026-08-16:** if the buffer matrix continues on the current stack, the next 512-frame test must
  pair the exact UCM candidate with a Quantum-only PipeWire/WirePlumber period-count rule. Do not
  make another UCM-only claim and do not change global rate/quantum metadata during that test.
- **2026-08-16:** the paired current-stack rule did not apply and its restart/rollback reproduced
  the WirePlumber pending-linkable wedge. Classify this checkpoint as failed verification, not as a
  512-frame result. Do not retry that unchanged `api.alsa.path` rule or another partial service
  restart from the wedged state; recover first and require a newly justified target before any
  later candidate.
- **2026-08-16:** a full reboot was not ultimately required for this occurrence. Starting the
  persistent WirePlumber service against the already-running PipeWire core restored the registry
  after bounded diagnostics. Do not treat the nondeterministic recovery as proof that repeated
  service restarts are safe or that the underlying direct-node activation race is fixed.
- **2026-08-16:** treat transition-path driver debt and settled PipeWire underruns as separate
  seams. Refine whole-engine rebuild and atomic stop behavior for startup/duplex robustness, but do
  not claim those paths caused a crackle interval in which they did not execute.
- **2026-08-16:** select the corrected four-period integration for the immediate PR-sized candidate.
  Reject the transition-only driver edit as the settled-crackle fix. Defer the System76 Scheduler
  integration because its exclusion retained realtime scheduling but also changed process niceness,
  is distribution-specific, and never reached endpoint or audible acceptance. Treat the 512-frame
  candidate as unproven until live read-back shows 128/512 and settled listening passes.
- **2026-08-16:** classify `TASK-002-INSTALL-512-V1` as `consumed_failed` before controller
  execution. Its no-retry boundary is permanent. A successor is justified only as a newly approved
  install-only gate using a fresh sealed controller in an interactive host terminal; it must stop
  after byte-for-byte installed-file read-back and must not activate or validate the runtime.
- **2026-08-16:** classify `TASK-002-INSTALL-512-V2` as `completed` with one consumed attempt. The
  desired installed-but-inactive state is achieved. Do not infer runtime activation or proceed to
  reboot, restart, playback, capture, rollback, or another gate without separate exact authority.
- **2026-08-16:** classify `TASK-002-ACTIVATE-512-V1` as `completed` with one consumed attempt. The
  corrected rule applies to Main at 128 frames and four periods and the complete endpoint inventory
  recovered. Keep hardware geometry and sound-quality conclusions unproven until separately
  authorized playback opens the PCM and the user supplies an audible verdict.
- **2026-08-16:** classify the following playback checkpoint as failed verification. Actual ALSA
  geometry remained 128/256 and occasional crackle remained audible, so reject this activation as a
  512-frame performance result. Do not retry, repair the rule, restart, or roll back under the spent
  activation authority.
- **2026-08-16:** replace UCM `buffer_size 512` with direct-plugin `periods 4` for the next bounded
  candidate. Keep the WirePlumber rule because it controls the PipeWire client side of the same
  four-period geometry. Do not install or claim the replacement as a fix until live ALSA read-back
  proves 128/512 and settled audible/error acceptance passes.
- **2026-08-16:** classify `TASK-002-INSTALL-PERIODS4-V1` and
  `TASK-002-ACTIVATE-PERIODS4-V1` as completed with one consumed attempt each. The installed pair
  and endpoint recovery pass, but keep the candidate unverified until user-started playback proves
  actual ALSA 128/512 geometry and supplies an audible verdict.
- **2026-08-16:** reject the periods-based activation as a 512-frame result. The exact installed
  UCM and WirePlumber requests both resolve to two periods once playback opens, so the earlier
  near-size ordering diagnosis was incomplete. Do not present either current-stack form as a
  release default or retry another restart without a newly evidenced control seam.
- **2026-08-16:** classify the corrected host constraint probe as completed and consumed. The live
  PCM itself refines to exactly 2 periods and 256 frames and rejects 4 periods before `hw_params`.
  ALSA's current 28 KiB preallocation, despite an 832 KiB allocation ceiling, identifies the
  driver's minimum-sized managed-buffer request as the limiter. Advance only to a separately
  authorized source correction; do not infer module replacement, restart, playback, or capture.
- **2026-08-16:** classify `TASK-002-INSTALL-MODULE-BUFFER-V1` as `consumed_failed` before controller
  execution. Its single host invocation reached an unexposed `sudo` password prompt and was
  cancelled after the user reported no visible approval surface. The installed predecessor is
  unchanged. Never reuse this gate; any successor needs fresh approval and a user-visible host
  authentication mechanism.
- **2026-08-16:** admit the user's subsequent direct terminal installation as completed external
  state, not as a retry of the consumed V1 controller. Exact read-back matches the built candidate
  and refreshed dependency lookup, while the loaded predecessor remains active. Keep module
  activation, service restart, and live geometry/listening as separately authorized boundaries.
- **2026-08-16:** classify `TASK-002-ACTIVATE-MODULE-BUFFER-V1` as `consumed_failed`. PipeWire's
  enabled sockets reactivated the stopped services before the root controller's closed/no-holder
  precondition, so the candidate was never loaded. The controller restored services and the full
  endpoint graph. Never retry V1; a successor must include the two PipeWire sockets in its exact
  stop/start set and keep playback/capture validation separate.
- **2026-08-16:** admit the user's subsequent direct terminal activation as completed external
  state. The candidate module is loaded, the full endpoint graph returned, and enumeration proves
  128/512 ALSA geometry. Keep ordinary playback and audible/error acceptance as the final separate
  validation boundary; do not infer capture testing or further runtime mutation.
- **2026-08-16:** retain the proven 128/512 geometry as the best current candidate but do not call it
  a complete crackle fix. The user's initial "sounds mint" verdict softened to occasional crackle;
  Main accumulated four graph errors while the Firefox client remained at zero and the kernel
  remained fault-free. Re-enter the System76/PipeWire scheduling seam before any 8- or 16-period
  experiment, service restart, capture test, or further driver change.

## Changes

- Created this task record and routed it through `docs/agents/tasks/index.yml`.
- Changed both shared UCM directions from a 256- to 512-frame buffer while preserving the proven
  128-frame hardware period.
- After that buffer-size candidate negotiated back to 256 frames, changed both shared UCM slaves to
  request `periods 4` explicitly while preserving the 128-frame period.
- Added a WirePlumber 0.4 rule scoped to Quantum UCM playback/capture `node.name` values and added
  staged install targets for the complete desktop-audio pair.
- Split that rule by direction and added one 128-frame period of ALSA headroom to playback only;
  capture retains the prior period properties without added headroom.
- Updated `alsa/README.md` to describe the paired install and its unproven live status.
- Changed the driver's managed-buffer initial allocation from the two-period minimum to zero while
  retaining the existing 64-period maximum, allowing ALSA to allocate the negotiated buffer during
  `hw_params` instead of constraining refinement to the initial two-period allocation.

## Validation

- Initial read-only inspection confirmed the current UCM/driver geometry and settled live graph
  state. No driver, UCM, module, or persistent user-audio setting was changed for TASK-002.
- The untouched 256-frame checkpoint revalidated live geometry, endpoint inventory, settled error
  counters, IRQ cadence, and recent kernel fault markers. The 512 candidate passed exact-diff,
  staged-install, and isolated-UCM checks. Its exact install and bounded service restart succeeded,
  but live read-back remained 128/256 and made the candidate invalid. A post-restart safety sample
  confirmed stable playback counters, expected IRQ cadence, and the full endpoint inventory.
- The exact rollback restored tracked/installed/runtime 256-frame agreement, but its required
  settled playback verification failed: PipeWire buffer starvation and dshare broken pipes recurred
  and the user heard repeated pops, glitches, and warble. No capture/duplex test or further candidate
  was run after the failure.
- The subsequent read-only diagnostic verified the RTKit grant, current non-realtime audio threads,
  exact installed System76 Scheduler source/configuration behavior, graph-driver geometry, and the
  bounded failure timeline. It made no runtime or repository change except this evidence record.
- The selected candidate staged all four desktop-audio files at mode 0644. An isolated ALSA UCM
  fixture parsed one HiFi verb, 13 playback devices, and 26 capture devices. The WirePlumber rule
  loaded against an intentionally empty PipeWire runtime without a configuration error, and its
  globs matched the preserved 13/26 Quantum node-name inventory exactly. `make -C driver W=1`
  passed with only the host's existing compiler-name and unavailable-pahole-version warnings.
- The first exact install gate passed preflight but failed at `sudo` before its controller ran. Its
  authority is consumed. Post-failure read-back kept the installed UCM at `3fa8c219...6429`, mode
  0644, and the candidate WirePlumber destination absent; installation is not achieved.
- The fresh install gate's exact host-terminal invocation exited 0. Bounded read-back matched both
  sealed candidate hashes and mode 0644. The gate is completed and consumed; no runtime validation
  was performed.
- The activation gate's single user-service restart exited 0. The three services are active, all
  13/26 Quantum endpoints returned, and Main advertises period size 128 plus period count 4. The
  hardware remained closed, so no ALSA geometry or audible claim is made.
- User-started playback then opened at 48 kHz, 26-channel S32_LE and 128/256 frames rather than the
  required 128/512. The user heard some improvement but still occasional crackle. Playback
  verification failed and stopped without broader sampling or mutation.
- The periods-based UCM candidate stages with the other three desktop-audio files byte-for-byte at
  mode 0644. Its isolated UCM fixture parses one HiFi verb, 13 playback devices, and 26 capture
  devices. `git diff --check` passes. No installed or runtime file was changed by this checkpoint.
- The periods-based install read-back matched the new UCM and retained WirePlumber hashes at mode
  0644. The single service restart returned all three services and 13/26 endpoints. Playback stayed
  closed during the bounded wait, so live geometry and sound quality remain pending.
- User-started playback subsequently resolved Main to period count 2 and ALSA to 128/256 while the
  user reported that it seemed good. This fails the required 128/512 geometry and ends the
  periods-based checkpoint without broader diagnostics or mutation.
- The corrected constraint helper's one approved host invocation exited 0 and reported
  `periods=2..2 buffer_size=256..256`; requesting four periods returned `EINVAL`. It did not apply
  hardware parameters, prepare, or start DMA. Post-run playback was closed and no matching kernel
  fault marker appeared. Read-only proc state reports 28 KiB currently preallocated, 832 KiB as the
  allowed maximum, and ALSA DMA preallocation enabled. ALSA core source constrains buffer bytes by
  the current preallocation before managed `hw_params` allocation, matching the driver's use of
  `QUANTUM_AUDIO_MIN_BUFFER_BYTES` as the initial managed allocation.
- The one-line driver candidate passes `make -C driver W=1` against the running 7.0.11 kernel
  headers with no compile or modpost error. The only output warnings are the pre-existing equivalent
  compiler-name report and unavailable BTF input. The uninstalled `snd-quantum2626.ko` has SHA-256
  `357f341d66165d912c5f02340a5a9bf0997ecd70f3e6f62340e2a115238544e6` and vermagic
  `7.0.11-76070011-generic SMP preempt mod_unload modversions`. `git diff --check` passes.
- The install-only V1 controller had SHA-256
  `cacb61473f5105f6d0771c4e6d2abac2b0a769d3f573a7a715219a662fda3277`; preflight matched the
  candidate, installed predecessor, running kernel, file modes, loaded source version, and closed
  PCM. Its only invocation exited 1 at the hidden `sudo` password prompt before controller
  execution. Read-back kept the installed module at `890dcde7...6578`, the candidate at
  `357f341d...44e6`, playback closed, and kernel logs free of matching runtime fault markers.
- After the user ran the supplied install command directly, source and installed module hashes both
  read `357f341d...44e6`, the destination is mode 0644, and dependency lookup selects the installed
  path. The installed candidate source version is `32249FA363697CEC99DC456`; the loaded predecessor
  remains `6CDB07D137537DE2CEB3797`. Playback is closed, so this proves installation only.
- Activation V1 used orchestrator SHA-256 `160ad229...aad7` and root-controller SHA-256
  `d26e41d4...c893`. Its only invocation exited 1 after PipeWire socket activation prevented the
  no-holder precondition. Read-back retained the predecessor loaded source version, restored all
  three services and 13/26 endpoints, and found both PCMs closed. The enumeration burst used the
  unchanged 128/256 geometry with zero-interrupt capture starts/stops and no fault marker.
- After the user manually stopped both PipeWire sockets and the three services, reloaded the module,
  and restored the stack, loaded/installed source versions matched `32249FA363697CEC99DC456` and
  the full 13/26 endpoint inventory returned. `/proc/asound` reports initial preallocation `0` and
  maximum `832` KiB. Enumeration prepared 53,248-byte buffers, exactly 512 frames at 26-channel
  S32_LE with 128-frame blocks. Both PCMs then closed and all 39 Quantum nodes suspended.
- User-started Firefox playback remained RUNNING at 48 kHz, 26-channel S32_LE with exact 128/512
  geometry. The user first described the sound as excellent and then reported occasional residual
  crackle, still the best result so far. Two dshare `Broken pipe` messages occurred at stream start;
  a later ten-second settled sample added no PipeWire or kernel error marker. `pw-top` then showed
  Main at four cumulative errors and Firefox at zero with low timing ratios. PipeWire, Pulse, and
  WirePlumber data loops all remained `SCHED_OTHER`; the active System76 Scheduler service was still
  managing PipeWire policy.
- The playback-headroom candidate loaded successfully through WirePlumber 0.4.17's own Lua
  configuration engine in an isolated PipeWire runtime. Its SHA-256 is
  `b3e47faa53fd4c6a2c30d507fe3bd315882903d1e87fe2331f5cc7994c43de83`. It preserves the already
  proven playback and capture globs, applies `api.alsa.headroom = 128` only to playback, and leaves
  capture at period size 128 plus period count 4. The isolated process exited only because no
  PipeWire core existed in its temporary runtime; no Lua/configuration error occurred.

## Remaining Work

- Restart only PipeWire, PipeWire Pulse, and WirePlumber when the current listening observation is
  complete, then prove the already restored installed/tracked 256-frame bytes and runtime geometry
  still agree. **Completed:** byte/runtime agreement passed, but post-restart desktop stability did
  not.
- Correlate the recurring settled PipeWire `out of buffers`/dshare `Broken pipe` sequence without
  changing the driver or opening capture; do not advance the buffer matrix while the control case
  is intermittently faulting. **Read-only diagnosis completed:** an active 60-second System76
  Scheduler rule can demote the RTKit-promoted PipeWire data loop to `SCHED_OTHER`; exact temporal
  causation remains to be measured.
- **Completed install precondition:** preserved and hashed the exact installed 256-frame UCM and
  confirmed the candidate WirePlumber file absent before installation. The completed install gate
  replaced that control with the sealed candidate pair. Reboot/restart, playback, and capture
  remain separate authority boundaries; do not change the module or hardware state.
- Proposed next live checkpoint, requiring separate direction: retain the exact tracked/installed
  256-frame UCM and module, apply an exact reversible System76 Scheduler exception or equivalent
  narrowly scoped policy that leaves the three audio data loops under PipeWire/RTKit control,
  restart only the affected scheduler/audio services, and sample thread policy plus PipeWire error
  counters at startup and across at least two 60-second refresh boundaries while the user listens.
  Roll back and re-hash the scheduler configuration afterward. Do not use that checkpoint to open
  capture or advance to 512 frames.
- **Checkpoint attempted and failed:** the exception preserved RT20 immediately, but endpoint
  enumeration failed before timing or audible acceptance. Exact configuration rollback also failed
  to restore the PipeWire registry. Do not retry the service restart, reinstall the exception,
  advance the buffer matrix, or touch the module until the user selects a recovery boundary.
- **Completed successor install gate:** created a fresh sealed controller
  at `/tmp/quantum2626-task002-install-512-v2/install-exact-candidate.sh` with controller hash
  `63d73cbee07b1b8a4afd1bf4d340c93c9554506a973e0c61e0a1dfc090d14954`, UCM hash
  `db4d09cbb70b8eefd40b45286a1c5b0a7d83171099b5abc0bcad143080c23192`, and WirePlumber hash
  `8fa704fa556eaf83941fb0862dc0d04b32fa2a002035f98af3b1905ec8d3bd6d`, then invoked it exactly
  once in an interactive host terminal:
  `/usr/bin/sudo /usr/bin/bash /tmp/quantum2626-task002-install-512-v2/install-exact-candidate.sh`.
  Both destinations read back byte-for-byte at mode 0644. The installed-but-inactive state is
  achieved. No retry, restart, reboot, playback, capture, module/device action, cleanup, rollback,
  or runtime claim belongs to this completed gate.
- **Completed activation checkpoint:** the user selected one partial restart rather than a reboot.
  The exact three-service restart returned all 13/26 endpoints without reproducing the pending-
  adapter wedge, and Main advertises period size 128 plus period count 4. Hardware geometry remains
  unavailable while playback is closed.
- **Failed playback validation:** user-started playback remained at ALSA 128/256 and still had
  occasional crackle. The unexpected-geometry hard stop occurred before broader PipeWire-error,
  journal, IRQ, scheduler, or settled-window sampling. Rollback remains another separately
  authorized boundary. Do not retry this activation or advance to 1024 from this invalid 512 result.
- **Completed periods-based install and activation:** installed UCM hash
  `8a837fcc14c4cc23ada9fc9df2f14da87b94cd4ddaf5296cd89e74b021da4bed`, retained WirePlumber hash
  `8fa704fa...d6d`, restarted the exact three services once, and recovered all 13/26 endpoints.
  Playback remained closed. When the user starts playback, require actual ALSA 128/512 geometry
  before settled listening evidence; stop without repair or retry on period count 2 or any other
  unexpected geometry.
- **Failed periods-based playback validation:** Main and ALSA resolved to period count 2 and
  128/256 despite the exact four-period configuration. Preserve the currently good-sounding session
  without intervention. The next diagnosis must identify what constrains the direct-plugin slave
  to two periods; do not infer another install, restart, rollback, or larger-buffer experiment.
- **Diagnosis and source correction completed:** the driver asked ALSA to preallocate only its
  two-period minimum, and ALSA core uses that current allocation as a hardware-refinement ceiling
  even though later managed
  allocation may grow to the separately recorded 64-period maximum. The source now passes `0` as
  the managed-buffer initial size while retaining the existing maximum, and its `W=1` build passes.
  The next boundary is exact module installation and activation planning. Do not install/load it,
  restart services, or open playback/capture without separate exact authority.
- **Install V1 consumed before controller execution:** no installed bytes changed. A successor must
  use a fresh sealed controller and an authentication prompt the user can actually see, such as a
  desktop policy prompt or an exact command run directly in the user's terminal. Do not retry V1
  or infer load/restart/playback authority from a later install approval.
- **Module installation completed externally by the user:** the candidate is now the dependency-
  selected on-disk module, but the old module is still loaded. The next boundary is activation of
  the installed module and restoration of the desktop endpoint graph. Do not infer playback,
  capture, or audible validation authority from installation.
- **Activation V1 consumed without loading the candidate:** service sockets defeated the intended
  quiescent interval, and the recovery branch restored the prior runtime. Any new activation must
  stop `pipewire.socket` and `pipewire-pulse.socket` alongside the services, prove no Quantum device
  holder remains, reload the module once, then start the sockets/services and verify 13/26 endpoints.
- **Manual activation completed:** the installed candidate is now loaded and 128/512 geometry is
  live-proven during endpoint enumeration and ordinary playback. **Playback acceptance is partial:**
  it is materially better but occasional crackle and four Main graph errors remain. Preserve this
  runtime. The next diagnostic boundary is the already identified System76 Scheduler conflict;
  do not open capture, restart services, reload the module, or change buffer geometry implicitly.
- **Completed upstream scheduling research:** the exact installed System76 Scheduler commit
  `8651bbf` creates profiles with `SchedPolicy::Other`, iterates every `/proc/<pid>/task` entry, and
  calls `sched_setscheduler()` even when the profile omits `sched=`. Its stock sound-server rule
  omits `sched=` and its 60-second refresh reapplies that profile, so it can replace PipeWire's
  RTKit-granted per-data-loop `SCHED_RR` priority 20 with `SCHED_OTHER` priority zero. PipeWire's
  own graph documentation says data-processing threads are intended to run realtime. System76
  issues #99 and #102 remain open with general crackling and external-interface 48 kHz/128-frame
  underruns; the historical #114/#118 fix removed whole-process FIFO 49 but changed only the stock
  configuration, not the setter's `SCHED_OTHER` default or all-thread behavior. This independently
  supports the local diagnosis without proving that every audible crackle has this single cause.
- Proposed next live checkpoint, requiring separate exact authority: install a full System76
  configuration override that excepts only `/usr/bin/pipewire` and `/usr/bin/pipewire-pulse`, reload
  only System76 Scheduler, then separately restart the three user audio services once so PipeWire
  can reacquire per-data-loop RTKit priority. Require all 13/26 endpoints and exact 128/512 geometry,
  then observe thread policy and error deltas across more than two 60-second refresh intervals while
  the user listens. Do not set FIFO on every process thread, change rate/geometry, open capture,
  reload the module, or infer rollback authority.
- **Scheduler-isolation checkpoint completed, 2026-08-16:** the exact full configuration override
  excepting only `/usr/bin/pipewire` and `/usr/bin/pipewire-pulse` was installed once at
  `/etc/system76-scheduler/config.kdl`, SHA-256
  `48f1743e3db8b2adeb110b41cd3f41a17bb11378bfd697ac62696b30d68ee677`, mode `0644`, owner
  `root:root`. System76 Scheduler was reloaded and the three user audio services were restarted
  once. All 13 playback and 26 capture endpoints returned. PipeWire and PipeWire Pulse data loops
  reacquired `SCHED_RR` priority 20 and retained it through 150 seconds, spanning more than two
  scheduler refresh intervals; their main threads remain `SCHED_OTHER` nice 0. The stock recording
  profile separately moved WirePlumber to `SCHED_OTHER` nice -9 after its first refresh, which does
  not demote the two audio-server data loops. During user playback ALSA remained exactly 48 kHz,
  26-channel S32_LE with 128-frame periods and a 512-frame buffer. Main's cumulative PipeWire error
  count stayed fixed at one and Firefox stayed at zero across the settled sample; focused user and
  kernel journals showed no xrun, underrun, overrun, DMA timeout, or fault. The user reports that
  initial crackling eases but occasional crackle remains. Classify scheduler isolation as proven
  and beneficial infrastructure correction, but no-crackle acceptance as incomplete. Preserve the
  override and 128/512 runtime; the next bounded seam is the 44.1 kHz graph-to-48 kHz hardware rate
  conversion or legacy dshare pointer/accounting path, not a larger hardware buffer.
- **48 kHz graph-isolation checkpoint active, 2026-08-16:** the user-level PipeWire fragment
  `/home/jamie/.config/pipewire/pipewire.conf.d/51-quantum2626-rate.conf` was installed once,
  SHA-256 `f251c0e971fa06e172857b86833dda041878b5308ec719801d3f6107cdcc3385`, mode `0644`, owner
  `jamie:jamie`, and the three user audio services were restarted once. PipeWire 1.0.3 now reports
  `clock.rate=48000` and `clock.allowed-rates=[ 48000 ]`; all 13/26 Quantum endpoints returned.
  The post-restart 20-sample graph observation contained no active playback stream. The user later
  reported that residual crackle remained; the immediate read-back again found ALSA closed and an
  idle Firefox stream still declaring 44.1 kHz with zero errors, so no active-stream geometry or
  error delta was captured. Classify the 48 kHz graph restriction as audibly insufficient, while
  recognizing that it removes only the graph-to-fixed-device rate boundary: it does not provide a
  native 44.1 kHz path because the driver and UCM still constrain the hardware to 48 kHz. Do not
  treat this as a test of hardware rate switching or claim that all resampling was eliminated.
- **Native-rate source implementation completed offline, 2026-08-16:** renewed static analysis of
  the exact official Universal Control 5.1.1.113315 artifact, matching the previously recorded
  installer and DriverKit hashes, confirms the `0x32` setter contract: two little-endian `u32`
  request fields `{clock-source wire enum, sample-rate wire enum}`, followed by response code
  `0x01` and a zero `u32` status. The vendor stops DMA and frees resources first. The Linux source
  now advertises only 44.1/48 kHz at 26 channels, 88.2/96 kHz at 18 channels, and 176.4/192 kHz at
  8 channels; rejects mismatched duplex geometry; refuses rate changes while running; performs the
  setter only with DMA resources absent; verifies status, rate read-back, and the duplex channel
  register; and preserves the current rate without an unnecessary write. `W=1`, checkpatch 0/0,
  and `git diff --check` pass. Built module SHA-256 is
  `74422a1675292015f0e622f21a8cc99550adb975d1ab1650c97c416fa6608a28`, srcversion
  `1DA82813C64453A1BC965D9`. No module installation/reload, service action, PCM open, or hardware
  rate write occurred. The tracked UCM remains intentionally fixed to the live-proven 48 kHz
  topology; the first live successor must prove 48 kHz unchanged, then switch only an idle direct
  PCM to 44.1 kHz under separate exact authority.
- **Native-rate module installation completed, 2026-08-16:** the exact candidate was installed once
  at `/lib/modules/7.0.11-76070011-generic/updates/snd-quantum2626.ko` and `depmod` completed. Host
  read-back is SHA-256 `74422a1675292015f0e622f21a8cc99550adb975d1ab1650c97c416fa6608a28`,
  srcversion `1DA82813C64453A1BC965D9`, mode `0644`, owner `root:root`; `modinfo -n` resolves that
  exact path. The loaded module remains predecessor srcversion `32249FA363697CEC99DC456`, both PCMs
  remain closed, and no module reload, service action, playback/capture open, TCI write, or cleanup
  occurred. Installation authority is consumed; activation remains a separate live boundary.
- **Native-rate module activation completed, 2026-08-16:** one bounded activation stopped the three
  user audio services and both PipeWire sockets, proved that no Quantum PCM/device holder remained,
  replaced predecessor srcversion `32249FA363697CEC99DC456`, and restored all five user units. The
  loaded module is now candidate srcversion `1DA82813C64453A1BC965D9`. Fresh probe read-back reports
  `clock_rate=48000 Hz`, `device_rate=48000 Hz`, and 26 capture/playback channels; PipeWire restored
  exactly 13 Quantum sinks and 26 Quantum sources with `clock.rate=48000` and allowed rates
  `[ 48000 ]`. Both PCMs remained closed, and no playback/capture open or 44.1 kHz setter was
  performed. This proves the new artifact preserves the idle 48 kHz control state; audible playback
  and the first idle 44.1 kHz switch remain separate live checkpoints.
- **First native 44.1 kHz switch completed, 2026-08-16:** exact controller SHA-256
  `95fb72d015d84475799acee2ffca84ee09c48f553babb50ceab21d4a8d306a93` stopped the three
  user audio services and both sockets, proved both Quantum PCMs closed with no device holder, and
  invoked one direct playback at 44.1 kHz, S32_LE, 26 channels, 128-frame periods, and a 512-frame
  buffer using one second of digital silence. The driver accepted the TCI setter and its built-in
  status/rate/channel verification logged `TCI sample rate changed: rate=44100 Hz channels=26`.
  DMA prepared with exact 53,248-byte 128/512 geometry, ran for 345 interrupts (the expected
  one-second order at 44.1 kHz/128 frames), and stopped cleanly. Both PCMs returned to `closed`; no
  xrun, underrun, overrun, DMA timeout, or fault was observed. One skipped unrelated TCI RX record
  appeared while awaiting the rate read-back, after which the correlated verification succeeded.
  Do not classify that skip as a failed switch. PipeWire/WirePlumber and both sockets remain
  intentionally stopped so the fixed-48 kHz UCM cannot immediately switch the device back. The
  next separate checkpoint is to create and install an exact 44.1 kHz desktop UCM/graph candidate,
  then restore the user audio stack and verify 13/26 endpoints without a fallback to 48 kHz.
- **44.1 kHz desktop candidate installed and active, 2026-08-16:** source and installed UCM hashes
  are `704b0b05eceb7616550a3f3b4f4e4222538dc9587e3cab389100a4e79fb74f76` for
  `P2626.conf` and `b57446a456db4304110be8ac56094be3464619e10747a3e50b6b50124bef3296`
  for `HiFi.conf`; both are root-owned mode `0644`. The user graph fragment is SHA-256
  `d42eadf76910c01f7e9e05c67bdfdc112052ff6836877ad075e0b725b7232a5a`, owner
  `jamie:jamie`, mode `0644`, and parses to rate/allowed-rates `44100` only. The correctly targeted
  WirePlumber rule remains byte-identical. Exact install/start controller SHA-256
  `d3c84c021cc81afc8555ec03ec1a2dde367acafa9c66a70caf1bb1b5bba73abe` completed once.
  All five user audio units are active; PipeWire reports graph rate `44100`, allowed rates
  `[ 44100 ]`, and exactly 13 Quantum sinks plus 26 Quantum sources. Both PCMs settled closed, and
  both PipeWire data loops hold `SCHED_RR` priority 20. WirePlumber's initial ALSA capability probe
  briefly selected 48 kHz with an 8192-frame buffer before returning the device to the UCM-selected
  44.1 kHz/26-channel 128/512 geometry. That probe was bounded to startup and produced no timeout,
  fault, xrun, underrun, overrun, or error marker. Treat the settled desktop rate as proven but
  audible crackle acceptance as pending user playback.
- **First audible 44.1 kHz desktop acceptance, 2026-08-16:** during ordinary Firefox playback the
  Main ALSA PCM was observed running at exactly 44.1 kHz, S32_LE, 26 channels, 128-frame periods,
  and a 512-frame buffer while capture remained closed. PipeWire Main ran at 44.1 kHz with a
  256-frame graph quantum, Firefox supplied native 44.1 kHz audio, and both nodes retained zero
  graph errors across five consecutive samples. The user reported **no clicks**. This proves the
  first clean audible native-44.1 desktop session; retain the configuration and use longer ordinary
  listening to determine whether the earlier intermittent crackle is fully eliminated.
- **Longer 44.1 kHz acceptance failed, 2026-08-16:** the user later reported heavy popping and a
  vinyl-like grain while the same Firefox/Main stream was still running. Live read-back remained
  exactly 44.1 kHz, S32_LE, 26 channels, 128-frame periods, and a 512-frame hardware buffer;
  capture was closed. Main and Firefox retained zero PipeWire errors across ten samples, both audio
  data loops remained `SCHED_RR` priority 20, the installed scheduler/UCM/rate hashes were unchanged,
  and the device delivered 1,035 IRQs in three seconds, matching 44.1 kHz/128-frame cadence. No
  kernel or user-audio timeout, fault, xrun, underrun, overrun, or error was logged, and no system
  suspend/resume occurred. The kernel slave's `appl_ptr=0` and nonsensical raw delay are the already
  documented dshare accounting artifact, not new proof of a driver pointer defect; the driver
  callback itself returns the hardware position modulo the negotiated buffer. Classify the initial
  no-click sample as non-durable and the settled corruption as below PipeWire's error accounting.
  Upstream alsa-lib documents `slowptr` as the dshare mode for slower but more precise pointer
  updates. The next narrow candidate is `slowptr true` on the playback dshare only, leaving capture,
  rate, period, buffer, scheduler, and `hw_ptr_alignment` unchanged; installation/restart/listening
  remain a separate live boundary.
- **Playback-only slow-pointer candidate active, 2026-08-16:** the UCM adds only `slowptr true` to
  the playback dshare; capture dsnoop, 44.1 kHz rate, S32_LE/26-channel format, 128/512 geometry,
  WirePlumber policy, and scheduler policy remain unchanged. Isolated and installed `_alibcfg`
  read-back both contain the playback-only setting. Source and installed UCM SHA-256 are
  `20724f1b5f0aac8cb2d035d075cdc0195da252151f7a4968b62d55f6c2850f86`, mode `0644`, owner
  `root:root`. Exact install/restart controller SHA-256
  `81ea5551aa0dd8032e5169bb92841bc09f11590235dca6505d4048e957305d8c` completed once.
  All five user audio units are active, the PipeWire graph remains restricted to 44.1 kHz, all
  13 Quantum sinks and 26 sources returned, both PCMs settled closed, and the realtime/fault
  invariants remained clean. No playback acceptance occurred during read-back; require ordinary
  playback beyond the prior several-minute failure window before classifying this candidate.
- **Playback-only slow-pointer listening result, 2026-08-16:** the user reports that the sustained
  vinyl-like grain is no longer present, but an occasional pop remains and appears to coincide
  with some musical transients. Treat `slowptr true` as beneficial but insufficient, not as a
  durable fix. The clean PipeWire error counts, realtime scheduling, exact IRQ cadence, and
  44.1-kHz/128/512 geometry from the active-stream read-back remain the control evidence. Renewed
  static analysis of the exact vendor HAL resolves the sample representation: signed interleaved
  linear PCM with 24 significant bits aligned high in each 32-bit word. Linux correctly uses an
  S32_LE container. The source now advertises `msbits=24` without changing sample storage, gain,
  rate, channels, period, or buffer geometry. `W=1`, checkpatch 0/0, and `git diff --check` pass;
  built module SHA-256 is `936671cb441888a8d679b7ac8d18a967d70e9210eb7b137c969b942a2c2bb362`
  with srcversion `700300BDE3C3C11C904B3F7`. Preserve this as a source-correctness candidate, not a
  proven pop fix. The reduced-volume listening discriminator made a remaining pop less obvious but
  did not eliminate it, so unity-gain operation remains the acceptance target. No installation,
  module action, restart, playback, capture, or runtime change occurred in this checkpoint.
- **Playback-only headroom candidate prepared, 2026-08-16:** PipeWire documents
  `api.alsa.headroom` as extra ringbuffer space for devices whose read/write position is not
  reported accurately. Because `slowptr true` materially reduced the below-PipeWire grain, the
  next narrow experiment adds 128 frames of headroom to Quantum playback only. The capture rule is
  separate and unchanged apart from retaining its existing period properties. This preserves
  44.1 kHz, S32_LE/26-channel format, 128/512 hardware geometry, scheduler policy, dshare
  alignment, and unity software gain while adding approximately 2.9 ms of playback margin. The
  exact candidate hash is `b3e47faa...de83`; WirePlumber 0.4.17 loaded it without a configuration
  error in an isolated runtime, and its unchanged globs retain the admitted exact 13/26 matching
  proof. It is not installed or active. Installation, service restart, and listening remain
  separate live boundaries; do not combine this test with loading the uninstalled `msbits=24`
  module, IRQ-affinity changes, or latency-QoS changes.
- **Playback-only headroom candidate installed and active, 2026-08-16:** the exact
  `b3e47faa...de83` WirePlumber rule was installed once through the visible host PolicyKit channel
  and read back root-owned at mode 0644. One restart of only PipeWire, PipeWire Pulse, and
  WirePlumber exited 0. All three services are active, the complete 13-playback/26-capture Quantum
  inventory returned, and both PCMs settled closed. Main's authoritative SPA `Props` parameter
  reports period size 128, period count 4, and headroom 128; a capture node reports period size
  128, period count 4, and headroom 0. The first strict check incorrectly treated absent suspended-
  node exported properties as a mismatch; direct parameter read-back resolved the classification
  without retry or mutation. No module action, capture open, rate change, geometry change, IRQ
  policy, latency QoS, or playback acceptance occurred. Ordinary unity-gain listening is now the
  sole next checkpoint for this candidate.
- **256-frame playback-headroom A/B active, 2026-08-16:** the user described the 128-frame
  headroom result as “pretty good,” with one tiny pop in approximately 30 seconds. Treat that as a
  material improvement but not elimination. The next candidate changes only playback headroom from
  128 to 256 frames, adding approximately another 2.9 ms while retaining the exact 44.1 kHz,
  S32_LE/26-channel, 128/512 hardware geometry. WirePlumber 0.4.17 loaded the candidate without a
  Lua/configuration error in an isolated runtime; exact SHA-256 is
  `98c0febe888b864dfc3a9fe97f6adf9edd7369ee596d22661e9a65cd9a68a218`. The one approved host
  installation read back root-owned at mode 0644, and the one three-service restart exited 0. All
  services and 13/26 endpoints returned. Main's SPA `Props` reports period size 128, period count
  4, and headroom 256; capture retains 128, 4, and headroom 0. Both PCMs settled closed. No driver,
  module, rate, hardware geometry, scheduler, IRQ, QoS, or capture action was combined with this
  activation. Longer unity-gain listening is pending.
- **CPU-latency QoS discriminator and source candidate, 2026-08-16:** after the user still heard an
  occasional pop with 256 frames of playback headroom, a temporary privileged process opened
  `/dev/cpu_dma_latency`, requested exactly 2 us, and held that request only for the listening
  interval. The exact holder script SHA-256 was
  `0681bdd068cd440b5a492244e72cd6125c3687f4f0e584030fd38110ee8cf4ff`; it reported PID 489410.
  CPU0's 120-us C2 and 1034-us C3 usage counters stopped advancing while it was active.
  During ordinary playback the user reported, “I didnt hear a single pop its clear af.” The holder
  was then released; no holder remained, C2 advanced from 11136565 to 11139402, and C3 advanced
  from 13810741 to 13811453 over three seconds. This is the
  strongest causal evidence so far that wake/IRQ latency contributes to the residual pops, but it
  is a short listening result rather than durable acceptance. The driver source now reuses ALSA's
  existing `latency_pm_qos_req` and tightens it to 2 us only after a successful PCM prepare; ALSA
  owns removal during PCM teardown. This ties the power/performance tradeoff to the configured PCM
  lifetime rather than a permanent userspace holder. `W=1`, checkpatch 0/0, and
  `git diff --check` pass. Built module SHA-256 is
  `553635940c21b666d89b333e4783c28ade9510d5e5c7effaa5eaf8db52643138`, srcversion
  `4B3A66AF5A381999FA112F3`; its expected unresolved QoS imports are
  `cpu_latency_qos_add_request`, `cpu_latency_qos_request_active`, and
  `cpu_latency_qos_update_request`, all exported GPL symbols on the running kernel. No install,
  module action, service restart, PCM open, or further runtime mutation occurred. Installation and
  activation remain a separate live boundary.
- **CPU-latency candidate installed and activated, 2026-08-16:** install gate
  `TASK-002-INSTALL-QOS-2US-V1` invoked exact controller SHA-256
  `2631fa26d0ceec429376a178354c7072f5de156bb40f987a912039fc67597f52` once. The dependency-selected
  module read back root-owned mode 0644 with exact SHA-256
  `553635940c21b666d89b333e4783c28ade9510d5e5c7effaa5eaf8db52643138` and srcversion
  `4B3A66AF5A381999FA112F3`; the old srcversion remained loaded until the distinct activation gate.
  Activation gate `TASK-002-ACTIVATE-QOS-2US-V1` then invoked exact controller SHA-256
  `62293a3f498af358c980073e4195f7bb92735d8d1381bc93056ba2b8be28ba97` once. It stopped exactly the
  PipeWire/Pulse sockets and services plus WirePlumber, proved the Quantum control/playback/capture
  device nodes unheld, reloaded only `snd_quantum2626`, verified the new srcversion and PCI binding,
  then restarted the same five units. Read-back found the installed hash exact, the new srcversion
  loaded, PCI `1c67:0104` rebound to `snd-quantum2626`, ALSA card `P2626` present, all five units
  active, exactly 13 sinks and 26 sources, and both PCMs closed. Startup discovery exercised
  128/512-frame prepare/start/stop paths; the settled sample contained no kernel or user-audio xrun,
  underrun, overrun, timeout, fault, pending-adapter, broken-pipe, or out-of-buffers marker. One
  WirePlumber proxy-destroyed activation message occurred during graph reconstruction but did not
  recur after startup and did not prevent the exact endpoint inventory. No playback or capture was
  opened by the gate. Audible acceptance and direct confirmation of the 2-us request while a PCM is
  configured remain pending user-started playback.
- **Combined-candidate audible regression and localization, 2026-08-16:** user-started Firefox
  playback after activation crackled and sounded worse than the earlier temporary 2-us QoS result.
  Live read-back proved the driver request was effective: over three seconds CPU0 C2 (120 us) and
  C3 (1034 us) usage counters did not advance, matching the temporary-holder discriminator. The
  stream retained 44.1 kHz, 26-channel S32_LE, 128-frame periods, a 512-frame hardware buffer,
  `slowptr true`, and 256 frames of PipeWire headroom. Both PipeWire data loops remained `SCHED_RR`
  priority 20; Main and Firefox retained zero graph errors; and IRQ 213 advanced by 1,037 in three
  seconds, consistent with the expected 44.1 kHz/128-frame cadence. No matching kernel or
  user-audio xrun, underrun, overrun, timeout, fault, broken-pipe, or out-of-buffers marker appeared.
  PipeWire now reports `alsa.resolution_bits = 24`, proving the previously uninstalled `msbits=24`
  source correction became active alongside the driver-scoped QoS request. The clean temporary-QoS
  listening result used the prior module without that metadata. Therefore QoS application failure
  is excluded by observation and `msbits=24` is the leading regression variable, but causation
  remains an inference until an exact QoS-only A/B removes that constraint. No restart, reload,
  rollback, source correction, or playback/capture command was performed during this diagnosis.
- **QoS-only discriminator prepared offline, 2026-08-16:** the source now removes only
  `QUANTUM_AUDIO_SIGNIFICANT_BITS` and the `snd_pcm_hw_constraint_msbits()` call from the crackling
  combined candidate. The 2-us per-substream QoS update, native-rate implementation, PCM format,
  channels, period/buffer limits, DMA/IRQ behavior, and all desktop configuration remain unchanged.
  `W=1`, checkpatch 0/0, and `git diff --check` pass. Exact source SHA-256 is
  `a99ce31bfafdd9170f247fe4ec71c21fb6c579d41512278c72616edd356ef937`; built module SHA-256 is
  `b6f261d074f94ca50b94c50d505242cad53a8bb6cfd96a798bf4b953484e025b`, srcversion
  `BB865ACB071304AE53DE91D`. Its only CPU-latency imports remain the expected add/active/update GPL
  symbols. This is offline integrity evidence only; the combined candidate remains installed and
  loaded until the separately sealed install and activation gates complete.
- **QoS-only discriminator installed and activated, 2026-08-16:** install gate
  `TASK-002-INSTALL-QOS-ONLY-V1` invoked controller SHA-256
  `bb34df803615f108f7cb81fdc3819378c071e75ef4bbd87805c380ea65838d2b` exactly once. The installed
  module read back root-owned mode 0644 with exact SHA-256
  `b6f261d074f94ca50b94c50d505242cad53a8bb6cfd96a798bf4b953484e025b` and srcversion
  `BB865ACB071304AE53DE91D`; the combined candidate remained loaded until the distinct activation.
  Activation gate `TASK-002-ACTIVATE-QOS-ONLY-V1` invoked controller SHA-256
  `0e1ac90761f1dbfb2b44cc13d80cd333c9d84d1f9a8c48c874ba9d6f9510b68f` exactly once. It stopped the
  same five PipeWire/Pulse/WirePlumber units and sockets, proved all Quantum ALSA nodes unheld,
  reloaded only `snd_quantum2626`, verified the new srcversion and PCI binding, and restarted those
  units. Read-back found all five active, exactly 13 sinks and 26 sources, PipeWire and Pulse data
  loops at `SCHED_RR` priority 20, and both PCMs closed. Main's SPA `Props` retained period size 128,
  period count 4, and headroom 256; discovery prepared exact 128/512 hardware geometry. PipeWire now
  reports `alsa.resolution_bits = 32`, proving the intended removal of only the precision metadata.
  One proxy-destroyed WirePlumber activation message occurred during reconstruction, did not recur,
  and did not prevent the complete endpoint graph. The settled sample had no xrun, underrun,
  overrun, timeout, fault, pending-adapter, broken-pipe, or out-of-buffers marker. No playback or
  capture was opened by the gates; ordinary listening is the remaining acceptance checkpoint.
- **First QoS-only audible acceptance, 2026-08-16:** during ordinary Firefox playback the user
  reported, “this is it!! this is what I paid for with the quantum sounds fucking excellent clean
  af.” Immediate read-back matched the exact installed/loaded QoS-only artifact. ALSA was RUNNING at
  44.1 kHz, 26-channel S32_LE, 128-frame periods, and a 512-frame buffer; capture remained closed.
  PipeWire reported resolution bits 32, period size 128, period count 4, and headroom 256. Main and
  Firefox retained zero graph errors across the bounded sample, and both PipeWire data loops stayed
  `SCHED_RR` priority 20. CPU0's 120-us C2 and 1034-us C3 counters did not advance over approximately
  three seconds, directly confirming the driver-scoped 2-us request remained effective; IRQ 213
  advanced by 1,050 in the same bounded window, consistent with 44.1 kHz/128-frame cadence. No
  kernel or user-audio xrun, underrun, overrun, timeout, fault, broken-pipe, or out-of-buffers marker
  appeared. This cleanly separates the successful QoS-only candidate from the failed combined
  `msbits=24` build. Treat it as strong immediate acceptance, not yet long-duration release
  acceptance, because earlier artifacts sometimes degraded only after additional listening.
- **Native-44.1 live-duplex failure isolated, 2026-08-16:** the user connected NeuralRack's JACK
  client from Quantum Mic/Instrument Input 1 to Main left/right while Firefox was also linked to
  Main. PipeWire showed the source, NeuralRack, Main, and Firefox links exactly as intended. At
  14:57:09 the driver prepared and started capture-only `directions=0x2`, stopped after zero IRQs,
  rebuilt exact 53,248-byte 128/512 resources for `directions=0x3`, and resumed only the previously
  running capture mask `0x2`. Source inspection confirms the later playback trigger joins an
  already-running engine without another hardware restart. Both PCMs then reported RUNNING at
  44.1 kHz, 26-channel S32_LE and 128/512 geometry, all three PipeWire nodes retained zero errors,
  Pulse remained responsive, and no kernel or user-audio fault appeared, but NeuralRack and
  Firefox were both inaudible. Closing NeuralRack at 15:06:57 stopped the duplex engine after
  202,639 IRQs, rebuilt playback-only `directions=0x1`, and resumed playback; capture closed and
  Firefox became audible but crackled. Playback geometry and zero graph errors remained exact,
  both PipeWire data loops retained `SCHED_RR` priority 20, and CPU0 C2/C3 usage counters remained
  frozen, proving the driver QoS request was still active. The user then paused YouTube for ten
  seconds so playback fully closed and reopened; playback returned clean. This is an observed
  44.1-kHz live-duplex lifecycle failure below PipeWire error accounting, not a regression in the
  accepted steady playback geometry, scheduling, or QoS candidate. The leading source seam is
  pointer/period phase continuity when the second direction late-joins the rebuilt joint engine;
  fix and validate that transition before reopening NeuralRack or claiming native-44.1 duplex.
- **Offline native-44.1 duplex lifecycle candidate, 2026-08-16:** the source now allocates fixed
  playback and capture PCM buffers at PCM construction and programs both stable DMA addresses when
  either direction first prepares. Adding or freeing one direction therefore no longer stops,
  rebuilds, or resumes the joint engine while the other direction runs. A late START remains
  pending until the next hardware-buffer wrap, at most 512 frames or about 11.6 ms at 44.1 kHz;
  its pointer reports zero until that boundary and its first `period_elapsed` notification occurs
  one period later. This preserves physical-ring and ALSA-ring phase without modifying PCM-core
  accounting. The candidate source SHA-256 is `304724c5...3376`; its built module SHA-256 is
  `c4e874b6...88bc` with srcversion `7B1636C1FDE52CD275CAC7C`. `git diff --check`, kernel
  `checkpatch` (0 errors, 0 warnings), and the running-kernel `W=1` build pass. This is offline
  integrity evidence only: the module has not been installed or loaded, and no playback, capture,
  service, or device state changed.
- **Installed and activated duplex lifecycle candidate, 2026-08-16:** the user manually installed
  exact module SHA-256 `c4e874b6...88bc`, then ran corrected activation controller SHA-256
  `8a32bf0f...33e2`. Read-back proves loaded srcversion `7B1636C1FDE52CD275CAC7C`, PCI
  `1c67:0104` rebound to `snd-quantum2626`, all five PipeWire/Pulse/WirePlumber units active, and
  exactly 13 Quantum sinks plus 26 sources restored. Ordinary playback reopened at native
  44.1 kHz, 26-channel S32_LE, 128-frame periods, and a 512-frame buffer while capture remained
  closed. The bounded activation log contains no xrun, DMA fault, timeout, warning, BUG, or oops.
  This proves exact activation and playback-control preservation, not the repaired transition;
  NeuralRack must now add and remove capture while playback remains active.
- **Playback-only regression discriminator, 2026-08-16:** before any capture late join, the user
  reported persistent pops during YouTube Music playback; a ten-second pause did not clear them.
  ALSA remained native 44.1 kHz, 26-channel S32_LE at 128/512, capture stayed closed, PipeWire
  reported no xrun or graph error, IRQ 213 advanced by 1,040 in about three seconds, CPU0 C2/C3
  remained frozen under the 2-us QoS request, and both PipeWire data loops retained `SCHED_RR/20`.
  The source was therefore restored byte-exactly to the prior QoS-only control SHA-256
  `a99ce31b...ef937` and rebuilt as exact module SHA-256 `b6f261d0...025b`, srcversion
  `BB865ACB071304AE53DE91D`. Checkpatch 0/0, `W=1`, and `git diff --check` pass. The loaded and
  installed duplex module is unchanged; install and activation of this A/B remain separate gates.
- **QoS-only playback A/B installed but inactive, 2026-08-16:** gate
  `TASK-002-INSTALL-QOS-ONLY-AB-V1` invoked fresh controller SHA-256
  `bf3cee9d...7c69` exactly once and completed. The disk module is exact SHA-256
  `b6f261d0...025b`, srcversion `BB865ACB071304AE53DE91D`, root-owned mode 0644. Loaded srcversion
  remains `7B1636C1FDE52CD275CAC7C`; all five user-audio units remained active and playback remained
  RUNNING at native 44.1 kHz, 26-channel S32_LE, 128/512. No restart, reload, capture, or activation
  occurred. Runtime activation requires a distinct authorization.
- **QoS-only playback A/B activated, 2026-08-16:** gate
  `TASK-002-ACTIVATE-QOS-ONLY-AB-V1` invoked fresh controller SHA-256
  `ae35ee91...e4ac` exactly once. The controller returned exit 1 without output, but bounded
  read-back proves the requested end state completed: loaded srcversion is
  `BB865ACB071304AE53DE91D`, PCI remains bound, all five audio units are active, exactly 13 sinks
  plus 26 sources returned, and playback reopened at native 44.1 kHz, 26-channel S32_LE, 128/512.
  IRQ 213 advanced by 1,035 in about three seconds, CPU0 C2/C3 remained frozen, and no kernel fault
  appeared. One `out of buffers` marker occurred at the old PipeWire process's activation boundary;
  it is not a settled error. The gate is completed by read-back and was not retried. Ordinary
  listening now provides the playback-only A/B result; native-44.1 duplex remains intentionally
  unsupported by this control.
- **QoS-only playback A/B audible result, 2026-08-16:** the user still heard pops, though they may
  be somewhat reduced. This rejects the duplex candidate as the root cause while allowing that its
  persistent-buffer lifecycle may slightly worsen susceptibility. The recurrent defect survives
  exact native 44.1 kHz/128/512 geometry, 256 frames of device headroom, `slowptr true`, 2-us QoS,
  correct average IRQ cadence, and `SCHED_RR/20` PipeWire loops without a settled xrun marker. The
  next bounded discriminator is PipeWire graph quantum, not another driver lifecycle edit.
- **Forced graph-quantum test rejected and rolled back, 2026-08-16:** an approved runtime-only
  `clock.force-quantum=512` gate changed Main from its active 256-frame graph quantum to 512 while
  preserving native 44.1 kHz and hardware 128/512. PipeWire recorded two errors at the live switch,
  then the counter stayed flat, but the user immediately heard roughly double-speed, corrupted
  playback. A separately approved rollback reset `clock.force-quantum=0`; Main returned to quantum
  256, Firefox timing normalized, and hardware geometry stayed unchanged. Do not repeat the forced
  512 graph quantum as a crackle remedy.
- **Post-quantum graph recovery, 2026-08-16:** resetting the metadata alone left the existing
  Firefox/PipeWire stream audibly corrupted. A separately approved restart of only the five
  PipeWire/Pulse/WirePlumber units rebuilt the graph without reloading the driver. Read-back found
  all five active, exact loaded QoS-only srcversion `BB865ACB071304AE53DE91D`, automatic quantum 0,
  13 sinks plus 26 sources, Main RUNNING at quantum 256 with zero fresh errors, Firefox RUNNING with
  zero errors, and unchanged native 44.1 kHz/128/512 hardware geometry.
- **Immediate post-recovery audible acceptance, 2026-08-16:** the user reported normal playback
  with no pops. Across the settled sample, Main and Firefox remained at zero errors, IRQ 213
  advanced by 1,037 in about three seconds, and CPU0 C2/C3 remained frozen. Repeated historical
  `out of buffers` messages belonged to pre-restart PipeWire PID 766239; current PipeWire PID
  788726 entered active state at 16:03:04 and has no matching error. Leave this graph running and
  require longer listening before treating the intermittent defect as closed.
- **Refined shared-transport duplex candidate built offline, 2026-08-16:** retain the mature
  professional-interface baseline used by ALSA's RME HDSP and FireWire streaming drivers: fixed
  playback/capture DMA storage, one shared transport lifetime, and per-direction logical stream
  attachment. The source now also advertises `SNDRV_PCM_INFO_SYNC_START`, assigns the standard
  card sync identifier, and handles same-card linked substreams as one trigger operation with
  `snd_pcm_group_for_each_entry()` and `snd_pcm_trigger_done()`. An independent direction that
  joins an already-running Quantum ring remains pending at logical pointer zero until the next
  512-frame hardware wrap, then receives its first elapsed-period notification one 128-frame
  period later. This preserves the hardware-ring/ALSA-ring phase requirement that software-only
  FireWire pointer attachment does not have. The IRQ path detects the ring counter crossing rather
  than requiring a zero-position sample, so ordinary handler latency cannot miss the join boundary.
  Source SHA-256 is `49a19aeb...0058`; module SHA-256 is `ab0b231f...ade5`, srcversion
  `F54583811438D0400BD5585`. `git diff --check`, kernel
  `checkpatch` (0 errors, 0 warnings), and `make -C driver W=1` against 7.0.11 pass. This is offline
  integrity evidence only. The exact QoS-only module remains the runtime control; no install,
  reload, audio-service action, playback, capture, or hardware operation occurred.
- **Refined duplex candidate installed but inactive, 2026-08-16:** one exact PolicyKit invocation
  ran controller SHA-256 `0b5941d0...d7ae` after revalidating candidate module
  `ab0b231f...ade5`, installed predecessor `b6f261d0...025b`, and loaded QoS-only srcversion
  `BB865ACB071304AE53DE91D`. The controller installed the candidate at mode 0644 and ran `depmod`.
  Read-back resolves `modinfo` and `modprobe --show-depends` to the exact installed candidate with
  srcversion `F54583811438D0400BD5585`; the kernel still reports loaded srcversion
  `BB865ACB071304AE53DE91D`. Installation is complete and inactive. No module reload, audio-service
  action, playback, capture, or runtime validation occurred; activation remains a separate boundary.
- **Refined duplex activation loaded the module but endpoint recovery is incomplete, 2026-08-16:**
  controller SHA-256 `75422bd6...57c4` passed exact module, predecessor, configuration, binding,
  geometry, service, and 13/26 graph preflight, then was invoked once through PolicyKit. It returned
  exit 1 without output and was not retried. Bounded read-back proves candidate srcversion
  `F54583811438D0400BD5585` is loaded, PCI `1c67:0104` is bound, card `P2626` is present, all five
  user-audio units are active, and playback reopened at native 44.1 kHz, 26-channel S32_LE with
  128/512 geometry while capture is closed. All 13 sinks returned, but capture-source count remained
  zero across a five-second settle window. WirePlumber logged one audio-adapter `proxy destroyed`
  activation and one invalid standard-link event; the kernel log contains no xrun, timeout, DMA
  fault, BUG, oops, or panic. Classify activation as consumed with incomplete desktop recovery.
  Do not rerun the controller or restart services without a new exact authority.
- **WirePlumber-only recovery attempt entered the pending-linkable wedge, 2026-08-16:** one approved
  `systemctl --user restart wireplumber.service` invocation exited 0. No PipeWire/Pulse unit or
  kernel module was restarted. All five units subsequently reported active, but repeated full
  PipeWire inventory calls did not complete, including a separately bounded five-second query.
  WirePlumber PID 850128 then logged `1 pending linkable(s) not activated in 20sec`; both Quantum
  PCMs settled closed. Candidate srcversion `F54583811438D0400BD5585` remains loaded and IRQ 213 is
  present. The prior 13/0 inventory is no longer a confirmed-current graph because the registry is
  unresponsive. Stop here: no second WirePlumber restart, broader audio-stack restart, module action,
  or rollback is authorized.
- **Five-unit recovery cleared the wedge but reproduced the capture-adapter failure, 2026-08-16:**
  one approved `systemctl --user restart` invocation targeted exactly the PipeWire and Pulse
  services/sockets plus WirePlumber and exited 0; the driver was not reloaded. PipeWire inventory
  became responsive and all five units are active, but the stable graph is still exactly 13 Quantum
  sinks and zero Quantum sources. Playback reopened at native 44.1 kHz, 26-channel S32_LE with
  128/512 geometry and capture is closed. Kernel discovery repeatedly completed capture-only
  prepare/start/stop at exact 44.1 kHz/128/512 with no DMA or kernel fault; WirePlumber again logged
  `Object activation aborted: proxy destroyed` for one audio adapter and an invalid standard link.
  This is a reproducible refined-candidate desktop regression, not merely a stale registry. The
  newly added ALSA synchronized-start metadata/group-trigger behavior is the narrow leading
  discriminator because the earlier persistent-buffer candidate restored 13/26 under the same
  UCM/WirePlumber configuration, but that attribution remains an inference until an offline A/B.
- **Synchronized-start compatibility A/B built offline, 2026-08-16:** the source removes exactly
  `SNDRV_PCM_INFO_SYNC_START`, `snd_pcm_set_sync()`, and same-card group iteration/trigger completion.
  Persistent fixed playback/capture DMA buffers, one shared engine lifetime, late-direction pending
  state, IRQ wrap-crossing promotion, 2-us QoS, native rate profiles, and 128-frame periods are
  unchanged. Source SHA-256 is `f9de15ab...5d12`; module SHA-256 is `06cb461b...1632`, srcversion
  `B684EFED2CAC8084DCF0D1B`. `git diff --check`, kernel checkpatch (0 errors, 0 warnings), and
  `make -C driver W=1` pass. This is offline integrity evidence only: installed and loaded module
  `ab0b231f...ade5` remains active with the observed 13/0 graph; no install, reload, service action,
  playback, capture, or hardware operation occurred during this checkpoint.
- **Synchronized-start compatibility A/B installed but inactive, 2026-08-16:** one exact PolicyKit
  invocation ran controller SHA-256 `e9a4a003...b220` after revalidating candidate module
  `06cb461b...1632`, installed predecessor `ab0b231f...ade5`, and loaded predecessor srcversion
  `F54583811438D0400BD5585`. The controller installed the candidate at mode 0644 and ran `depmod`.
  Read-back resolves `modinfo` to candidate srcversion `B684EFED2CAC8084DCF0D1B`, while the kernel
  still reports loaded predecessor srcversion `F54583811438D0400BD5585`. Installation is complete
  and inactive. No reload, audio-service action, PCM operation, or runtime validation occurred.
- **Compatibility-A/B activation V1 stopped in preflight, 2026-08-16:** controller SHA-256
  `d490feda...511d` was invoked once through PolicyKit and returned exit 1 without output before any
  service or module action. Read-back proves loaded synchronized-start srcversion remains
  `F54583811438D0400BD5585`, all five units remain active, playback remains native
  44.1 kHz/128/512 with capture closed, and the graph remains 13 sinks/0 sources. The installed
  compatibility module remains exact `06cb461b...1632`. A subsequent labeled read-only check passed
  kernel, installed/loaded module, unit, and 13/0 graph predicates; the silent controller does not
  identify which transient predicate stopped it. Do not retry V1. A successor must expose labeled
  preflight results and requires fresh invocation authority.
- **Compatibility-A/B activation V2 reproduced the failure and exposed an IOMMU fault, 2026-08-16:**
  one exact PolicyKit invocation ran labeled controller SHA-256 `a12e9e40...936c`. Every preflight
  predicate passed, the five user audio units were stopped, predecessor srcversion
  `F54583811438D0400BD5585` was unloaded, installed compatibility srcversion
  `B684EFED2CAC8084DCF0D1B` was loaded, and the five units were started. All units returned active,
  but the final graph remained exactly 13 Quantum sinks and zero sources, so the controller exited
  1. The installed and loaded module is exact `06cb461b...1632`; playback is RUNNING at native
  44.1 kHz, 26-channel S32_LE, 128/512 and capture is closed. During capture-only discovery churn,
  the kernel recorded `DMAR: [DMA Write NO_PASID]` from PCI `09:00.0` to fault address `0x0` with
  reason `0x05` (`PTE Write access is not set`). This rejects synchronized-start/group-trigger
  handling as the cause and makes a capture DMA stop/resource-lifetime race the leading hypothesis,
  not a confirmed source conclusion. V2 authority is consumed; no retry, rollback, or further
  service/module action occurred.
- **Persistent DMA-table lifetime correction built offline, 2026-08-16:** monotonic kernel timing
  places the address-zero DMAR fault at the capture stop boundary: rapid discovery started capture,
  stopped it about 1 ms later with zero IRQs, and emitted the fault as `hw_free` cleared the table
  registers and released their coherent memory. ALSA's fixed playback and capture allocations are
  already card-lifetime buffers. The source now builds both page tables over those complete fixed
  allocations once, retains the tables and MMIO addresses across `hw_free`, probe cycles, and
  stopped rate changes, and changes only the active byte/frame geometry before prepare. This closes
  the observed zero-address window while preserving native rate/channel profiles, 128-frame periods,
  the 512-frame active desktop buffer, wrap-crossing late-direction promotion, and 2-us QoS. Source
  SHA-256 is `51639424...8cb`; module SHA-256 is `279eae29...0c6b`, srcversion
  `69CC3718CA2E575A1DE5451`. `git diff --check`, kernel checkpatch (0 errors, 0 warnings), and
  `make -C driver W=1` pass. This is offline integrity evidence only; installed and loaded module
  `06cb461b...1632` remains unchanged, and no service, module, PCM, or hardware action occurred.
- **Persistent DMA-table installation V1 stopped before mutation, 2026-08-16:** exact controller
  SHA-256 `64dd23eb...91ba` was invoked once through PolicyKit and exited 1 after printing the
  `preflight:loaded-predecessor` label but before `action:install`. Authority is consumed and V1
  must not be retried. Bounded read-back proves the installed module remains exact
  `06cb461b...1632`, loaded srcversion remains `B684EFED2CAC8084DCF0D1B`, PCI remains bound to
  `snd_quantum2626`, card `P2626` remains present, playback remains RUNNING, and capture remains
  closed. Classification identified a controller defect: it expected sysfs driver basename
  `snd_quantum2626`, while the actual driver directory is correctly named `snd-quantum2626`.
  No install, `depmod`, reload, service action, PCM operation, cleanup, or rollback occurred. A
  corrected successor must be newly sealed and separately approved.
- **Persistent DMA-table installation V2 completed, 2026-08-16:** after fresh approval, corrected
  controller SHA-256 `93f26db3...45c3f` was invoked exactly once through PolicyKit. All labeled
  preflight predicates passed; it installed exact module `279eae29...0c6b`, srcversion
  `69CC3718CA2E575A1DE5451`, root-owned mode 0644, and ran `depmod` for kernel
  `7.0.11-76070011-generic`. Privileged and independent read-back confirm the installed hash and
  srcversion. Loaded srcversion remains predecessor `B684EFED2CAC8084DCF0D1B`, PCI remains bound,
  playback remains RUNNING, and capture remains closed. Installation is complete and inactive;
  no reload, service restart, PCM operation, or runtime validation occurred.
- **Persistent DMA-table activation V1 loaded safely but did not restore capture nodes, 2026-08-16:**
  controller SHA-256 `c84ceac1...da03` was invoked exactly once through PolicyKit. All preflight
  predicates passed, including the installed candidate, loaded predecessor, exact UCM/WirePlumber
  hashes, active five-unit audio stack, 13/0 graph, and native 44.1 kHz/128/512 playback geometry.
  It stopped the five units, unloaded predecessor srcversion `B684EFED2CAC8084DCF0D1B`, loaded
  candidate srcversion `69CC3718CA2E575A1DE5451`, and restarted all five units. PCI/card read-back
  passed, but the final graph remained 13 sinks/0 sources, so the controller exited 1 and must not
  be retried. The rapid capture-only discovery storm again produced zero-IRQ start/stop cycles, now
  without any DMAR/IOMMU fault, DMA stop timeout, or page-table timeout. This validates the narrow
  persistent-table safety property but does not repair WirePlumber's `proxy destroyed` adapter
  failure. User-session logs briefly referenced all 26 input stream IDs before the objects became
  invalid, consistent with capture nodes being created then destroyed rather than never described.
  Playback is RUNNING at native 44.1 kHz, 26-channel S32_LE, 128/512 and capture is closed. No retry,
  rollback, second restart, playback command, or capture command occurred.
- **User-observed playback regression under the persistent maximum-map candidate, 2026-08-16:**
  ordinary playback has a new “weird static sound.” Read-only diagnosis confirms loaded srcversion
  `69CC3718CA2E575A1DE5451`, exact native 44.1 kHz/26-channel S32_LE/128/512 geometry, capture
  closed, and 1,036 IRQ 213 events over three seconds versus about 1,034 expected. No new DMAR,
  IOMMU, xrun, timeout, warning, BUG, or oops marker appeared. The candidate's new maximum-sized
  data-page mapping is therefore the leading regression variable: persistent coherent table memory
  fixed the address-zero teardown fault, but publishing every maximum-buffer page changed the
  hardware-visible table extent relative to the previously audible active-size mapping. Reject this
  candidate for playback. The next offline design should allocate table capacity once, retain its
  DMA address across `hw_free`, and populate/link only the active-buffer pages. No restart, rollback,
  module action, service action, or source correction occurred in this diagnosis.
- **Persistent-table/active-page correction built offline, 2026-08-16:** each capture and playback
  table now allocates coherent capacity once for the maximum supported PCM buffer and retains that
  DMA address across `hw_free`. A separate population step zeros the table, writes only the active
  buffer's DMA page entries, and links only the segments required by those active pages. At the
  current 53,248-byte/512-frame geometry this restores the prior exact 13-data-page extent with no
  extra segment link, while a stopped geometry change repopulates the same allocation rather than
  freeing it. This preserves the address-zero safety fix without exposing the rejected maximum data
  extent. Source SHA-256 is `1a11efe8...2d0e`; module SHA-256 is `d54f2bf4...b45e`, srcversion
  `D1D19FA61C85B05A46E2A01`. `git diff --check`, kernel checkpatch (0 errors, 0 warnings, 0 checks),
  and `make -C driver W=1` pass. Installed and loaded maximum-map module `279eae29...0c6b` remains
  unchanged; no install, reload, service action, PCM operation, or hardware mutation occurred.
- **Active-page correction installation V1 completed, 2026-08-16:** exact controller SHA-256
  `fb182171...fe86` was invoked once through PolicyKit after candidate, predecessor, loaded runtime,
  PCI, and ALSA predicates passed. It installed module `d54f2bf4...b45e`, srcversion
  `D1D19FA61C85B05A46E2A01`, root-owned mode 0644 and ran `depmod` for the running kernel.
  Read-back confirms that exact installed artifact while loaded srcversion remains rejected
  maximum-map `69CC3718CA2E575A1DE5451`; playback remains RUNNING and capture remains closed.
  Installation is complete and inactive. No reload, restart, PCM operation, or runtime validation
  occurred.
- **Active-page correction activation V1 loaded safely but still lacks capture nodes, 2026-08-16:**
  exact controller SHA-256 `9b3a5865...8b8d` was invoked once through PolicyKit. All installed
  candidate, loaded predecessor, UCM/WirePlumber, PCI/card, service, 13/0 graph, and native
  44.1 kHz/128/512 predicates passed. It stopped the five audio units, unloaded rejected srcversion
  `69CC3718CA2E575A1DE5451`, loaded active-page srcversion `D1D19FA61C85B05A46E2A01`, and
  restarted all five units. PCI/card and active-service read-back passed, but the stable graph
  remained 13 sinks/0 sources, so the controller exited 1 and must not be retried. Playback returned
  RUNNING at exact 44.1 kHz, 26-channel S32_LE, 128/512 and capture is closed. Rapid capture probes
  again completed without a DMAR/IOMMU fault, DMA-stop timeout, or page-table timeout. Audible
  validation of the static regression is pending. No retry, rollback, second restart, playback
  command, or capture command occurred.
- **User-observed active-page playback acceptance, 2026-08-16:** after ordinary playback began on
  active-page srcversion `D1D19FA61C85B05A46E2A01`, the user reported “sounds pretty good now.”
  The distinct weird static heard under the maximum-map predecessor is not reproduced in this
  immediate interval. This supports active-only page population as the correct playback mapping,
  but does not yet establish long-duration no-pop acceptance. Capture publication remains failed at
  the separately observed stable 13/0 graph.
- **User-observed sustained active-page playback acceptance, 2026-08-16:** after continued ordinary
  gaming use, the user reported “no pops at all,” “been great,” and “super stable.” Neither the
  maximum-map static artifact nor the earlier intermittent pop reproduced during this longer
  real-world interval. This is the strongest playback acceptance for TASK-002. It establishes the
  current active-page mapping as the release-performance candidate for playback; it does not prove
  native-44.1 duplex.
- **Delayed active-page capture publication observed, 2026-08-16:** the activation controller's
  bounded 10-second checkpoint ended at 13 sinks/0 sources, but a later direct read-only `pw-dump`
  snapshot found all 13 Quantum sinks and 26 Quantum sources without another restart or module
  action. Input 1 is correctly published as node 95, a one-channel `MONO` source backed by
  `quantum2626_mono_in:P2626,0,0`; its suspended state is normal while no client is linked.
  Reclassify 13/0 as a startup checkpoint rather than the final stable graph. Capture remains
  closed, so this proves endpoint recovery but not native-44.1 duplex behavior.
- **Malformed NeuralRack route rejected as duplex evidence, 2026-08-16:** the locally built
  standalone app launched at 44.1 kHz/256 JACK frames. Source inspection confirms
  `neuralrack:in` is MIDI, `neuralrack:in_0` is its single audio input, and `out_0`/`out_1` are
  stereo audio outputs. PipeWire accepted an incorrect Input 1 audio link to the MIDI port; after
  the real audio input was also linked, NeuralRack emitted an xrun and segfaulted in its userspace
  `pw-data-loop`. The Quantum hardware reached exact joint 44.1 kHz/26-channel S32_LE/128/512
  geometry without a Quantum, DMAR, or IOMMU fault. Client exit removed its links, capture closed,
  and Firefox playback remained linked at the same geometry. Do not classify this malformed-route
  crash as a driver or duplex result. A clean test uses only Input 1 to `neuralrack:in_0`, then
  `out_0`/`out_1` to Main left/right.
- **Clean NeuralRack routing retry live, 2026-08-16:** a freshly launched standalone client remains
  running at 44.1 kHz/256 JACK frames with only the intended three audio links: Input 1 to
  `neuralrack:in_0`, `out_0` to Main left, and `out_1` to Main right. Playback and capture are both
  open at exact 44.1 kHz/26-channel S32_LE/128/512 geometry. One connection-time xrun appeared in
  NeuralRack's terminal, but the client and links remained present and no Quantum, DMAR, IOMMU,
  timeout, fault, BUG, or oops marker appeared in the bounded kernel log. Audible validation is
  pending.
- **NeuralRack model-enable crash classified outside the driver, 2026-08-16:** the user heard the
  correctly routed live input before enabling the saved JC-40 model crashed NeuralRack. The second
  segfault reproduced the first executable offset `0x3904e` on another CPU. An exact unstripped
  relink maps that offset to the post-model `memcpy` in `NeuralModelLoader::compute()`, whose local
  implementation uses variable-length realtime stack buffers. The saved model is a supported
  48-kHz NAM 0.7 `SlimmableContainer`. Client exit removed the links, capture closed, Firefox
  playback remained at exact 44.1 kHz/26-channel S32_LE/128/512, and no Quantum, DMAR, or IOMMU
  fault appeared. This proves routing and duplex transport reached the app but does not complete an
  audible processed-guitar test. Treat preallocated app buffers as the narrow next discriminator;
  do not change the driver or stable desktop geometry for this userspace crash.
- **NeuralRack app-side discriminator built offline, 2026-08-16:** a separate temporary source copy
  now gives `NeuralModelLoader` reusable process and resample buffers prepared outside its realtime
  callback, includes capacity guards, and expands the NAM model's maximum block size for 44.1-to-
  48-kHz resampling. The standalone build succeeded at hash `a26a3ed9...dee8`, links against the
  system PipeWire JACK library, and its `compute()` disassembly has one fixed 24-byte stack frame
  with no allocation call. This is build/disassembly proof, not runtime acceptance. The candidate
  remains `/tmp/neuralrack-debug.gY9Hq1/bin/Neuralrack`; no launch, PipeWire link, restart, driver
  action, or model processing followed the offline build. Live launch and correct three-link routing
  remain a separate boundary.
- **NeuralRack fixed-build live discriminator, 2026-08-16:** the temporary fixed app survived model
  enable at the intended Input 1 -> `in_0` -> Main route, so the variable-stack-buffer crash fix is
  effective. The user heard processed audio with many pops while exact duplex 44.1 kHz/26-channel
  S32_LE/128/512 geometry held. Main consumed only 0.02--0.03 of its PipeWire deadline, Input 1
  effectively zero, bounded error totals did not advance, and no driver or app crash appeared. An
  offline probe of the exact `StreamingResampler` chain shows 256-frame callbacks producing 253,
  255, 256, or 257 return frames. `NeuralModelLoader::compute()` discards that count and copies 256
  unconditionally, creating stale or dropped block-edge samples. Treat proper output-frame
  accumulation as the next app-only fix; do not alter the Quantum driver or stable graph geometry.
- **NeuralRack exact-block output fix built offline, 2026-08-16:** after the user closed the app,
  the temporary candidate gained a preallocated circular return queue primed with eight frames
  (about 0.18 ms). It retains all 253--257 produced frames and consumes exactly 256 per callback,
  with no realtime allocation. The exact rate chain stayed within -3..0 cumulative frames over one
  million blocks. A 10,000-block 1-kHz A/B reduced the maximum adjacent step from 0.449398 on the
  original copy-256 path to 0.150643 on the queued path, ending with five frames buffered. Build
  `4c2913b3...321f` succeeds; `compute()` has a fixed 40-byte stack frame and no allocator call.
  This updated `/tmp/neuralrack-debug.gY9Hq1/bin/Neuralrack` remains unlaunched and unlinked; live
  JC-40 plus cabinet validation is the next separate boundary.
- **Overnight ordinary-playback recurrence observed, 2026-08-17:** the user returned to occasional
  mild Firefox pops after all three desktop-audio services had run since 17:52 August 16 with zero
  restarts. NeuralRack is not running, capture is closed, and exact native 44.1 kHz/26-channel
  S32_LE/128/512 remains active. Main's actual quantum is 256 despite an unforced global default of
  1024. PipeWire logged `spa.audioconvert: out of buffers` with one suppressed repetition at 20:22;
  Main's accumulated error count rose from the earlier 19 to 29 and active Firefox has one. Those
  totals stayed flat over a later 30-second sample while both nodes used at most 0.03 of their
  deadline. The kernel has no xrun, DMA/IOMMU fault, timeout, BUG, or oops, and a three-second sample
  showed exact IRQ and 44.1-kHz pointer cadence. Main deliberately remains running with
  `node.pause-on-idle=false` and ALSA's infinite silence region, so its long trigger epoch and zero
  `appl_ptr` do not alone prove stale driver state. Classify the return-time event as PipeWire buffer
  starvation; capture the next audible steady-state pop against live counter deltas before changing
  the driver, geometry, or services.
- **Transient clipping independently proven, 2026-08-17:** Main and both initially visible Firefox
  streams read back at 100%/0.00 dB with no additional ALSA mixer gain, proving 100% is unity. The
  first approved float32 Main-monitor capture measured 1.136673689 (about +1.11 dBFS), but the user
  clarified that the second uncorked stream was an idle ChatGPT tab, so summing was not proven.
  After that tab closed, only YouTube Music remained. A second isolated 704,512-sample capture still
  measured 1.127280354 (about +1.04 dBFS), with 790 samples at or above 1.0, 1,174 at or above 0.99,
  and 4,200 at or above 0.95. The YouTube-only float path therefore exceeds full scale at transients
  before S32_LE conversion. The monitor exited; its link transition advanced Main's error count
  once from 29 to 30 while Firefox remained zero, so exclude that increment from spontaneous error
  evidence. No volume or persistent configuration changed. Do not conflate peak overload with the
  separately logged `spa.audioconvert` buffer-starvation event.
- **Clipping rejected as the persistent artifact cause, 2026-08-17:** the user still heard the same
  transient-correlated digital artifact with the only YouTube Music stream at 73%/-8.31 dB, over
  7 dB below the attenuation required by the measured +1.04 dBFS excess. Main/Firefox error totals
  stayed fixed at 30/0 with negligible realtime load. Unity clipping is therefore incidental, not
  causal. Investigate sample continuity below PipeWire accounting—especially dshare/ALSA pointer
  handoff and hardware-period data—without treating lower volume or limiting as a driver fix.
- **Offline loopback-continuity harness prepared, 2026-08-17:**
  `scripts/quantum2626_loopback_soak.py` now generates a deterministic low-level sequence on the
  left side of the Line Outputs 3-4 endpoint, tracks it through one exact selected mono input, and
  records compact ALSA pointer, IRQ, PipeWire, and event-window evidence. Its dependency-free
  self-test distinguishes clean/noisy content, corrupted content, an exact repeated 128-frame
  period (`-128`), and an exact skipped period (`+128`).
  `docs/LOOPBACK_CONTINUITY_TESTING.md` records the preferred direct Out 3 to In 3 patch, a
  configurable exact return source, -30 dBFS starting level, exact
  44.1-kHz/26-channel/S32_LE/128/512 runtime predicates, and fail-closed stop conditions. This is
  offline integrity evidence only. No PipeWire endpoint was opened and no playback, capture,
  service, module, or configuration action occurred. Physical output identity, five-minute
  calibration, and any overnight soak remain separately approved live checkpoints.
- **Physical loopback input identified, 2026-08-18:** with the user-connected patch in place, one
  bounded five-second scan sent a -36 dBFS pulsed 660 Hz signal only to Line Out 3 and captured the
  exact 26-channel hardware frame. The signal returned unambiguously on ADAT Input 1, zero-based
  channel 10 / ALSA channel 11, with a 44.64 dB spectral margin over the runner-up. Loaded
  srcversion remained `D1D19FA61C85B05A46E2A01`, the graph remained 13 sinks/26 sources, exact
  native-44.1-kHz/26-channel/S32_LE/128/512 duplex geometry held, capture closed afterward, and no
  raw audio was retained. The harness now accepts an explicit capture-node fragment, and the
  runbook records `quantum2626_mono_in_P2626_0_10__source` for this wiring. Classify the return as
  Quantum DAC -> patch bay -> Digimax ADC -> ADAT Input 1; Digimax/ADAT clocking is therefore a
  confound, not part of a direct Quantum analog-loop claim. Short continuity calibration remains
  the next separately bounded live checkpoint.
- **Five-minute loopback calibration passed, 2026-08-18:** the separately approved harness run used
  -30 dBFS Line Out 3 and the exact ADAT Input 1 node for 300.009 seconds. It analyzed 3,227 blocks
  with zero continuity events, zero phase-delta frames in every telemetry sample, absolute
  correlation 0.969441--0.981008, and a maximum captured peak of -49.2974 dBFS. Both PCMs retained
  exact native 44.1 kHz, 26-channel S32_LE, 128/512 geometry throughout. The Quantum sink, ADAT
  source, and `pw-record` error counts remained zero; `pw-play` entered the first sample with one
  connection-time error and did not advance. The kernel delivered 105,083 interrupts over the
  305.003-second DMA epoch, exact 44.1-kHz/128-frame cadence, with no xrun, DMA/IOMMU fault,
  timeout, warning, BUG, or oops. Capture closed, all three helper stderr files remained empty, and
  no event audio was created. A post-teardown read-only registry check retained all 13 sinks and 26
  sources, including ADAT Input 1. Preserve the minimum Digimax gain. This validates the harness
  and current return level, not root-cause localization; an overnight soak remains a separate live
  checkpoint because the return still includes Digimax/ADAT clocking.
- **Eight-hour loopback soak terminated at its event ceiling, 2026-08-18:** the separately approved
  transient run used the calibrated -30 dBFS Line Out 3 to ADAT Input 1 path and retained exact
  native 44.1-kHz/26-channel/S32_LE/128/512 geometry. It failed closed after 346.221 seconds and
  3,689 blocks when it reached 1,000 continuity events; `summary.json` and all retained evidence
  remain under `/tmp/quantum2626-loopback-overnight-20260818-1`. The first 53 seconds were clean,
  then events arrived in bursts with repeated recovery to about 0.98 correlation. The terminal set
  contains 968 low-correlation blocks and 32 recovered phase jumps, 20 of which are exactly
  +/-256 frames. That dominant recovered displacement matches the PipeWire graph quantum rather
  than the 128-frame hardware period. Over the same run, the Line Out 3 sink error count advanced
  0->52, `pw-play` 1->194, ADAT Input 1 0->2, and `pw-record` 0->174. PipeWire logged playback
  `snd_pcm_mmap_commit` `Broken pipe` errors and `spa.audioconvert` buffer starvation during the
  dense bursts; the kernel logged only prepare/start/stop, delivered 121,005 interrupts over the
  approximately 351.2-second DMA epoch at the expected 44.1-kHz/128-frame cadence, and emitted no
  DMA/IOMMU fault, timeout, warning, BUG, or oops. Both PCMs are closed and helper stderr files are
  empty after teardown. Classify this as real ALSA/PipeWire xrun evidence, not clipping or steady
  clock drift, but do not use its event count as driver-causality proof: low-correlation analysis
  took about 37 ms versus 1.1 ms normally while playback was fed by another thread in the same
  Python interpreter, allowing analyzer GIL contention to amplify an initial discontinuity.
- **Non-amplifying harness correction verified offline, 2026-08-18:** playback feeding now runs in
  an isolated process forked before the telemetry thread starts, while the parent retains analysis,
  logging, and fail-closed supervision. The offline self-test now exercises that feeder as well as
  clean, repeated-period, skipped-period, and corrupted-content fixtures; three consecutive runs,
  Python bytecode compilation, `git diff --check`, and the existing driver `W=1` build pass. This
  changes only diagnostic integrity. It is not installed driver code and does not authorize a live
  retry, service restart, module action, or longer soak. The next justified live discriminator is a
  short corrected loopback calibration before considering any driver or desktop-policy candidate.
- **Corrected five-minute loopback calibration passed, 2026-08-18:** the separately authorized
  non-amplifying harness completed 300.035 seconds and 3,227 analysis blocks on the existing
  -30 dBFS Line Out 3 -> Digimax/ADAT Input 1 return with zero continuity events and zero phase
  displacement. Absolute correlation stayed between 0.975788 and 0.981085, and the maximum
  captured peak was -49.3026 dBFS. Playback and capture retained exact native
  44.1-kHz/26-channel/S32_LE/128/512 geometry. The selected sink, selected source, and `pw-record`
  error counts stayed zero; `pw-play` acquired one connection-time error at 0.31 seconds and did
  not advance. The 305-second DMA epoch delivered 105,092 interrupts at expected cadence and the
  bounded kernel log contained only prepare/start/stop, with no user-audio service entries. All
  helper stderr files are empty; both PCMs closed; the loaded srcversion remains
  `D1D19FA61C85B05A46E2A01`; and the complete 13-sink/26-source graph survived teardown. This
  confirms the old shared-interpreter feeder materially amplified the prior 1,000-event run, so
  that run is not evidence of an autonomous driver failure. It does not erase the user's ordinary
  playback pops or localize their cause, and the Digimax/ADAT return remains a loopback confound.
  Any longer corrected soak is a fresh live checkpoint; no install, restart, or driver candidate is
  justified by the contaminated result.
- **Corrected long-run loopback classified, 2026-08-18:** the isolated-feeder run under
  `/tmp/quantum2626-loopback-overnight-corrected-20260818-2` retained exact native
  44.1-kHz/26-channel/S32_LE/128/512 duplex geometry for 5,838.383 seconds and 62,834 analysis
  blocks. The first reported continuity event followed 3,890.338 clean seconds. During the ensuing
  bursts, the selected sink advanced from 0 to 33 PipeWire errors, `pw-play` from its fixed
  connection-time 1 to 160, the selected source from 0 to 3, and `pw-record` from 0 to 148. All
  four nodes remained at a 256-frame PipeWire quantum; sampled busy ratios stayed at or below 0.07,
  IRQ cadence remained centered on 44.1 kHz / 128 frames, and the two ALSA hardware pointers
  continued at about 44.1 kframes/s. The 39 recovered phase jumps include 17 at +256 and 9 at -256
  frames. The first retained event window contains one internal +256-frame sequence jump while all
  sixteen 256-frame slices correlate at 0.974--0.981; the second contains +256 and +512 jumps with
  slice correlations of 0.968--0.982. This proves real captured sample-continuity displacement
  aligned with PipeWire error bursts, not clipping, steady clock drift, or a threshold-only false
  positive. It does not identify whether playback, capture, ALSA, the driver, or the Digimax/ADAT
  return originated the first displacement.
- **Global reacquisition correction and retained-window replay verified offline, 2026-08-18:** the
  analyzer now searches the complete 8,191-frame reference after local lock fails. A globally
  matched displacement is counted once and becomes the new expected phase; a genuine loss of global
  lock records one correlation-drop episode, advances the trusted expected timeline, logs recovery
  without a second defect event, and fails closed after 16 consecutive lost blocks. Synthetic
  fixtures retain exact +/-128-frame skip/repeat detection, reacquire a +1,024-frame displacement
  once, collapse five corrupt blocks to one loss event, and recover at the expected phase. Read-only
  replay of all 1,000 immutable event captures used the corrected adaptive threshold of 0.68496938.
  It globally reacquired 893 of 961 old correlation drops and confirmed 36 of 39 original phase
  jumps at or above that threshold; 71 captures remained globally unclassifiable. Median global
  correlation was 0.97852768 and the minimum was 0.07222929. This confirms that the raw count,
  ceiling, and apparent burst length are analyzer inflation while preserving the real intermittent
  PipeWire-visible discontinuities and a bounded set of globally unclassifiable blocks.
  Stable IRQ/pointer cadence remains absent positive driver-fault evidence, and the Digimax/ADAT
  return still confounds playback, capture, converter, and clock locus. No driver, desktop, service,
  endpoint, or artifact state changed. Any direct-ALSA versus PipeWire or dual-return experiment
  remains a separately authorized live checkpoint.
- **Direct Line Input 3 calibration stopped on absent return signal, 2026-08-18:** one approved
  invocation targeted the unique Line Outputs 3-4 sink and Line Input 3 source at -30 dBFS for a
  planned five minutes, using the corrected analyzer and reported direct balanced Out 3 -> Input 3
  cable with monitoring off and gain at minimum. It acquired exact native
  44.1-kHz/26-channel/S32_LE/128/512 geometry, then failed closed after 10.288 seconds because the
  capture remained below the -60 dBFS usable-signal floor. No analysis block or continuity event
  was admitted. The selected sink stayed at 33 errors, `pw-play` at its existing 1, the source at
  zero, and `pw-record` at zero; all helper stderr files are empty and no matching kernel or
  user-audio fault appeared. All three services and the exact two endpoints survived, while
  PipeWire retained both hardware PCMs RUNNING before and after with zero application pointers.
  Evidence remains under `/tmp/quantum2626-loopback-direct-calibration-20260818-1`; summary SHA-256
  is `d7c50375e45269ca4e7140b1179bcac8aff4dc2bf63b26638af65427c82eaa82` and events SHA-256 is
  `605db45d403db7473e301ce817143ad2f090c389980190d771ff49a466d5dc88`. This proves only that no
  usable signal reached the selected Line Input 3 node under the reported physical/gain state; it
  does not distinguish cable placement, input mode/routing, minimum-gain attenuation, or source
  identity. The invocation is consumed. Do not retry, raise the stimulus, change gain, switch
  inputs, or begin an ALSA/PipeWire A/B without a new exact live-test authorization.
- **Input 3 gain increase did not recover the direct return, 2026-08-18:** after the user reported
  raising Input 3 above minimum, one separately approved 30-second level check used the same exact
  sink, source, -30 dBFS stimulus, and native 44.1-kHz/26-channel/S32_LE/128/512 geometry. It again
  failed closed on no usable signal after 10.312 seconds with zero admitted blocks or events.
  Sink/`pw-play`/source/`pw-record` counters again stayed fixed at 33/1/0/0; helper stderr remained
  empty; no matching kernel or user-audio fault appeared; and services plus endpoints survived.
  Summary SHA-256 is `2768f71d8589ac1a1026fd6dc3b09933166a21faed41ba77e490214eff200aa2`
  and events SHA-256 is `5ec24db8e362b06e45a19081c856514574447c95c128f7c77b23392228d09e19`
  under `/tmp/quantum2626-loopback-direct-levelcheck-20260818-1`. This makes minimum gain alone a
  weaker explanation and leaves physical jack/input mode, cable/output path, or source identity as
  the leading unresolved readiness variables. It does not identify which variable is wrong. The
  check is consumed; do not retry or switch paths without new exact authority.
- **Higher Input 3 gain proves the direct analog return, 2026-08-18:** after the user raised Input 3
  further, one approved 30-second check completed 30.027 seconds and 320 analysis blocks on the
  exact Line Out 3 -> Line Input 3 path with zero events, zero loss episodes, and zero phase delta
  in every telemetry sample. Absolute correlation stayed between 0.98098128 and 0.98515020; RMS
  remained -57.6709 to -57.5692 dBFS and the maximum peak was -47.2137 dBFS, leaving ample clipping
  headroom. Both PCMs retained exact native 44.1-kHz/26-channel/S32_LE/128/512 geometry.
  Sink/`pw-play`/source/`pw-record` counters stayed fixed at 33/1/0/0, helper stderr remained empty,
  no matching kernel or user-audio fault appeared, and all services plus endpoints survived. This
  confirms the reported direct cable, Line Out 3 route, Line Input 3 UCM binding, and physical input
  path. The two prior no-signal stops were insufficient-gain observations, not wiring or source-map
  failures. Evidence remains under `/tmp/quantum2626-loopback-direct-levelcheck-20260818-2`;
  summary SHA-256 is `4d2a120c0b5e1544dff109b14c00f007f586d22093f3aff6c91045e6846cb82a`
  and events SHA-256 is `25dba69963f8ced98c10e65c89efda6745788cb7fd9db846e945482dc6425c13`.
  Preserve the current gain position. This is level/path readiness, not a five-minute or long-run
  direct-return continuity result; any longer run requires fresh exact authorization.
- **Five-minute direct-return calibration reproduces bounded discontinuities, 2026-08-18:** one
  separately approved run completed 300.052 seconds and 3,227 analysis blocks on the proven Line
  Out 3 -> Line Input 3 cable at the preserved gain and exact native
  44.1-kHz/26-channel/S32_LE/128/512 duplex geometry. The corrected analyzer recorded four events:
  two locked +256-frame phase jumps and two one-block global-lock-loss episodes, recovering once at
  +256 frames and once at +512 frames. It did not inflate either loss episode into a burst. The
  selected sink held 33 errors after connection, `pw-play` held 1, and the source held zero, while
  `pw-record` advanced 0->4. Signal remained stable at -57.7177 to -57.5067 dBFS RMS with a
  -47.2113 dBFS maximum peak; ordinary locked telemetry correlation reached 0.98510390. Across
  299.534 seconds of telemetry, capture and playback hardware pointers advanced 13,210,086 and
  13,210,087 frames while IRQ count advanced 103,204. Helper stderr is empty, all desktop-audio
  services and exact endpoints survived, every ALSA stream closed on teardown, and the bounded
  kernel log contains only normal DMA prepare/start/stop messages with no xrun or fault. This direct
  Quantum DAC-to-ADC return excludes the Digimax/ADAT converter, return, and external clock as
  necessary causes of the observed discontinuities. It positively establishes captured sequence
  displacement accompanied by PipeWire capture-helper errors, but continuous IRQ/pointer cadence
  and an empty fault log remain absent positive driver-fault evidence; the run does not distinguish
  PipeWire, ALSA PCM handling, the driver, or the Quantum's own data path. Evidence remains under
  `/tmp/quantum2626-loopback-direct-calibration-20260818-2`; summary/events/`pw-top` SHA-256 are
  `c9d97180e96c62c378bac42b8c6c2b14f190934d8dd139b2c036f1816f5a97bf`,
  `133b0557101808eb6a47c2f683742938b47d684e0b3776f3adcd5560502a66fc`, and
  `cdff459a925254d1e5e423a9aa695dbbe42c4d8e3d07eaee4e1fcba74915f1cc`. The invocation is consumed;
  do not retry or begin a direct-ALSA/PipeWire A/B without a new exact authorization.
- **First direct-ALSA arm is analyzer-contaminated and rejected, 2026-08-18:** one approved
  five-minute comparison arm opened `hw:P2626,0` directly with the same physical Line Out 3 ->
  Line Input 3 return and exact 44.1-kHz/26-channel/S32_LE/128/512 duplex geometry. The initial
  backend synchronously drained all 26 capture channels in the analysis process. Capture was
  already `XRUN` in the first telemetry sample; `arecord` logged 1,002 overruns, and its repeated
  recovery produced 1,000 high-correlation phase jumps before the fail-closed event ceiling stopped
  the run at 269.237 seconds/1,468 blocks. Six later `aplay` underruns accompanied repeated normal
  DMA stop/prepare/start cycles. PipeWire's suspended sink/source counters remained zero, all ALSA
  streams closed on teardown, and no DMA, IOMMU, or kernel fault appeared. Reject the raw event
  count and this arm as a PipeWire-versus-ALSA discriminator: analysis backpressure created the
  ALSA xruns and recovery jumps it then counted. Immutable evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-1`; summary/events/`pw-top` SHA-256 are
  `3e5be71a59572e63f90d0939bd00f2177355f8c64ccb64b6a645fe3a6ae52251`,
  `304a5774058a602d75f0b25c406c9ae6642460f22e9f0024255f31cab7f8e9ad`, and
  `7a6d7bd0559c2ef39b5dcd55b6792ab4910136bf903d76501a04f8b2c1a8d9d9`. The consumed invocation
  cannot be retried.
- **Direct-ALSA harness correction is offline-proven, 2026-08-18:** direct capture now uses a
  dedicated process to continuously drain the full 26-channel stream and forward only channel
  index 2 to the analyzer. Direct `aplay`/`arecord` helpers now treat the first xrun as fatal, and
  telemetry fails closed if either PCM leaves `RUNNING`, preventing helper recovery from inflating
  one overload into hundreds of analyzer events. Focused `py_compile` and self-test pass, including
  exact 26-channel packing/extraction, silent guard channels, isolated playback feeding, isolated
  capture extraction, +/-128 and +1,024-frame displacement, and persistent-loss recovery. The
  corrected script SHA-256 is
  `f4c46ce2ca9c5a95ede332f41c0fdba4551f83f17441d2be62bfe5a65faff379`. This is offline readiness
  only; a fresh direct-ALSA invocation requires new exact live-test authorization.
- **Corrected direct-ALSA arm fails at capture startup, 2026-08-18:** the separately approved exact
  invocation used the sealed corrected harness and created the intended direct-ALSA artifact once,
  but `arecord` reported one fatal overrun before ALSA geometry validation. The harness failed
  closed after 0.370 seconds with zero admitted analysis blocks, events, loss episodes, or signal
  measurements. `aplay` then reported an interrupted write during teardown, and the isolated
  extractor reported the resulting short final block; neither is a continuity observation. Both
  PCMs closed, all three audio services and the complete 13-sink/26-source graph survived, and the
  bounded kernel and user-audio run-window searches contained no matching fault. No IRQ or hardware
  pointer cadence was admitted. This is positive direct-ALSA capture-helper xrun evidence, not
  positive driver-fault evidence, and it does not reproduce or exclude the PipeWire arm's four
  continuity events. The corrected arm remains invalid as a PipeWire-versus-lower-layer
  discriminator. Immutable evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-2`; summary/events/`pw-top` SHA-256 are
  `965b46e99c597e119e4bbdb59eba383bfebb86159f5565f8b7878e54f9703b03`,
  `0113919ed0ec516bdfec23c281f1982207f83a0740574b6626f9e540207d021e`, and
  `44a9cf4b576f738d84b288f9c82fb5a5f854012151e3c67687beaebf851c77c0`. The invocation is consumed;
  do not retry, repair the harness, or begin another backend under this authority.
- **Direct-ALSA startup overrun is localized and corrected offline, 2026-08-18:** the old harness
  launched `arecord` before starting its Python extractor. At 44.1 kHz, 26-channel S32_LE, capture
  produces 4,586,400 bytes/second; this host's 65,536-byte pipe fills in 14.289 ms while the
  512-frame hardware buffer spans only 11.610 ms. The failed extractor's 66,560-byte final read is
  consistent with that startup-pipe ceiling. The harness now launches the extractor first, waits
  for an explicit readiness byte over a dedicated file descriptor, and only then starts `arecord`
  with its output connected to the already-draining pipe. Focused `py_compile`, the complete
  analyzer fixtures, isolated 26-channel extraction, and the new readiness-handshake fixture pass;
  `git diff --check` is clean. Corrected script SHA-256 is
  `d42b8cb58646683e0d0a853c88a7cb27ac3b1c66932e772948cf11c652cd9c7b`. This is an offline harness
  correction, not live ALSA evidence. The driver's active-page DMA-table and late-ring-wrap logic
  are unchanged. Any validating direct-ALSA invocation is a fresh live gate requiring separate
  exact approval.
- **Readiness-corrected direct-ALSA arm runs cleanly, then both helpers xrun, 2026-08-18:** the
  separately approved exact invocation admitted native 44.1-kHz/26-channel/S32_LE/128/512 duplex
  geometry and analyzed 576 blocks over 53.879 seconds before failing closed. The startup overrun
  did not recur. All admitted blocks had zero phase delta and produced zero continuity events,
  loss episodes, or recoveries; absolute correlation stayed at or above 0.98082945, RMS stayed
  -27.2228 to -27.1022 dBFS, and maximum peak was -16.8142 dBFS. Across telemetry from 0.536 to
  53.715 seconds, capture and playback hardware pointers each advanced 2,345,311 frames while IRQ
  count advanced 18,323, matching the native rate and period cadence. Capture/playback `avail_max`
  nevertheless rose to 483/494 of the 512-frame buffer, after which `arecord` reported one fatal
  overrun and `aplay` one fatal underrun; the analyzer then observed capture EOF. PipeWire kept the
  exact source and sink suspended at zero errors. Both PCMs closed, all three audio services and
  the complete 13/26 graph survived, and bounded kernel and user-audio logs contained no matching
  fault. This is positive direct-ALSA duplex-xrun evidence and proves PipeWire is not necessary for
  that terminal failure, but no direct-ALSA continuity event preceded it, so it does not reproduce
  or exclude the PipeWire arm's four sequence-displacement events. Exact cadence and empty fault
  logs remain absent positive driver-fault evidence. Immutable evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-3`; summary/events/`pw-top` SHA-256 are
  `513b849450644d2cf7888c1303ef15c6e6567fcde0f485fd11296077245f79a2`,
  `bb312953e384686fe013f36f752862f1fca37b7c911995e6dc2e26d2e00ba622`, and
  `2c09420dba90e3143ff2305b555834f756e14c0dd04bb6586cda5b18ced1f416`. The invocation is consumed;
  do not retry or repair under this authority.
- **Direct-ALSA helper starvation is isolated from analyzer cost and instrumented offline,
  2026-08-18:** steady-state phase analysis takes 1.211 ms median and 1.967 ms p95 per 92.880-ms
  audio block, about 1.3% and 2.1% of real time. The 117.967-ms measured maximum is the initial
  full-reference acquisition; the live arm recorded no later global search, and the old mono pipe
  already held about 371.5 ms. Analyzer throughput therefore does not explain the terminal xrun.
  The gate execution context instead has `RLIMIT_RTPRIO=0`; `aplay`, `arecord`, and Python have no
  scheduling capabilities and inherit `SCHED_OTHER`, while the current PipeWire data loops receive
  `SCHED_RR/20` through RTKit. The old raw transport pipes held only 65,536 bytes, or 14.289 ms at
  26-channel S32_LE. The harness now fail-closes unless playback input, raw capture, and extracted
  mono pipes each reach 1,048,576 bytes, providing about 228.6 ms on each raw edge and 5.94 seconds
  on the mono edge without changing the 512-frame ALSA buffer. Every direct-ALSA telemetry sample
  now records policy, priority, nice level, context switches, runtime, scheduler wait time, and
  timeslices for both helpers, feeder, and extractor. Focused `py_compile`, all analyzer/extractor
  fixtures, 1-MiB pipe proof, scheduling-telemetry fixture, and `git diff --check` pass. Corrected
  script SHA-256 is `fe7a9f0b904e87585f0add1c35dce40703237c5e211139c24f39aa3a565aa634`.
  This removes bounded harness-pipe backpressure and adds the missing discriminator; it does not
  promote any process, change the driver, or prove why the two helpers xrunned. RTKit promotion is
  deferred unless a separately authorized run's new wait telemetry positively identifies helper
  scheduling starvation.
- **Enlarged-pipe direct-ALSA arm isolates a later capture-only overrun, 2026-08-18:** the exact
  separately approved invocation confirmed all three 1-MiB pipes and admitted native
  44.1-kHz/26-channel/S32_LE/128/512 duplex geometry. It analyzed 999 blocks over 93.181 seconds
  with zero phase delta, continuity events, loss episodes, or recoveries; absolute correlation
  stayed at or above 0.98110169, RMS stayed -27.2492 to -27.0798 dBFS, and maximum peak was
  -16.8142 dBFS. Across telemetry from 0.566 to 92.554 seconds, capture/playback pointers advanced
  4,056,916/4,056,907 frames and IRQ count advanced 31,695 at exact cadence. All four helper
  processes were `SCHED_OTHER` at nice +6. The largest sampled one-second scheduler-wait increments
  were 7.355 ms for `arecord`, 7.545 ms for `aplay`, 2.093 ms for the extractor, and 1.667 ms for
  the feeder; none positively explains an 11.610-ms-buffer xrun before the final sample. Capture
  `avail_max` peaked at 380 and playback at 326 frames, both below the prior arm's 483/494. After
  the last telemetry sample, `arecord` reported one fatal overrun and capture EOF stopped the
  analyzer. `aplay` reported only an interrupted write during fail-closed teardown, not an
  underrun. PipeWire nodes stayed suspended at zero errors; both PCMs closed; all services and the
  13/26 graph survived; and bounded kernel/user logs contained no matching fault. The 1-MiB pipes
  therefore removed the reproduced playback-side helper failure in this arm but did not prevent a
  later direct-capture overrun. Because the terminal 0.627-second interval has no final scheduling
  snapshot, scheduler starvation is still unproven; exact cadence and empty logs remain absent
  positive driver-fault evidence. Evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-4`; summary/events/`pw-top` SHA-256 are
  `de872effeb0add562509f572a90b22dda02751144a028ea408b5d743ea76fb11`,
  `f701b6a8d5331c8a4cfbbd5c852fb6655e35be4df981c262d3775d44bae6df9e`, and
  `6de43a350a9f585cca13f73bc32ebe5a193b111b50cd3ff955653279c14c4870`. The invocation is consumed;
  do not retry, add RTKit promotion, or repair terminal telemetry under this gate.
- **Terminal evidence is now captured before helper reaping, offline 2026-08-18:** process
  supervision now uses Linux `waitid(..., WNOWAIT)` instead of polling or reaping helpers during
  the run. On analyzer failure, `events.jsonl` receives one `terminal_snapshot` before teardown,
  containing the volatile playback/capture ALSA status and hardware parameters (or explicit
  closed/unavailable state), any still-exposed pointers, IRQ count, each helper's final process
  state, scheduler policy, context-switch counts, runtime,
  scheduler wait, timeslices, and non-reaped child-exit status. A later `teardown_complete` record
  and summary return codes distinguish initiating exits from teardown-induced interruption. The
  offline self-test proves an exited fixture remains a readable zombie until explicitly reaped;
  focused `py_compile`, the complete analyzer/extractor/pipe/scheduler suite, and
  `git diff --check` pass. Script SHA-256 is
  `d8e28c0d78ba196006ca600ec88cc8606c72294795055f563e3c7ad90e751eb0`. This closes the missing
  final scheduler/exit-order seam; it cannot reconstruct an ALSA pointer after a helper has already
  closed its PCM. It supplies no new live ALSA result, changes no scheduling policy or driver path,
  and does not authorize another run.
- **Terminal-evidence direct-ALSA arm proves aligned scheduler contention with no positive driver fault,
  2026-08-18:** the separately approved exact invocation was consumed and failed closed after 452
  clean blocks/42.431 seconds at native 44.1-kHz/26-channel/S32_LE/128/512 geometry with all three
  1-MiB pipes. Phase delta and continuity/loss/recovery counts stayed zero; minimum absolute
  correlation was 0.98068229, telemetry RMS stayed -27.2139 to -27.1011 dBFS, and maximum peak was
  -16.8108 dBFS. At 42.419923 seconds the new terminal snapshot found `arecord` already an
  unreaped zombie with exit 1 after its sole fatal overrun while `aplay`, the feeder, extractor,
  and `pw-top` were still running. Capture had closed; playback remained `RUNNING` at exact
  geometry and later exited 0 in teardown with empty stderr. The extractor's exit 1 followed the
  capture EOF and partial final raw block, so it is downstream evidence rather than another xrun.
  All helpers were `SCHED_OTHER` at nice 0. The largest sampled one-second cumulative runqueue-wait
  increases were 160.109 ms for `arecord`, 247.997 ms for `aplay`, 23.022 ms for the extractor, and
  10.114 ms for the feeder; from the last telemetry point to the terminal snapshot they increased
  another 103.170/232.168 ms for capture/playback. This is positive severe host scheduler-
  contention evidence aligned with the overrun. Linux `schedstat` wait is cumulative across many
  dispatches, however, so it does not prove one contiguous scheduling stall exceeded the 11.610-ms
  hardware buffer or alone establish scheduling as the cause. Across 0.510 to 42.420 seconds IRQ
  cadence was 344.548/s versus 344.531/s expected and playback pointer cadence was 44,101.6
  frames/s; the driver logged exactly 14,615 normal run-window interrupts and only normal DMA
  start/stop. PipeWire nodes stayed suspended at zero errors, both PCMs closed afterward, all three
  services and endpoints 186/77 survived, and bounded kernel/user audio logs contained no driver
  fault. Stable cadence and empty fault logs remain absent positive driver-fault evidence. Evidence
  is under `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-5`; summary/events/`pw-top`
  SHA-256 are `2d8d6bc7cabb92b8f90cf5a75f7a5bf4ff37c88dc11096098b26f5311ba91056`,
  `d432b3619a3939c2e511a7d93d77b4ea5147daa0cbfb3f3f90e739a6064ea4c9`, and
  `c761358453fcae5e25b77580762c99be3826f71a6c45242935c1141a86b987c0`. The gate is
  `consumed_failed`; do not retry it. The next discriminator is a separately designed and approved
  RTKit promotion A/B that preserves exact transport and captures maximum per-dispatch latency or
  equivalent trace evidence; no promotion is authorized by this result alone.
- **RTKit direct-helper A/B is prepared offline and fail-closed, 2026-08-18:** host introspection
  confirms `org.freedesktop.RealtimeKit1` is active, exposes
  `MakeThreadRealtimeWithPID(process, thread, priority)`, caps real-time priority at 20, and requires
  a 200,000-us maximum RT runtime. The harness now accepts the opt-in direct-ALSA-only
  `--rtkit-helper-priority 20` seam. Before exec it applies exactly that `RLIMIT_RTTIME` plus
  `SCHED_RESET_ON_FORK` to `aplay` and `arecord`, requests RR/20 for only their main threads, proves
  the resulting policy immediately and every telemetry interval, and records both promotion
  receipts. Feeder and extractor remain `SCHED_OTHER` controls; helper exit removes the policy, and
  no RTKit reset, service change, driver change, or geometry change is performed. The offline
  fixture proves the RTTIME/reset prerequisites after exec, the exact bounded D-Bus command, valid
  RR/20 policy acceptance, and rejection of RTKit mode with PipeWire. `perf` is absent and this
  kernel's per-process `sched` view exposes no maximum individual wait, so cumulative `schedstat`
  wait remains supporting contention evidence rather than a per-dispatch latency measurement.
  Focused `py_compile`, the complete offline suite, CLI validation, and `git diff --check` pass;
  script SHA-256 is `84b2755a39ff931b474270f92f574d42c53179f0168da87165c8f250b5a04a67`.
  This is offline readiness only. No RTKit request or audio open occurred, and a live A/B remains a
  fresh one-shot gate requiring approval of its exact command and new output path.
- **RTKit A/B is rejected by simultaneous policy loss before the comparison window, 2026-08-18:**
  the separately approved invocation was consumed once. RTKit returned success for both bounded
  `MakeThreadRealtimeWithPID` requests, and the harness proved `aplay` and `arecord` were RR/20 with
  reset-on-fork from pipeline admission through the 13.779-second telemetry sample. During that
  admitted window, it analyzed 156 blocks with zero phase delta, continuity events, loss episodes,
  or recoveries; minimum absolute correlation was 0.98118544, telemetry RMS stayed -27.1882 to
  -27.1276 dBFS, and maximum peak was -16.8122 dBFS. Cumulative RT runqueue wait remained only
  18,718 ns for playback and 4,286 ns for capture, while `avail_max` peaked at 145/262 frames.
  At 14.802 seconds both helpers were still alive and both PCMs remained `RUNNING` at exact
  44.1-kHz/26-channel/S32_LE/128/512 geometry, but both policies had simultaneously become
  `SCHED_OTHER`/priority 0 with reset-on-fork cleared. The harness therefore stopped on policy
  drift, before any xrun: `arecord` stderr is empty, `aplay` contains only the teardown-induced
  interrupted write, and the extractor's partial-block failure is downstream teardown evidence.
  RTKit's journal confirms both initial promotions but contains no demotion/reset marker. The
  daemon uses the default 5,000-ms canary and 10,000-ms watchdog intervals, which is temporally
  consistent with the policy loss, but a watchdog or external `ResetKnown`/`ResetAll` remains an
  inference rather than an observed cause. The helpers' total recorded runtime was below the
  200,000-us RTTIME bound, so the evidence does not support RTTIME exhaustion. From the first sample
  to terminal, capture/playback pointers advanced identically at 44,101 frames/s and IRQ cadence
  was 344.55/s versus 344.531/s expected; the driver logged 5,099 normal interrupts and only normal
  DMA start/stop. PipeWire nodes stayed suspended at zero errors, both PCMs closed afterward, all
  four services including RTKit and endpoints 186/77 survived, and no driver fault appeared.
  Evidence is under `/tmp/quantum2626-loopback-direct-alsa-rtkit-calibration-20260818-6`;
  summary/events/`pw-top` SHA-256 are
  `dd396b595ceb68ee31367ae9d8f80908891109b428f483f0bca332ac420b2295`,
  `72daa03cb471f8ae014198889682bd3b620dd6ef9ff71a0fb68d4b1f4c957433`, and
  `54acc73793cfda91306f6f2309259cbcd45fc64ff11fc5e58b2cff732ce2c09e`. The gate is
  `consumed_failed`; do not retry, reset RTKit, change its service, or treat the 13.8-second clean
  prefix as the requested five-minute A/B. The next checkpoint is bounded read-only attribution of
  the simultaneous demotion or a separately designed non-RTKit scheduling mechanism, not another
  live invocation under this authority.
- **Read-only attribution identifies System76 Scheduler as the RTKit-policy demoter with high
  confidence, 2026-08-18:** the active override remains exact SHA-256
  `48f1743e3db8b2adeb110b41cd3f41a17bb11378bfd697ac62696b30d68ee677` and enables real-time
  `execsnoop` assignment. Its explicit exceptions protect only `/usr/bin/pipewire` and
  `/usr/bin/pipewire-pulse`; `aplay` and `arecord` are not excepted. The override itself records the
  already source-proven behavior: exact installed System76 Scheduler commit `8651bbf` defaults an
  omitted `sched=` property to `SCHED_OTHER`, walks every task/thread, and invokes
  `sched_setscheduler()` during profile assignment. `execsnoop` handles newly executed processes,
  distinct from the 60-second periodic refresh, matching the two helpers created together and then
  normalized together after their successful RTKit grants. The service has been continuously
  active with its `pipewire`/execsnoop worker, while RTKit emitted neither its compiled-in
  `The canary thread is apparently starving` nor `Demoting known real-time threads`/per-thread
  success markers during the gate. `/usr/bin/aplay` and `/usr/bin/arecord` are the same exact ELF,
  and neither that binary nor `libasound.so.2` imports `sched_setscheduler`, `sched_setparam`,
  `setpriority`, or `setrlimit`; this is absent helper/library self-demotion evidence, not proof
  against a direct syscall. The RTKit helper runtimes also stayed below the 200-ms bound. Together,
  active config/source semantics plus exact simultaneous policy loss positively identify the
  System76 assignment path as the high-confidence demoter; the precise setter syscall was not
  traced, so keep that final link inferred rather than claim an audited call. No process policy,
  config, service, module, endpoint, or device state changed during attribution. Any later RTKit
  audio A/B first requires a separate privileged, reversible gate to except exactly
  `/usr/bin/aplay` and `/usr/bin/arecord` and reload only System76 Scheduler, followed by read-back;
  the audio run remains another independently approved gate.
- **System76 ALSA-helper exception gate V1 is sealed offline and waiting for approval, 2026-08-18:**
  controller `/tmp/quantum2626-task002-system76-helper-exceptions-v1.sh` (SHA-256
  `2289ed59deb78e55578d7366d862be300cfb9c90ab7af52ab7d15e60b20f30f6`) and gate packet
  `/tmp/TASK-002-SYSTEM76-ALSA-HELPER-EXCEPTIONS-V1.gate.md` (SHA-256
  `2675a90eb3bb871298d355d4d40e22d70ca95a3f787485fb58cc13eeea077f93`) are sealed. The read-only
  preflight passes against config `48f1743e...ee677`, unit `e97648c1...fb88d`, daemon
  `77889453...7775`, and the active/running reload-capable service. The only candidate delta adds
  exact exceptions for `/usr/bin/aplay` and `/usr/bin/arecord`; its expected config hash is
  `01fe04b46a646a4e6831cbc3823cbcf1ebe05b48ac65a9e68b4454d6459f0846`. Execution would first
  retain a root-only byte-exact backup, atomically install that candidate, invoke only
  `systemctl reload com.system76.Scheduler.service` once, and require successful reload plus
  unchanged daemon PID/active-enter timestamp and exact config/count read-back. It performs no
  automatic rollback: any restoration and second reload require a distinct recovery gate. No
  config, service, audio, module, endpoint, device, or process-policy state changed while sealing;
  attempt count remains zero and authority is unconsumed. Do not execute without fresh exact gate
  approval, and keep the later RTKit direct-ALSA A/B separately gated.
- **System76 ALSA-helper exception gate V1 is consumed before controller execution, 2026-08-18:**
  the exact host-view preflight passed immediately before invocation and reconfirmed the sealed
  artifact, checkout, config, unit, daemon, service, exception-count, target-hash, and absent-path
  anchors. The approved command was then invoked exactly once, but `sudo` exited 1 because it
  required a terminal and could not read a password; the controller never started. Bounded
  read-back proves `/etc/system76-scheduler/config.kdl` remains the exact before bytes
  (`48f1743e...ee677`), `root:root` mode 0644, with exception counts `pipewire=1`,
  `pipewire-pulse=1`, `aplay=0`, and `arecord=0`. The sealed target (`01fe04b4...846`) was not
  installed, both the task backup/receipt path and active temporary config path remain absent, and
  the scheduler unit (`e97648c1...f88d`), daemon (`77889453...7775`), and loaded/active/running,
  reload-capable service state remain exact. The existing `ReloadResult=success` is not attributable
  to this failed invocation. Classify the gate as `consumed_failed`, with attempt count one and no
  retry or recovery authority. No repository, config, service, audio, module, endpoint, device, or
  process-policy state changed. Never replay or reconstruct V1; any helper-exception recovery and
  the later RTKit direct-ALSA A/B require new, separately sealed and approved gates.
- **System76 ALSA-helper exception gate V2 is sealed with desktop authentication, 2026-08-18:**
  after approval to advance a fresh successor boundary, controller
  `/tmp/quantum2626-task002-system76-helper-exceptions-v2.sh` (SHA-256
  `ec6485e4ae7db80165d571d287b891c219233f4c06bfb771d8c67ae246270cce`) and gate packet
  `/tmp/TASK-002-SYSTEM76-ALSA-HELPER-EXCEPTIONS-V2.gate.md` (SHA-256
  `07304f4a24fda76342b4ae47be577fbf9a4d25d9fc9e78ddca32c2d8829efc84`) were sealed with fresh
  V2 backup/temp paths. The only candidate delta and target hash remain the two exact helper
  exceptions and `01fe04b4...f0846`. V2 replaces V1's non-interactive `sudo` entry with exact
  invocation
  `/usr/bin/pkexec /bin/bash /tmp/quantum2626-task002-system76-helper-exceptions-v2.sh --execute`;
  host inspection proves
  `pkexec` SHA-256 `441f1eb9...2dbf`, root-owned mode 4755, and administrator authentication through
  `org.freedesktop.policykit.exec`. The exact host-view controller preflight passes with the before
  config, unit, daemon, service, exception counts, target digest, checkout, and absent V2 paths
  intact. Attempt count remains zero and authority is unconsumed. Because the concrete PolicyKit
  invocation was sealed only after the boundary-level approval, exact one-shot approval and task
  creation are still required before execution; no fallback, retry, repair, audio run, or recovery
  is authorized.
- **System76 ALSA-helper exception gate V2 installed the target but is consumed-failed on independent
  artifact read-back, 2026-08-18:** the exact approved PolicyKit invocation began once; the controller
  exited 0 and reported completion after checking the backup and candidate, installed config, reload
  result, service-process continuity, active-enter continuity, unit, and daemon anchors. Independent
  bounded read-back proves `/etc/system76-scheduler/config.kdl` is the exact target
  (`01fe04b46a646a4e6831cbc3823cbcf1ebe05b48ac65a9e68b4454d6459f0846`), `root:root` mode 0644,
  with exception counts `pipewire=1`, `pipewire-pulse=1`, `aplay=1`, and `arecord=1`. The scheduler
  remains loaded, active, running, and reload-capable with `ReloadResult=success`; unit
  (`e97648c1...f88d`) and daemon (`77889453...7775`) hashes are unchanged, and the active temporary
  config path is absent. The V2 backup directory exists as `root:root` mode 0700. The unprivileged
  independent reader could not traverse it, so presence and hashes for its backup, candidate, and
  receipt remain unknown; descendant `absent` results are permission projections, not absence
  evidence. Because that required independent read-back is incomplete after the single invocation,
  classify V2 as `consumed_failed` despite positive installed-config and controller proof. Never
  replay V1 or V2, use privileged access to fill the missing hashes, or infer retry, repair, cleanup,
  or rollback authority. The next RTKit direct-ALSA comparison remains a fresh, separately sealed
  and explicitly approved one-shot audio gate; none is prepared or entered by this admission.
- **RTKit direct-ALSA comparison after helper exceptions is sealed offline, 2026-08-18:** gate
  `TASK-002-DIRECT-ALSA-RTKIT-AFTER-EXCEPTIONS-V1` repeats the spent `-6` arm's exact five-minute
  native 44.1-kHz/26-channel/S32_LE/128/512, -30-dBFS, direct channel-3 physical-return, 1-MiB-pipe,
  and helper RR/20 conditions with fresh output
  `/tmp/quantum2626-loopback-direct-alsa-rtkit-calibration-20260818-7`. The intended causal
  prerequisite delta is only the now-installed System76 Scheduler exceptions for `/usr/bin/aplay`
  and `/usr/bin/arecord`. Preflight
  `/tmp/quantum2626-task002-direct-alsa-rtkit-after-exceptions-v1-preflight.sh` (SHA-256
  `84197a85996ea91c6550d00a0d3d0a46eaa2d0980a7526a6a8101f28e8c7fb3a`) passes against the exact
  checkout/harness, helper-exception config, active-page module, installed UCM/WirePlumber defaults,
  13/26 graph and selected endpoints, active services, RTKit 20/200000 limits, closed PCMs, passing
  offline self-test, and absent output path. Gate packet
  `/tmp/TASK-002-DIRECT-ALSA-RTKIT-AFTER-EXCEPTIONS-V1.gate.md` has SHA-256
  `7e8a9013edd4037fffd4c0471fabf663aaa3defce21cd7c77f2451d836b0206e`. Attempt count is zero and
  authority is unconsumed. No audio or RTKit request occurred. Execution still requires fresh exact
  approval that also confirms Output 3 remains patched to the selected Input 3 return with direct
  monitoring off; preparation approval is not invocation authority. Never replay `-6`, V1/V2
  scheduler gates, or this new gate after its first process begins.
- **Post-exception RTKit direct-ALSA comparison completes cleanly, 2026-08-18:** the separately
  authorized gate `TASK-002-DIRECT-ALSA-RTKIT-AFTER-EXCEPTIONS-V1` was invoked exactly once and is
  now consumed. It completed the intended 300.05-second comparison at exact native
  44.1-kHz/26-channel/S32_LE/128/512 duplex geometry, analyzing 3,227 blocks with zero continuity
  events, loss episodes, recoveries, or lost blocks. Minimum absolute correlation was 0.9807085,
  telemetry RMS remained -27.2806 to -27.0435 dBFS, maximum peak was -16.8119 dBFS, and phase delta
  remained zero with every telemetry sample locked. RTKit returned success for both bounded
  promotions. From pipeline admission through all 294 telemetry points, all 295 scheduler samples
  kept `aplay` and `arecord` at `SCHED_RR/20` with reset-on-fork true, while feeder and extractor
  remained `SCHED_OTHER/0` controls. Maximum cumulative sampled scheduler wait was 3,928,813 ns for
  playback, 3,099,950 ns for capture, 6,759,159 ns for the feeder, and 7,754,265 ns for the
  extractor. Both PCMs were `RUNNING` throughout; `avail_max` peaked at 180/275 frames. Pointer
  deltas matched at about 44,102.066 frames/s, and IRQ cadence was 344.545/s versus 344.531/s
  expected. Neither ALSA helper reported an xrun; helper and `pw-top` stderr were empty. The
  capture-helper exit 1, extractor SIGINT, and short final block followed the normal duration stop
  and are teardown evidence, not run-window failures. Kernel evidence contains only normal DMA
  prepare/start/stop, with no positive driver or general fault marker. Post-run, both PCMs were
  closed, helpers were absent, the services and 13/26 graph survived, and the exact scheduler,
  module, UCM, WirePlumber, harness, and checkout anchors were unchanged. Evidence is immutable
  under `/tmp/quantum2626-loopback-direct-alsa-rtkit-calibration-20260818-7`; summary/events/`pw-top`
  SHA-256 are `020af763b1828d667c1ed832a3958d07084c87ded9128a6ad0ff25a00a45d796`,
  `abbdf4e77584c2940907559fba49c8c7e6007ea38bd9bd0f734818a9260b1eef`, and
  `f0c419a700677cc0e8206aa83ab79334da3084cb16f5171e5a6643ef6b344eca`.
  Compared with spent arm `-6`, which lost both successful RTKit policies simultaneously at 14.802
  seconds before its comparison window, the intended prerequisite delta was the installed exact
  System76 Scheduler exceptions for `/usr/bin/aplay` and `/usr/bin/arecord`. The paired result
  supports those exceptions as the change that prevented the observed demotion and permitted this
  clean five-minute RR/20 run. Keep the precise untraced System76 setter call, permanent elimination
  of scheduling failures, and general audible/PipeWire crackle resolution classified as inferred
  or unproven. The event-free captured sequence covers the reported direct Line Out 3 -> Line Input
  3 analog return at its preserved gain; it excludes the earlier Digimax/ADAT return confound but
  does not validate other physical outputs, inputs, digital paths, or subjective listening. Empty
  fault logs are absent positive driver-fault evidence, not proof that the driver cannot contribute
  elsewhere. Never replay `-6` or `-7`, modify or clean the `-7` artifacts, or infer authority for
  another live, privileged, recovery, or publication action.
- Design a separately bounded migration from the legacy direct dshare/dsnoop topology to upstream
  UCM `SplitPCM`, requiring WirePlumber 0.5.8 or newer plus ALSA UCM/alsa-lib new enough to describe
  all 26 hardware channels. Do not replace distribution audio packages or vendor partial macros as
  an incidental buffer-test step.
- **Completed recovery boundary:** exact configuration rollback and a later persistent
  WirePlumber-only recovery restored the 13/26 endpoint registry without a reboot. Do not run
  another candidate or restart while the user resumes ordinary work. Revalidate audible playback
  and error counters only when the user explicitly resumes testing.
- If 512 activates but crackles remain after the System76 Scheduler refresh, classify the buffer
  candidate as insufficient and return to the separately scoped scheduling seam; do not hide that
  conflict with a larger unmeasured buffer.

## Closure Summary

Completed; objective state is `completed`. The completed `-7` gate is admitted without replay, its
authority is consumed, and the scheduling discriminator is closed: the exact helper exceptions
preserved RR/20 through a clean five-minute direct-ALSA run where spent arm `-6` lost both policies
at 14.802 seconds. Repeatable performance evidence and the conservative defaults are now
technically grounded: preserve native 44.1-kHz/26-channel/S32_LE/128/512 geometry, playback
`slowptr true`, 256-frame headroom, the active-page DMA-table lifetime correction, and the existing
PipeWire plus helper System76 exceptions. The bounded live claims above were separately approved
and proven, and both canonical task-owned notes are current. No successor gate has been prepared or
entered; broader PipeWire, audible, long-duration, or other physical-route claims are deferred
outside this acceptance and require fresh authority.
