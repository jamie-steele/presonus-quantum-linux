# TASK-002 Release Performance Hardening

## Status

The managed-buffer driver correction is installed, loaded, and live-proven at 128-frame periods
with a 512-frame hardware buffer. Ordinary Firefox playback is materially improved and the user
calls it the best result so far, but still hears occasional crackle. The Quantum PipeWire node has
four graph errors while Firefox has zero; no settled kernel xrun, timeout, or fault marker appears.
PipeWire's data loop is currently `SCHED_OTHER` despite its realtime module, with the active
System76 Scheduler integration still controlling policy. Exact installed source plus upstream
issue research confirms this is a general low-latency audio conflict: System76 applies one policy
to every thread, while PipeWire expects only its data-processing threads to run realtime. Keep
128/512 as the best measured buffer candidate, but classify no-crackle acceptance as incomplete
and return to the separately bounded scheduling seam before changing geometry again.

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

Open.
