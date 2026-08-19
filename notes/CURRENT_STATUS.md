# Quantum 2626 Linux Driver — Current Status

**Last updated:** 2026-08-18
**TL;DR:** Static analysis of the vendor's macOS DriverKit extension recovered the TCI mailbox,
audio page tables, IRQ contract, rate setter, and rate-dependent channel order. The installed Linux
module reaches the solid-blue ready state and implements native 44.1/48/88.2/96/176.4/192 kHz
selection with 26/18/8-channel profiles. Direct and ordinary Firefox playback at 44.1 kHz are
live-proven at 26-channel S32_LE with 128-frame periods and a 512-frame buffer. Playback-only
`slowptr true`, 256 frames of PipeWire headroom, and corrected realtime scheduling reduce the
intermittent crackle. A temporary 2-us CPU-latency QoS request then produced the first user-observed
pop-free interval and cleanest playback so far. The corresponding driver candidate builds cleanly
and is now installed and loaded with the complete desktop endpoint graph restored; longer audible
playback immediately reproduced crackle. The 2-us request is active and suppresses deep idle, while
geometry, IRQ cadence, realtime scheduling, and PipeWire counters remain clean. The previously
untested `msbits=24` metadata became the leading regression variable. An exact QoS-only candidate is
now installed and loaded with PipeWire returned to 32 resolution bits; audible acceptance is
immediately excellent and clean, with the active stream retaining zero graph errors, exact IRQ
cadence, realtime scheduling, and suppressed deep idle. A later NeuralRack test isolated a distinct
native-44.1 duplex lifecycle defect: capture-first startup silenced playback, capture teardown
restored crackling playback, and a complete playback-only close/reopen restored clean audio.
The refined driver candidate now keeps both DMA buffers stable across one-sided lifecycle changes,
handles ALSA synchronized starts, and aligns an independent late direction at the next ring wrap.
Its exact build is installed and loaded, and playback returned at native 44.1 kHz/128/512. Desktop
recovery is incomplete: 13 sinks returned, but WirePlumber aborted one audio adapter and currently
publishes none of the 26 capture sources. A later approved WirePlumber-only restart entered the
known pending-linkable wedge. A separately approved restart of all five audio units restored
registry responsiveness, but the graph remains at 13 sinks and zero sources. Playback is running
at native 44.1 kHz/128/512 and capture is closed. A compatibility A/B removed only ALSA
synchronized-start metadata and grouped trigger completion while preserving the shared-buffer and
wrap-alignment design. It is now installed and loaded, but activation again produced 13 sinks and
zero sources, rejecting synchronized-start handling as the cause. Capture discovery also emitted a
DMAR DMA-write fault from the Quantum PCI function to address zero. Playback remains running at
native 44.1 kHz/128/512 and capture is closed. The source now keeps the fixed ALSA buffers and their
maximum-sized DMA page tables valid across `hw_free`, rate changes, and rapid discovery cycles,
removing the observed zero-address teardown window while leaving active 128/512 geometry unchanged.
The candidate builds cleanly and is now installed and loaded. Its rapid capture-discovery storm no
longer produced a DMAR/IOMMU, stop, or page-table fault, validating that narrow safety correction,
but WirePlumber again destroyed the capture adapter and the stable graph remains 13 sinks/0 sources.
Playback is RUNNING at native 44.1 kHz/128/512 and capture is closed. Stop live retries and diagnose
the remaining adapter/probe-lifecycle failure offline. User listening also reports a new weird
static artifact. Exact geometry, IRQ cadence, and fault logs remain clean, isolating the new
maximum-buffer page-table extent as the leading playback regression variable. Reject this runtime
candidate. The source now retains fixed coherent table allocations while populating and linking only
active-buffer pages. The corrected artifact builds cleanly and is installed and loaded. Its exact
activation loaded the
active-page artifact and restarted all five audio units. Playback returned at native
44.1 kHz/128/512 with no DMA/IOMMU, stop, or page-table fault. Initial user listening reports
“sounds pretty good now,” followed by sustained ordinary gaming use with “no pops at all” and
“super stable.” Neither the maximum-map static regression nor earlier intermittent pops reproduced.
The activation controller observed 13 sinks/0 sources at its bounded 10-second checkpoint, but a
later direct read-only PipeWire snapshot after a longer settle found the complete 13-sink/26-source
graph. Mic / Instrument Input 1 is correctly published as a suspended mono source; suspension is
normal until a client links it. Capture remains closed, so native-44.1 duplex is not yet validated.
Direct capture, physical headphone-left/right output, and bounded PipeWire duplex remain
live-proven at 48 kHz; native-44.1 duplex is now observed failing. Higher rates, mixer controls,
MIDI, hot removal, and physical S/PDIF/ADAT routing remain unproven. A later separately approved
direct-ALSA A/B held helper RR/20 scheduling for five minutes at native 44.1-kHz/26-channel
S32_LE/128/512 duplex geometry with zero xruns or captured continuity events. Paired with the prior
14.802-second helper demotion, this supports retaining the exact System76 `aplay`/`arecord`
exceptions as conservative host defaults; it does not establish PipeWire or subjective listening
acceptance.

## Evidence Labels

- **Observed Linux:** directly measured on this host/device.
- **Static analysis:** recovered from the x86_64 slice of the macOS DriverKit extension.
- **Implemented, unverified:** present in the Linux driver but not yet confirmed on hardware.
- **Hypothesis:** still requires static corroboration or a bounded live test.

## Current Host Baseline

- **Observed Linux:** PCI function `09:00.0` is `1c67:0104` and is bound to `snd_quantum2626`.
- **Observed Linux:** the running kernel is `7.0.11-76070011-generic` on x86_64.
- **Observed Linux:** ALSA card `P2626` exposes playback and capture device 0 on IRQ 213.
- **Observed Linux:** the installed and loaded module SHA-256 is
  `d54f2bf411430c5ed350b5999d07795e9d7de6aa3801332c9e0d97152fa9b45e`, srcversion
  `D1D19FA61C85B05A46E2A01`.
- **Observed Linux:** all five user audio units report active and the PipeWire registry responds.
  After a longer settle than the activation controller allowed, the active-page candidate publishes
  all 13 Quantum sinks and 26 Quantum sources. Playback runs at native 44.1 kHz/128/512; capture is
  closed.
- **Observed Linux:** Secure Boot is disabled, so an unsigned local test module is loadable after
  local sudo authentication.
- **Observed Linux:** a later read-only desktop inspection confirmed the active Main endpoint was
  still the validated S32_LE, 48 kHz sink, but PipeWire was driving its graph at 44.1 kHz with a
  64-frame quantum. The sink error counter increased from 117 to 118 during a short observation;
  the active Line Input 5 source also showed 19 accumulated errors. This matches the user's
  low-bitrate-like audible artifact and points to graph resampling/underrun pressure rather than a
  reduced-bit-depth Quantum profile. No runtime setting was changed during that inspection.
- **Observed Linux:** with explicit user approval, temporary PipeWire metadata overrides forced the
  graph to 48 kHz and 128 frames, matching the Quantum endpoint and hardware period. Renegotiation
  raised the cumulative Main error counter from 118 to 123 and Line Input 5 from 19 to 20 once;
  afterward Main, the Brave stream, and Line Input 5 all reported 48 kHz, Main reported a 128-frame
  quantum, and both error counters remained stable throughout the post-change sample. The user
  reported that this forced live-renegotiated session still sounded bad.
- **Observed Linux and user-observed hardware:** an explicitly requested restart of the user
  PipeWire, PipeWire Pulse, and WirePlumber services cleared the temporary overrides and rebuilt the
  graph without unloading the module or touching the interface. The Quantum endpoints returned,
  Main remained the default HiFi sink, and the user heard weird artifacts initially before playback
  resolved by itself. In the settled state Main ran at S32_LE, 48 kHz, and 128 frames with zero
  PipeWire errors throughout a 24-sample observation; both browser streams also reported 48 kHz.
  The hardware delivered 1,127 interrupts over approximately three seconds, consistent with the
  expected 375 interrupts per second. Line Input 5 independently ran a 44.1 kHz, 64-frame capture
  graph against its 48 kHz endpoint with zero errors. Because the artifact occurred immediately
  after forced metadata changes and a service restart, then resolved, it is currently classified as
  an intervention-induced transient rather than evidence of a persistent baseline playback defect.
- **Observed Linux:** a later untouched 256-frame control retained the exact tracked/installed UCM
  and loaded-module hashes, all 13 sinks and 26 sources, and RUNNING 48 kHz, 26-channel S32_LE ALSA
  playback/capture with 128-frame periods and 256-frame buffers. Across 24 PipeWire samples, Main
  remained at 48 kHz/128 frames with its cumulative error counter fixed at 16; Firefox stayed at
  14, and the active Line Input 5 device node stayed at 30 after the first sample. The GNOME
  Settings client rose from 124 to 126 early and then settled, so that client result is not treated
  as a device-node error. After the sampler's initial zero row, Main stayed at W/Q 0.00--0.03 and
  B/Q 0.00--0.01 while Line Input 5 stayed at W/Q 0.00--0.06 and B/Q 0.00. The device delivered
  1,125 IRQs in 3.004 seconds, approximately 374.5 per second, with no recent Quantum xrun, timeout,
  DMA, or fault marker. Main's configured soft volume was observed at 100%, a user-state change from
  the earlier 31% snapshot that this task did not make. No new audible verdict was collected during
  this read-only checkpoint.
- **Offline validation and observed Linux:** a 512-frame UCM candidate changes only both shared
  playback/capture `buffer_size` values, retains the 128-frame periods, stages cleanly, and parses
  as all 13 playback plus 26 capture PCMs. Its SHA-256 is
  `db4d09cbb70b8eefd40b45286a1c5b0a7d83171099b5abc0bcad143080c23192`. After exact installation
  and a restart limited to PipeWire, PipeWire Pulse, and WirePlumber, all 13 sinks and 26 sources
  returned but the geometry remained 128/256: PipeWire reported two periods, `/proc/asound`
  reported a 256-frame playback buffer, and every driver prepare logged `buffer_frames=256`. A new
  playback IPC segment had been created, so retained pre-restart shared memory did not explain the
  result. This was an ineffective UCM-only trial, not 512-frame performance evidence; capture,
  duplex, and audible comparison were skipped. Settled playback then held its cumulative error
  counter at 15 and delivered 3,753 IRQs in 10.009 seconds, approximately 375 per second. The
  user subsequently reported that the audio was "sounding really good." Since PipeWire,
  `/proc/asound`, and the driver log all still showed 128/256 frames, that audible result belongs to
  the clean post-restart 256-frame runtime rather than the ineffective 512-byte-file candidate. The
  installed file was subsequently restored to the preserved tracked 256-frame profile before the
  actual desktop period-count control is investigated.
- **Observed Linux and user-observed hardware:** while the same post-restart runtime was settled,
  the user heard audio go weird for about one second and then return to sounding great without an
  intervention at that moment. Playback remained RUNNING at 48 kHz, 26-channel S32_LE and 128/256
  frames. Main and Firefox had both advanced from 15 to 20 cumulative PipeWire errors; the nearest
  relevant user-service log in the bounded five-minute window was one PipeWire `out of buffers on
  port 0 2` entry at 23:17, while no matching Quantum kernel xrun, timeout, DMA, or fault marker
  appeared. The artifact time was not independently instrumented, so this is correlated window
  evidence rather than proof that the log line caused that exact audible event. Both counters then
  remained at 20 across 12 samples while playback sounded good again. This demonstrates a brief,
  self-resolving settled desktop-graph transient at the actual 256-frame runtime; it is neither
  persistent corruption nor evidence about a 512-frame buffer. Read-back afterward confirmed the
  installed file had been restored to the tracked 256-frame
  `3fa8c219efc6754e886b9637b6cf0d8b60d7628265c75509aa39cbe6ab464b29` bytes. The services had not
  been restarted again, so the transient occurred in the untouched settled session.
- **Observed Linux and user-observed hardware:** a subsequent rollback restart was limited to
  PipeWire, PipeWire Pulse, and WirePlumber after tracked, installed, and preserved UCM files all
  matched the original 256-frame hash. All 13 sinks and 26 sources returned, Main reopened RUNNING
  at 48 kHz, 26-channel S32_LE and 128/256 frames, and the user initially said it sounded "even
  better." Main then held zero errors across 24 samples and delivered 8,253 IRQs in 22.007 seconds,
  approximately 375 per second. The same bounded window subsequently recorded two PipeWire `out of
  buffers` events followed by three dshare `snd_pcm_mmap_commit` `Broken pipe` errors. An immediate
  snapshot showed Main at seven cumulative errors and Brave at six while ALSA playback remained
  RUNNING at 128/256, with no matching Quantum kernel xrun, timeout, DMA, or fault marker. The
  user then confirmed many audible pops and glitches plus a brief warbling interval. The rollback
  bytes and runtime geometry agree, but settled 256-frame desktop stability failed objectively and
  audibly: recurrent PipeWire buffer starvation is now a live hard stop. Capture/duplex was
  intentionally not reopened after the faults, and no further service, buffer, module, or hardware
  action was taken.
- **Observed Linux and source inspection:** the post-failure read-only scheduling diagnosis found a
  concrete desktop control conflict. RTKit granted the restarted PipeWire, PipeWire Pulse, and
  WirePlumber data-loop threads realtime priority 20 at 23:24:50, but those exact live threads later
  reported `SCHED_OTHER` and realtime priority zero. The first new `out of buffers` entry was at
  23:26:07; dshare `Broken pipe` entries began at 23:26:24. The host has no
  `/etc/system76-scheduler` override, and the active distribution configuration refreshes process
  assignments every 60 seconds. Exact installed-package source commit `8651bbf` shows that profiles
  without an explicit `sched=` default to `SCHED_OTHER` and that each refresh applies that policy
  to every thread; the active `sound-server` profile names PipeWire and PipeWire Pulse but omits
  `sched=`. PipeWire's own documentation says its data loop normally uses the realtime priority
  supplied by `module-rt`, with RTKit as the fallback when `RLIMIT_RTPRIO` is unavailable; the user
  services here have `LimitRTPRIO=0`. This establishes an active mechanism capable of undoing the
  successful RTKit grant. It is a high-confidence explanation for the observed loss of realtime
  scheduling and a likely contributor to the later starvation, but exact fault causation remains
  inferred because thread policy was not sampled at the instant of demotion. No UCM, service,
  module, or hardware state was changed during this diagnosis.
- **Observed Linux and user-observed hardware:** without a further intervention, the user then
  reported that playback sounded excellent. An immediate eight-sample read-only `pw-top` window
  held Main at 48 kHz/128 frames and 27 cumulative errors with W/Q 0.00--0.03 and B/Q 0.00--0.01;
  Brave also stayed fixed at 27 errors while requesting 1024 frames. The preceding two-minute
  journal contained one additional `out of buffers` entry at 23:35:44 but no dshare broken pipe.
  The recurrent fault is therefore bursty and self-recovering. Loss of realtime scheduling is a
  concrete risk mechanism, but it is not by itself sufficient to make every playback interval
  audibly bad.
- **Observed Linux:** a subsequent bounded scheduler-isolation checkpoint installed one exact
  additive System76 Scheduler exception file with SHA-256 `46eb1724...6e85`, then reloaded the
  scheduler and restarted only PipeWire, PipeWire Pulse, and WirePlumber. The three new data loops
  retained `SCHED_RR` priority 20, proving the exception prevented immediate demotion, but the
  PipeWire registry did not complete, no Quantum endpoints could be confirmed, and WirePlumber
  reported one pending linkable not activated after 20 seconds. The test stopped before its planned
  timing and audible samples.
- **Observed Linux:** exact rollback moved the installed exception to the task-owned
  `.failed-live` path with its hash unchanged and restored the prior absence of
  `/etc/system76-scheduler`. After scheduler reload and a restart limited to the same three user
  services, the PipeWire registry still failed to return and WirePlumber again reported one pending
  linkable after 20 seconds. The Quantum remains ALSA card `P2626` on IRQ 214, PCI `1c67:0104`
  remains bound to `snd_quantum2626`, and the installed module hash remains `890dcde7...6578`.
  Configuration rollback is exact, but desktop endpoint recovery failed; further live mutation is
  stopped pending user direction.
- **Observed Linux:** post-failure read-only localization shows all three user audio services still
  running, but Pulse clients block and YouTube cannot start playback. PipeWire exposes the five
  ALSA cards, including the Quantum device, but only a dummy audio sink and no ALSA audio nodes.
  WirePlumber identified its indefinitely pending object as `WpSiAudioAdapter`; it holds the
  Quantum control device but no process holds either Quantum PCM. UCM still parses as 13 playback
  plus 26 capture PCMs, direct ALSA control queries return, and no task-owned dshare/dsnoop System V
  IPC key remains. Both restart probes completed their short playback, duplex, and capture driver
  transitions without a stop timeout, kernel xrun, DMA fault, warning, or oops. The original
  System76 scheduler classes and niceness are also restored. This is currently a desktop
  PipeWire/WirePlumber ALSA-adapter activation wedge, not evidence that newly loaded kernel code
  crashed; no newer module was installed or loaded during this checkpoint. A lower-level
  UCM/driver-topology interaction remains possible until a clean recovery is followed by narrower
  startup tracing.
- **Observed Linux:** a user-initiated full reboot recovered the PipeWire/WirePlumber registry with
  no further partial service restart. The protected installed/tracked 256-frame UCM and installed
  module hashes remain exact, PCI `1c67:0104` is still bound to `snd_quantum2626`, and the scheduler
  override remains absent. All 13 Quantum sinks and 26 mono sources returned with Main and Input 5
  as defaults; both hardware PCM directions were closed after discovery. The original System76
  `SCHED_OTHER` classes and niceness were restored after its first refresh, and fresh user-audio
  logs contain no pending-linkable, activation, out-of-buffers, broken-pipe, or xrun marker.
- **Observed Linux:** successful fresh-boot discovery nevertheless caused 82 playback-only, 160
  capture-only, and two duplex prepares, with 240 start/resume operations. Two hundred thirty-four
  stops had zero IRQs; six short runs had three to seven IRQs. All retained 128/256-frame geometry
  and completed without a Quantum timeout, xrun, DMA fault, warning, BUG, or oops. The 13/26 UCM
  topology therefore multiplies discovery into hundreds of shared-engine transitions. This is now
  the leading bounded startup-risk seam, though it is not yet proven to have caused the earlier
  WirePlumber adapter activation wedge.
- **Observed Linux and user-observed hardware:** untouched YouTube Music PWA playback after that
  reboot reproduced many audible pops. ALSA playback remained RUNNING at 48 kHz, 26-channel
  S32_LE, 128-frame periods, and a 256-frame buffer while capture stayed closed. The device
  delivered 1,129 interrupts in approximately three seconds, consistent with 375 per second, and
  the kernel emitted no matching Quantum timeout, xrun, DMA fault, warning, BUG, or oops. The
  PipeWire graph was instead running at 44.1 kHz/64 frames around a 48 kHz Main adapter; Main and
  Firefox error counters advanced, and the bounded user journal contained 40 dshare
  `snd_pcm_mmap_commit` `Broken pipe` entries. This is a clean-reboot reproduction of the desktop
  failure with a healthy hardware transport, not evidence that a newer kernel artifact crashed.
- **Observed Linux and user-observed hardware:** during a later report that the recurring pops
  sounded like vinyl, Main had accumulated 97 PipeWire errors and Firefox two. The counters stayed
  fixed across eight samples, but the preceding three minutes contained three new pairs of dshare
  `snd_pcm_mmap_commit` `Broken pipe` errors about 21 seconds apart. ALSA remained at the protected
  48 kHz, 26-channel S32_LE, 128/256-frame playback geometry with capture closed; IRQ 213 advanced
  by exactly 1,125 in approximately three seconds and the kernel emitted no matching fault. This
  confirms a bursty, repeatedly recurring userspace playback failure rather than a continuously
  overloaded graph or lost hardware cadence.
- **Static standards comparison:** established Linux ALSA drivers such as RME HDSPM and FireWire
  AMDTP retain one raw multichannel PCM, report a hardware pointer, notify ALSA at period
  boundaries, and coordinate shared directions. The Quantum driver follows that relevant basic
  model at fixed 48 kHz, 26-channel S32_LE and a 128-frame integer-period geometry. No observed
  hardware fault currently justifies a speculative DMA rewrite or driver-side xrun detector.
- **Static desktop-audio comparison:** upstream ALSA UCM's `SplitPCM`/`SplitPCMDevice` macros are
  the established solution for publishing channel slices from multichannel hardware. The Quantum
  UCM currently hand-builds the old dshare/dsnoop fallback, which this host's WirePlumber 0.4.17
  probes as 39 direct nodes. Native PipeWire loopback handling arrived in WirePlumber 0.5.8. The
  installed ALSA UCM/alsa-lib 1.2.8 split macro only addresses hardware channels 0-23; upstream
  1.2.13 expanded it to 32 hardware channels. The current distribution repositories offer neither
  compatible upgrade, so adopting `SplitPCM` now would lose Quantum channels 24-25 and retain the
  legacy probe behavior. A future migration must upgrade the complete compatible userspace stack,
  not vendor a partial endpoint rewrite.
- **Static PipeWire comparison:** the active Quantum ALSA node's 128-frame period and
  `api.alsa.period-num = 2` directly select its observed 256-frame hardware buffer. This explains
  why changing only UCM `buffer_size` did not produce a 512-frame runtime. The current host also
  explicitly allows multiple graph rates, so PipeWire may validly run a 44.1 kHz graph and resample
  the fixed 48 kHz hardware node; that behavior is not itself proof of the audible fault. A valid
  current-stack 512 test must pair UCM `buffer_size = 512` with a Quantum-only
  `api.alsa.period-num = 4` rule and keep the 128-frame period. No such rule has been installed.
- **Observed Linux:** an authorized paired 512-frame checkpoint installed the exact
  `db4d09cb...3192` UCM candidate plus a new Quantum-only WirePlumber 0.4 rule,
  `dd3fd0ed...94840`, requesting 128-frame periods and four periods for both shared playback and
  capture paths. Both installed files matched their sealed bytes, and the 512 UCM parsed offline
  as all 13 playback plus 26 capture endpoints. After restarting only PipeWire, PipeWire Pulse,
  and WirePlumber, all endpoints initially returned and Firefox reconnected, but Main still
  reported `api.alsa.period-num = 2`; ALSA and driver logs remained 128/256. Dense dshare broken
  pipes began immediately. This was not a 512-frame runtime and supplies no 512-frame performance
  evidence.
- **Observed Linux and user-observed host:** exact rollback restored tracked/installed UCM hash
  `3fa8c219...64b29` and removed only the new rule, restoring its prior absence. The rollback
  restart left the three services active but `wpctl` timed out and WirePlumber reported one pending
  linkable after 20 seconds. ALSA card `P2626`, PCI binding, IRQ 213, and module hash
  `890dcde7...6578` remain intact with the PCM closed and no kernel fault. The user confirmed the
  desktop audio path had crashed. This is failed runtime rollback verification and a hard stop;
  do not retry the rule, restart the services again, or advance the buffer matrix. A full host
  reboot is the only recovery already proven for this exact pending-linkable state.
- **Observed Linux and user-observed host:** the same occurrence was subsequently recovered without
  rebooting. PipeWire could still enumerate the Quantum card but initially had only the dummy sink;
  WirePlumber alone held `controlC0`, both Quantum PCMs were free, no Quantum shared-memory segment
  remained, and PipeWire/Pulse were healthy. A bounded foreground WirePlumber diagnostic made
  endpoints work temporarily and then removed them when its 25-second timeout exited, which the
  user observed. Starting the persistent WirePlumber service afterward—without restarting
  PipeWire, Pulse, applications, the module, or the host—restored all 13 playback and 26 capture
  endpoints with Main and Input 5 defaults. No pending-linkable message appeared during the next
  25 seconds and the final registry count remained 13/26. Protected hashes remain exact. The user
  had closed playback, so audible stability remains untested; the activation race itself is not
  fixed, only the desktop session is recovered.
- **Static analysis and observed Linux:** the driver has transition-path performance debt even
  though current evidence does not identify it as the settled crackle source. Changing one PCM
  direction's parameters or freeing it while the other direction runs stops and rebuilds the full
  joint DMA engine. The final trigger stop can also spend up to about one millisecond polling the
  stop status and emits a stop log from the atomic trigger path. Multiplied by hundreds of legacy
  UCM probe transitions, this is plausibly harmful during discovery, startup, or capture-open
  reconfiguration and should be redesigned narrowly. The measured 00:13:30--00:15:10 vinyl-like
  crackle window contained no driver DMA prepare/start/stop/reconfiguration log, while PipeWire
  emitted repeated dshare broken pipes and hardware IRQ cadence remained correct. Therefore the
  known transition debt is not evidenced as the cause of that settled playback burst. A longer
  direct-ALSA control and narrow IRQ-position delta instrumentation are required before claiming a
  steady-state pointer/period bug or rewriting DMA.
- **Observed Linux and offline validation:** a read-only 2026-08-16 checkpoint retained PCI
  `1c67:0104`, the `snd-quantum2626` binding, ALSA card `P2626` on IRQ 213, module hash
  `890dcde7...6578`, loaded `srcversion` `6CDB07D137537DE2CEB3797`, installed/tracked UCM hash
  `3fa8c219...64b29`, and all 13 playback plus 26 capture endpoints. The failed four-period rule
  matched `api.alsa.path`, while its preserved debug log identifies the Quantum UCM nodes through
  `node.name`. A new repository candidate pairs the already parsed 512-frame UCM
  (`db4d09cb...3192`) with a WirePlumber 0.4 rule (`8fa704fa...d6d`) whose two globs match the exact
  13/26 preserved node-name inventory. Staged installation produced mode-0644 files; isolated UCM
  parsing retained one HiFi verb and all 39 devices; the WirePlumber configuration loaded without
  a parse error against an intentionally empty runtime; and the driver build passed. At that
  checkpoint the candidate had not been installed; four-period activation and crackle improvement
  were unproven live.
- **Observed Linux, 2026-08-16:** the exact 512-frame UCM (`db4d09cb...3192`) and corrected
  WirePlumber 0.4 rule (`8fa704fa...d6d`) were installed byte-for-byte at mode 0644. A subsequent
  separately authorized single restart of PipeWire, PipeWire Pulse, and WirePlumber exited 0. All
  three services returned active, and the complete 13 Quantum playback plus 26 capture endpoint
  inventory returned without the earlier pending-adapter wedge. Main now advertises
  `api.alsa.period-size = 128` and `api.alsa.period-num = 4`, proving the corrected node-name rule
  activated. Playback and capture remained closed, so hardware 128/512 geometry, settled error
  behavior, and audible improvement remain unproven.
- **Observed Linux and user-observed hardware, 2026-08-16:** user-started playback after that
  restart opened at 48 kHz, 26-channel S32_LE with a 128-frame period but an unchanged 256-frame
  hardware buffer; capture remained closed. The user described playback as somewhat better while
  still hearing occasional crackle. Thus the corrected rule's advertised four-period value still
  did not produce 128/512 hardware geometry, and the audible observation belongs to another
  post-restart 256-frame runtime. This is an invalid 512-frame trial and failed settled audible
  acceptance; no further runtime action followed the unexpected-geometry hard stop.
- **Static source diagnosis and offline validation, 2026-08-16:** the driver's PCM hardware table
  advertises 2 through 64 periods at its fixed 128-frame period; this alone does not exclude a
  narrower ALSA-core buffer constraint. The active dshare IPC
  segment was created after the service restart, excluding stale pre-restart geometry. Exact
  alsa-lib 1.2.8 source shows that a configured `buffer_size` is negotiated with a near-size request
  before period size is fixed, while its documented `periods` path is used only when buffer size and
  time are omitted and applies the period count after fixing period size. The repository UCM now
  requests `period_size 128` plus `periods 4` for both dshare and dsnoop and retains the matching
  WirePlumber period-count rule. The new UCM hash is `8a837fcc...4bed`; staged mode-0644 installation
  is byte-exact and an isolated fixture parses one verb, 13 playback devices, and 26 capture
  devices. The installed UCM remains the failed `db4d09cb...3192` buffer-size candidate; no runtime
  file or service changed, and the periods-based replacement remains unproven live.
- **Observed Linux, 2026-08-16:** the periods-based UCM (`8a837fcc...4bed`) was subsequently
  installed byte-for-byte at mode 0644 while retaining the exact WirePlumber rule
  (`8fa704fa...d6d`). A separately authorized single restart of PipeWire, PipeWire Pulse, and
  WirePlumber exited 0; all three services and the complete 13 playback plus 26 capture endpoint
  inventory returned without the prior pending-adapter wedge. Playback did not reconnect during a
  bounded 30-second wait, so both hardware PCMs remained closed. Actual 128/512 geometry, settled
  errors, and audible improvement remain unobserved; no playback/capture opening, retry, repair,
  rollback, module/device action, or further runtime mutation occurred.
- **Observed Linux and user-observed hardware, 2026-08-16:** once the user started playback with the
  periods-based candidate active, Main resolved to `api.alsa.period-size = 128` and
  `api.alsa.period-num = 2`; ALSA opened at 48 kHz, 26-channel S32_LE with 128-frame periods and a
  256-frame buffer, while capture remained closed. The user reported that playback seemed good, but
  this is another clean 128/256 interval rather than 512-frame evidence. Explicit UCM `periods 4`
  therefore failed just as `buffer_size 512` did, and the earlier negotiation-order diagnosis is
  incomplete. No further diagnostic or runtime mutation followed the unexpected-geometry hard stop.
- **Static source diagnosis, 2026-08-16:** exact installed PipeWire 1.0.2 source confirms that two
  periods are a configurable default, not a hard PipeWire limit. Its ALSA node accepted the
  WirePlumber `api.alsa.period-num = 4` property, passed `4` to
  `snd_pcm_hw_params_set_periods_near()`, then used the value returned by ALSA to calculate and
  publish the active buffer geometry. The returned value was `2`, matching the observed 128/256
  hardware runtime. The remaining limiter is therefore in the ALSA direct-plugin/slave constraint
  path, not an unconditional PipeWire clamp. No live state changed during this diagnosis.
- **Observed configuration, 2026-08-16:** no user ALSA, PipeWire, WirePlumber, or user-systemd
  configuration sets a two-period limit. The user PipeWire and WirePlumber configuration
  directories contain no files, system ALSA leaves `defaults.pcm.dmix.max_periods` at automatic
  (`0`), and live PipeWire metadata has no forced rate, quantum, or period-count override. The only
  active Quantum period-count rule explicitly requests `4`. This excludes a normal user setting as
  the source of the negotiated `2`; no runtime state changed during the check.
- **Static and read-only live localization, 2026-08-16:** alsa-lib's `_alibcfg` read-back of the
  isolated installed-UCM fixture retains `period_size 128` plus `periods 4` in the expanded dshare
  and dsnoop definitions. A read-only attachment to the active playback dshare shared-memory
  segment then showed both its hardware interval and copied slave state fixed at period size 128,
  period count 2, and buffer size 256. The value is therefore lost when dshare initializes its
  first hardware slave, after UCM expansion but before PipeWire configures the dshare client. No PCM
  was opened and no runtime state changed by these checks.
- **Failed constraint probe, 2026-08-16:** after the PCM closed and sealed hashes matched, the
  constraint-only helper was invoked exactly once inside the execution sandbox. It exited 1 before
  opening the PCM because ALSA could not resolve card `P2626` there; `/dev/snd` was unavailable in
  that execution context. Host read-back still showed card 0 as `P2626`, PCI `09:00.0` bound to
  `snd-quantum2626`, and playback closed. No hardware parameters were applied and DMA was not
  started. The attempt is consumed and cannot be retried without a fresh host-execution approval.
- **Observed host constraint rejection, 2026-08-16:** a separately approved host-level invocation
  of the same helper passed closed-PCM, hash, and `/dev/snd/controlC0` preflight, then reached the
  real hardware PCM and returned `EINVAL` while refining the exact fixed geometry plus four periods.
  Playback read back closed and no Quantum prepare, DMA, xrun, timeout, or fault event appeared.
  Because the first helper used one shared error label, this proves rejection within the four-period
  refinement sequence but does not distinguish the period setter from its final single-buffer
  query. The attempt is consumed; a corrected range-reporting helper is prepared but uninvoked.
- **Observed host constraint and static root cause, 2026-08-16:** the separately approved corrected
  helper was invoked exactly once. After fixing access, S32_LE, 48 kHz, 26 channels, and a
  128-frame period, the real hardware PCM reported `periods=2..2` and `buffer_size=256..256`; an
  exact four-period refinement returned `EINVAL`. Read-back left playback closed and the kernel log
  contained no Quantum prepare, DMA, xrun, timeout, or fault event. `/proc/asound` reports a 28 KiB
  current preallocation and an 832 KiB permitted allocation ceiling with `preallocate_dma=1`.
  ALSA core constrains hardware parameters with the substream's current preallocated byte count,
  while the driver's `snd_pcm_set_managed_buffer_all()` call requests the two-period minimum as its
  initial allocation and the 64-period value only as the later allocation ceiling. The page-aligned
  initial allocation cannot hold four 26-channel periods, so refinement collapses to two before
  managed allocation can grow it. This is the kernel-side limiter; PipeWire, UCM, dshare, and user
  configuration are passing the requested four periods correctly. The corrected helper gate is
  completed and consumed; no hardware parameters were applied and no DMA was started.
- **Decision, 2026-08-16:** use the corrected four-period integration as the immediate PR-sized
  candidate because it is device-scoped and addresses measured userspace underrun headroom while
  preserving the 128-frame hardware period. Do not present it as a fix until live read-back proves
  128/512 geometry and settled audible/error acceptance. Keep the transition-path driver cleanup
  and distribution-specific System76 Scheduler policy as separate later seams.
- **Decision, 2026-08-16:** correct the driver's managed-buffer setup before another 512-frame
  activation. The narrow source candidate is to request no fixed initial preallocation (`size=0`)
  while retaining `QUANTUM_AUDIO_MAX_BUFFER_BYTES` as the managed allocation ceiling, preserving
  the fixed 48 kHz, 26-channel, S32_LE transport and 128-frame hardware period. Build/static proof,
  module replacement, service activation, and live geometry/listening remain separate boundaries.
- **Implemented and offline-validated, 2026-08-16:** the driver now passes `0` as the managed-buffer
  initial allocation while retaining `QUANTUM_AUDIO_MAX_BUFFER_BYTES` as its ceiling. This is the
  single intended source change and does not alter the fixed transport or period constants.
  `make -C driver W=1` completed successfully against kernel 7.0.11 headers; only the existing
  compiler-name and unavailable-BTF warnings appeared. The resulting uninstalled module has SHA-256
  `357f341d66165d912c5f02340a5a9bf0997ecd70f3e6f62340e2a115238544e6` and matching kernel
  vermagic. No installed or loaded module, service, PCM, or hardware state changed.
- **Failed install gate, 2026-08-16:** `TASK-002-INSTALL-MODULE-BUFFER-V1` passed exact source,
  predecessor, kernel, mode, loaded-module, and closed-PCM preflight, then invoked its sealed
  controller exactly once. The host PTY stopped at an unexposed `sudo` password prompt; after the
  user confirmed no approval or prompt was visible, the invocation was cancelled and exited 1
  before the controller ran. Read-back proves the installed module remains the predecessor hash
  `890dcde7...6578`, the built candidate remains `357f341d...44e6`, playback is closed, and no
  Quantum prepare, DMA, xrun, timeout, or fault appeared. The gate is `consumed_failed` and cannot
  be retried. A successor requires a fresh exact invocation using a user-visible authentication
  mechanism; installation and runtime activation remain unachieved and separate.
- **User-installed and read back, 2026-08-16:** the user ran the exact install and `depmod` command
  in their own visible terminal. The installed module now matches the built candidate SHA-256
  `357f341d66165d912c5f02340a5a9bf0997ecd70f3e6f62340e2a115238544e6` at mode 0644;
  `modinfo` and `modprobe --show-depends` resolve to that exact path, and its source version is
  `32249FA363697CEC99DC456`. The currently loaded module remains the predecessor source version
  `6CDB07D137537DE2CEB3797`, and playback is closed. Installation is achieved but activation is not;
  no unload/load, restart, playback/capture, or hardware action occurred during read-back.
- **Failed activation gate, 2026-08-16:** `TASK-002-ACTIVATE-MODULE-BUFFER-V1` stopped the three user
  audio services once, but their enabled PipeWire sockets could reactivate them before the root
  controller's no-open-handle precondition. The exact controller exited 1 and restored the three
  services without unloading the predecessor module. Read-back shows loaded source version
  `6CDB07D137537DE2CEB3797`, PCI/card present, both PCMs closed, all three services active, and the
  full 13/26 endpoint inventory restored. Enumeration produced repeated zero-interrupt capture
  prepare/start/stop probes at the unchanged 128/256 geometry; no xrun, timeout, or fault appeared.
  The gate is consumed and cannot be retried. The installed candidate remains inactive; a successor
  must stop both PipeWire services and their sockets before the exact module reload.
- **User-activated and live-proven geometry, 2026-08-16:** the user stopped both PipeWire sockets
  with the three services, unloaded/reloaded `snd-quantum2626`, and restored the audio stack in
  their visible terminal. Loaded and installed source versions now both read
  `32249FA363697CEC99DC456`; the installed SHA-256 remains `357f341d...44e6`. The card returned on
  PCI `09:00.0`, all three services are active, and all 13 playback plus 26 capture endpoints are
  present. ALSA now reports zero initial preallocation with the unchanged 832 KiB ceiling. Endpoint
  enumeration repeatedly prepared exactly 53,248 bytes: 512 frames at the fixed 128-frame period,
  48 kHz, 26-channel S32_LE geometry. Both PCMs subsequently returned closed and all 39 Quantum
  nodes are suspended; only PipeWire and WirePlumber hold the control device. This proves the
  managed-buffer source correction and 128/512 activation. Settled user playback, sound quality,
  and error-counter acceptance remain untested.
- **Observed Linux and user-observed hardware, 2026-08-16:** ordinary Firefox playback runs at the
  exact 48 kHz, 26-channel S32_LE, 128/512 geometry. The user initially said it sounded excellent,
  then reported occasional residual crackle while still calling it the best result so far. Two
  dshare `Broken pipe` messages occurred exactly at stream start; no further PipeWire or kernel
  error marker appeared in a later ten-second settled sample. `pw-top` reported four cumulative
  errors on Main, zero on Firefox, and low scheduling ratios. No kernel xrun, timeout, or fault was
  recorded. The buffer correction is therefore proven and materially beneficial, but no-crackle
  acceptance is incomplete.
- **Observed scheduling state, 2026-08-16:** the live PipeWire, PipeWire Pulse, and WirePlumber data
  loops are all `SCHED_OTHER`; PipeWire is nice -15 rather than realtime. The System76 Scheduler
  service and its PipeWire policy helper remain active. With Firefox error-free, Main carrying the
  graph errors, hardware geometry correct, and the kernel fault-free, the remaining crackle again
  localizes to the userspace scheduling/control seam rather than insufficient hardware buffer
  allocation. Preserve 128/512 while investigating that seam separately.
- **Upstream scheduling research, 2026-08-16:** exact installed System76 Scheduler source commit
  `8651bbf` confirms that every profile defaults to `SCHED_OTHER`, the priority setter walks every
  thread of each selected process and calls `sched_setscheduler()`, and the enabled 60-second
  refresh reapplies those profiles. The stock sound-server profile selects PipeWire and PipeWire
  Pulse but omits `sched=`, so the implementation can undo PipeWire's observed RTKit `SCHED_RR/20`
  grants. PipeWire documents realtime data-processing threads as part of its graph design. This is
  also a known general class of failure: upstream System76 issues #99 and #102 remain open for
  scheduler-associated crackling and external-interface underruns at 48 kHz/128 frames. The merged
  #114/#118 response removed a whole-process FIFO-49 rule after reports of audible glitches, but
  changed only `data/config.kdl`; it did not change the default policy or all-thread setter. The
  correct ownership model is therefore to except the PipeWire server processes from System76 CPU
  policy changes and let PipeWire/RTKit manage realtime on only their data loops, not to force FIFO
  or `SCHED_OTHER` across every process thread. This strongly supports the local scheduling
  diagnosis, but a controlled listening/error-delta checkpoint is still required for causal
  acceptance.
- **Observed scheduler isolation and residual crackle, 2026-08-16:** the exact full System76
  Scheduler override excepting only `/usr/bin/pipewire` and `/usr/bin/pipewire-pulse` is installed
  at `/etc/system76-scheduler/config.kdl`, SHA-256
  `48f1743e3db8b2adeb110b41cd3f41a17bb11378bfd697ac62696b30d68ee677`, mode `0644`, owner
  `root:root`. After one scheduler reload and one user-audio restart, all 13 playback and 26 capture
  endpoints returned. PipeWire and PipeWire Pulse data loops held `SCHED_RR/20` through 150 seconds
  and more than two 60-second scheduler refreshes; their main threads remain `SCHED_OTHER` nice 0.
  WirePlumber alone was reassigned to `SCHED_OTHER` nice -9 by the stock recording profile after
  the first refresh. Ordinary playback retained exact 48 kHz, 26-channel S32_LE, 128/512 ALSA
  geometry. Main's cumulative PipeWire error count stayed at one and Firefox stayed at zero across
  the settled sample, with no focused user-journal xrun/underrun or kernel DMA/fault marker. The
  user still hears occasional clicks, strongest initially and easing over time. Thus the scheduler
  ownership defect is corrected and its periodic demotion eliminated, but it was not the sole
  audible cause. Preserve the override and current hardware geometry. The next diagnostic seam is
  the live 44.1 kHz PipeWire graph feeding fixed 48 kHz hardware, followed by the legacy dshare
  pointer/accounting path; either live configuration experiment needs its own exact authority.
- **Active 48 kHz graph-isolation checkpoint, 2026-08-16:** the user-level PipeWire fragment
  `/home/jamie/.config/pipewire/pipewire.conf.d/51-quantum2626-rate.conf` is installed with SHA-256
  `f251c0e971fa06e172857b86833dda041878b5308ec719801d3f6107cdcc3385`, mode `0644`, owner
  `jamie:jamie`. After one user-audio restart, PipeWire 1.0.3 reports graph rate `48000` with allowed
  rates restricted to `[ 48000 ]`, and all 13/26 Quantum endpoints returned. A 20-sample observation
  contained no active playback stream. The user subsequently reported that residual crackle was
  still audible; the immediate read-back again found ALSA closed and Firefox idle at its declared
  44.1 kHz format with zero errors, so no active-stream geometry or error delta was captured. The
  48 kHz graph restriction is therefore audibly insufficient. It removes only the mismatch between
  the PipeWire graph and the fixed 48 kHz device path; it cannot eliminate 44.1-to-48 conversion for
  a 44.1 kHz client. Native 44.1 operation requires separately implemented and tested driver clock
  switching plus UCM/topology changes.

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
- **Implemented and live-proven at 48 kHz:** one S32_LE duplex PCM uses 128-frame periods, recovered
  playback/capture page tables, the confirmed base registers, and the hardware position for ALSA,
  with bounded stop/failure handling.
- **Implemented, unverified on hardware, 2026-08-16:** the source advertises only the exact native
  rate/channel profiles recovered from the vendor table: 26 channels at 44.1/48 kHz, 18 at
  88.2/96 kHz, and 8 at 176.4/192 kHz. The exact official DriverKit x86_64 slice confirms that TCI
  request `0x32` carries `{clock source, sample-rate enum}` as two little-endian `u32` values and
  expects status response `0x01` with a zero `u32`. Linux now stops/frees DMA resources before a
  rate change, refuses changes while either direction runs, checks the response, reads both device
  and clock rates back, and waits for the expected duplex channel register. Duplex parameters must
  match. `W=1`, checkpatch 0/0, and `git diff --check` pass; built module SHA-256 is
  `74422a1675292015f0e622f21a8cc99550adb975d1ab1650c97c416fa6608a28`. This is source integrity
  evidence only and does not authorize installation, module reload, or a TCI write.
- **Installed and active at the 48 kHz control state, 2026-08-16:** the native-rate candidate is the
  dependency-selected and loaded
  module at `/lib/modules/7.0.11-76070011-generic/updates/snd-quantum2626.ko`, SHA-256
  `74422a1675292015f0e622f21a8cc99550adb975d1ab1650c97c416fa6608a28`, srcversion
  `1DA82813C64453A1BC965D9`, mode `0644`, owner `root:root`. One bounded activation stopped and
  restored the three user audio services plus both sockets. All five units are active, and
  PipeWire exposes exactly 13 Quantum sinks and 26 Quantum sources. Fresh driver probe read-back is
  48 kHz device/clock rate with 26 capture/playback channels; the graph remains restricted to
  48 kHz. Both PCMs remained closed, so no playback/capture open or 44.1 kHz setter occurred. The
  first idle direct-PCM 44.1 kHz switch remains a separately bounded hardware checkpoint.
- **Observed Linux at native 44.1 kHz, 2026-08-16:** one direct one-second digital-silence playback
  switched the idle device to 44.1 kHz through the confirmed TCI setter. The driver's correlated
  read-back reported `rate=44100 Hz channels=26`. Playback used S32_LE, 26 channels, 128-frame
  periods, a 512-frame/53,248-byte buffer, and stopped after 345 interrupts. Both PCMs returned to
  `closed`, with no xrun, underrun, overrun, DMA timeout, or fault. One unrelated TCI RX record was
  skipped before the successful correlated rate read-back. PipeWire, PipeWire Pulse, WirePlumber,
  and both sockets remain intentionally stopped, preserving the hardware at 44.1 kHz because the
  currently installed UCM and graph override are still fixed to 48 kHz. Desktop audio is therefore
  unavailable until a separately validated 44.1 kHz desktop candidate is installed and the user
  audio stack is restored.
- **Observed Linux desktop at 44.1 kHz, 2026-08-16:** the installed UCM now selects 44.1 kHz for
  both shared 26-channel directions, and the user PipeWire fragment fixes the graph and allowed-rate
  list to `44100`. All five user audio units are active; PipeWire publishes exactly 13 Quantum sinks
  and 26 Quantum sources, both PCMs settled closed, and its two data loops run `SCHED_RR` priority
  20. During initial ALSA capability probing, WirePlumber briefly selected 48 kHz with an 8192-frame
  probe buffer, then returned the hardware to the UCM-selected 44.1 kHz, S32_LE, 26-channel,
  128/512 geometry. No timeout, fault, xrun, underrun, overrun, or error marker accompanied the
  bounded startup probe. The settled desktop rate and endpoint inventory are proven; audible
  44.1 kHz playback and crackle acceptance still require the user's ordinary listening result.
- **User-observed Linux desktop at 44.1 kHz, 2026-08-16:** ordinary Firefox playback ran through
  Main with exact ALSA geometry of 44.1 kHz, S32_LE, 26 channels, 128-frame periods, and a 512-frame
  buffer; capture remained closed. PipeWire Main used a 256-frame graph quantum, Firefox supplied
  native 44.1 kHz audio, and both nodes stayed at zero errors across five samples. The user reported
  no clicks. This is the first clean audible native-44.1 result; longer ordinary listening remains
  appropriate before declaring the earlier intermittent crackle eliminated in all conditions.
- **User-observed longer-playback failure at 44.1 kHz, 2026-08-16:** the same active Firefox/Main
  path later produced frequent pops and vinyl-like grain. ALSA remained exactly 44.1 kHz, S32_LE,
  26 channels, and 128/512 frames with capture closed. Main and Firefox stayed at zero PipeWire
  errors across ten samples; PipeWire/Pulse data loops retained `SCHED_RR` priority 20; configuration
  hashes were unchanged; and 1,035 hardware interrupts arrived in three seconds, the expected
  44.1 kHz/128-frame cadence. No audio/kernel fault marker or system suspend/resume was present.
  Raw kernel-slave `appl_ptr`/delay values remain invalid through this dshare topology as previously
  established, while the driver pointer callback correctly returns modulo the buffer. This
  invalidates durable no-click acceptance and localizes the next experiment to dshare timing below
  PipeWire's counters. Upstream alsa-lib describes `slowptr true` as its more precise pointer-update
  mode; test that on playback only before changing alignment, capture, rate, or geometry.
- **Active playback dshare precision candidate, 2026-08-16:** playback alone now specifies
  `slowptr true`; capture dsnoop is byte-for-byte unchanged. Installed `_alibcfg` confirms the
  option on `quantum2626_stereo_out`, with UCM SHA-256
  `20724f1b5f0aac8cb2d035d075cdc0195da252151f7a4968b62d55f6c2850f86`, mode `0644`, owner
  `root:root`. One bounded install/restart restored all five user audio units, the 44.1 kHz-only
  graph, 13 Quantum sinks, and 26 Quantum sources. Both PCMs settled closed, realtime data-loop
  policy remained intact, and no new kernel fault marker appeared. Rate, format, channel count,
  128/512 geometry, capture settings, scheduler policy, and pointer alignment were not changed.
  Audible acceptance remains pending a longer ordinary playback run.
- **User listening result with precise dshare pointer updates, 2026-08-16:** the sustained
  vinyl-like grain is no longer reported, but occasional pops remain and seem associated with some
  musical transients. This makes `slowptr true` beneficial but insufficient. Static analysis of the
  exact vendor HAL now proves that its linear PCM stream uses signed, interleaved samples with 24
  significant bits aligned high in a 32-bit container. Linux's S32_LE DMA container is consistent
  with that representation. The source now reports the 24-bit MSB precision to ALSA without
  changing storage, gain, rates, channels, period, or buffer geometry. The `W=1` build, checkpatch
  0/0, and `git diff --check` pass; module SHA-256 is
  `936671cb441888a8d679b7ac8d18a967d70e9210eb7b137c969b942a2c2bb362`, srcversion
  `700300BDE3C3C11C904B3F7`. A reduced-volume replay made any remaining pop harder to notice but did
  not eliminate it; retain unity-gain desktop operation as the acceptance target and do not claim
  the metadata correction fixes the pops before a separately authorized install and live test.
- **Offline playback-headroom candidate, 2026-08-16:** PipeWire documents
  `api.alsa.headroom` as extra ringbuffer space for devices whose read/write position is not
  accurately reported. The repository WirePlumber rule is now split by direction and requests
  128 frames of headroom on Quantum playback only; capture retains period size 128 plus period
  count 4 with no added headroom. This preserves the active rate, format, channels, 128/512
  hardware geometry, dshare alignment, scheduler policy, and unity gain while adding about 2.9 ms
  of playback safety margin at 44.1 kHz. WirePlumber 0.4.17 loaded the exact candidate without a
  Lua/configuration error in an isolated runtime; SHA-256 is
  `b3e47faa53fd4c6a2c30d507fe3bd315882903d1e87fe2331f5cc7994c43de83`. The node globs are
  unchanged from the admitted exact 13-output/26-input match proof. This candidate is not installed
  or active; do not combine its eventual test with the uninstalled `msbits=24` module or any IRQ,
  power-management, capture, rate, period, or buffer change.
- **Active playback-headroom candidate, 2026-08-16:** the exact
  `b3e47faa...de83` rule is installed root-owned at mode 0644 after one visible PolicyKit
  authorization. One restart limited to PipeWire, PipeWire Pulse, and WirePlumber returned all
  three services plus exactly 13 Quantum sinks and 26 Quantum sources. Main's SPA `Props` reports
  period size 128, period count 4, and playback headroom 128; a capture node retains period size
  128, period count 4, and headroom 0. Both hardware PCMs settled closed. No module, rate, capture,
  IRQ, QoS, or buffer-geometry action was combined with this activation. The next result must come
  from ordinary playback at unity software gain beyond the prior intermittent-pop window.
- **Active 256-frame playback-headroom A/B, 2026-08-16:** with 128 frames of headroom, the user
  heard only one tiny pop in about 30 seconds and called the result “pretty good.” Because that is
  improved but not pop-free, playback headroom alone was increased from 128 to 256 frames. The
  candidate passed WirePlumber 0.4.17's isolated Lua loader and has exact SHA-256
  `98c0febe888b864dfc3a9fe97f6adf9edd7369ee596d22661e9a65cd9a68a218`. Its one host install
  read back root-owned mode 0644, and one restart of PipeWire, PipeWire Pulse, and WirePlumber
  restored all three services plus 13/26 Quantum endpoints. Main reports period size 128, period
  count 4, and headroom 256; capture retains 128, 4, and headroom 0. Both PCMs settled closed. This
  adds about 2.9 ms relative to the 128-headroom trial and about 5.8 ms relative to zero headroom,
  without changing the 128/512 hardware geometry. Longer unity-gain listening is pending.
- **Observed CPU-latency QoS discriminator, 2026-08-16:** after the user still heard an occasional
  pop with 256 frames of playback headroom, a temporary `/dev/cpu_dma_latency` holder requested
  exactly 2 us during ordinary playback. Its exact script SHA-256 was
  `0681bdd068cd440b5a492244e72cd6125c3687f4f0e584030fd38110ee8cf4ff` and it reported PID 489410.
  CPU0's 120-us C2 and 1034-us C3 counters stopped advancing
  while the request was active. The user reported, “I didnt hear a single pop its clear af.” The
  holder was then released; no holder remained, C2 advanced from 11136565 to 11139402, and C3
  advanced from 13810741 to 13811453 over three seconds. This
  is strong causal evidence that CPU wake/IRQ latency contributes to the residual pops, but the
  short interval is not durable no-pop acceptance.
- **Implemented, unverified CPU-latency candidate, 2026-08-16:** after successful PCM prepare, the
  driver now tightens ALSA's existing per-substream `latency_pm_qos_req` to 2 us. ALSA retains
  ownership of teardown, so the request follows the configured PCM lifetime instead of remaining
  system-wide. The setting can reduce CPU idle depth and therefore increase power use while a PCM
  stays configured. `W=1`, checkpatch 0/0, and `git diff --check` pass. Module SHA-256 is
  `553635940c21b666d89b333e4783c28ade9510d5e5c7effaa5eaf8db52643138`, srcversion
  `4B3A66AF5A381999FA112F3`. The expected QoS imports resolve to GPL exports in the running kernel.
  No install, module action, service restart, PCM open, or runtime change occurred; live proof is a
  separately authorized boundary.
- **Observed Linux candidate installation and activation, 2026-08-16:** the exact module candidate
  was installed through one visible PolicyKit gate and read back root-owned mode 0644 with SHA-256
  `553635940c21b666d89b333e4783c28ade9510d5e5c7effaa5eaf8db52643138`. A distinct one-shot
  activation stopped the PipeWire and PipeWire Pulse services and sockets plus WirePlumber, proved
  the Quantum ALSA nodes unheld, reloaded only `snd_quantum2626`, and restarted the same five units.
  Loaded srcversion is `4B3A66AF5A381999FA112F3`; PCI `1c67:0104` is rebound to the driver, ALSA
  card `P2626` is present, all five units are active, and exactly 13 sinks plus 26 sources returned.
  Startup discovery exercised 128/512-frame prepare/start/stop paths and both PCMs settled closed.
  One WirePlumber proxy-destroyed activation message during graph reconstruction did not recur; the
  settled sample contained no kernel or user-audio xrun, underrun, overrun, timeout, fault,
  pending-adapter, broken-pipe, or out-of-buffers marker. No playback/capture command was run.
  User-started playback is required for audible acceptance and direct observation of the 2-us QoS
  effect while a PCM remains configured.
- **Observed Linux audible regression with active driver QoS, 2026-08-16:** user-started Firefox
  playback crackled and sounded worse than the earlier temporary 2-us `/dev/cpu_dma_latency` test.
  The in-driver request is nevertheless active: CPU0's 120-us C2 and 1034-us C3 counters remained
  unchanged over three seconds. ALSA stayed at 44.1 kHz, 26-channel S32_LE, 128/512 frames; Main
  retained playback headroom 256 and zero graph errors; Firefox retained zero errors; both PipeWire
  data loops remained `SCHED_RR` priority 20; and IRQ 213 advanced by 1,037 over three seconds,
  matching the expected period cadence. No matching kernel or user-audio fault marker appeared.
  PipeWire now reports `alsa.resolution_bits = 24`, which was absent from the prior loaded module.
  Because the clean temporary QoS result used that prior module, `msbits=24` is the leading audible
  regression variable rather than failed QoS application. Confirm with an exact QoS-only candidate
  before changing latency, geometry, rate, scheduling, or pointer settings. No mutation occurred in
  this diagnosis.
- **Implemented, unverified QoS-only discriminator, 2026-08-16:** the source removes only the
  `msbits=24` constraint from the crackling combined candidate while retaining the 2-us QoS update
  and all transport/desktop behavior. `W=1`, checkpatch 0/0, and `git diff --check` pass. Source
  SHA-256 is `a99ce31bfafdd9170f247fe4ec71c21fb6c579d41512278c72616edd356ef937`; module SHA-256 is
  `b6f261d074f94ca50b94c50d505242cad53a8bb6cfd96a798bf4b953484e025b`, srcversion
  `BB865ACB071304AE53DE91D`. The combined candidate remains installed and loaded pending the exact
  QoS-only install/activation A/B.
- **Observed Linux QoS-only installation and activation, 2026-08-16:** exact module SHA-256
  `b6f261d074f94ca50b94c50d505242cad53a8bb6cfd96a798bf4b953484e025b` was installed root-owned
  mode 0644 and loaded as srcversion `BB865ACB071304AE53DE91D`. The bounded activation stopped the
  same PipeWire/Pulse services and sockets plus WirePlumber, proved the Quantum nodes unheld,
  reloaded only the driver, and restarted those units. All five are active, exactly 13 sinks plus
  26 sources returned, both data loops are `SCHED_RR` priority 20, and both PCMs settled closed.
  Main retains period size 128, period count 4, and headroom 256; discovery prepared exact 128/512
  hardware geometry. PipeWire reports `alsa.resolution_bits = 32`, proving that only the prior
  `msbits=24` metadata was removed while driver QoS remains. One startup proxy-destroyed message did
  not recur, and the settled sample contains no audio/kernel fault marker. No playback/capture
  command was run; user listening is pending.
- **User-observed QoS-only acceptance, 2026-08-16:** during ordinary Firefox playback the user
  reported, “this is it!! this is what I paid for with the quantum sounds fucking excellent clean
  af.” ALSA was RUNNING at 44.1 kHz, 26-channel S32_LE, 128/512 frames with capture closed. Main
  reported resolution bits 32, period size 128, period count 4, headroom 256, and zero errors;
  Firefox also retained zero errors. Both PipeWire data loops remained `SCHED_RR` priority 20.
  CPU0 C2 (120 us) and C3 (1034 us) counters did not advance over approximately three seconds,
  proving the driver QoS request was active, while IRQ 213 advanced by 1,050, consistent with the
  expected 44.1 kHz/128-frame cadence. No matching audio/kernel fault marker appeared. This is the
  strongest clean desktop result so far and isolates `msbits=24` as the regression in the preceding
  combined build. Longer ordinary listening is still required before declaring durable no-pop
  release acceptance.
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
- **Observed Linux and user-observed hardware:** native-44.1 NeuralRack routing exposed a later
  capture-first duplex failure that the proven 48-kHz test did not cover. The driver started
  capture-only `0x2`, rebuilt exact 128/512 resources for joint `0x3`, and resumed only the
  previously running `0x2` mask; source inspection shows playback then late-joins the active engine
  without a hardware restart. Capture, NeuralRack, Main, and Firefox all reported RUNNING with zero
  PipeWire errors and no fault log, but both processed guitar and Firefox playback were inaudible.
  Closing NeuralRack rebuilt playback-only `0x1` and restored Firefox with crackle. Geometry stayed
  44.1 kHz, 26-channel S32_LE and 128/512, PipeWire data loops stayed `SCHED_RR` priority 20, and
  frozen CPU0 C2/C3 counters proved the 2-us driver QoS remained active. A ten-second user pause
  then forced a complete playback-only close/reopen and restored clean audio. Treat native-44.1
  live duplex as failed until pointer/period phase continuity across the second-direction late join
  is corrected and separately validated.
- **Implemented, unverified:** the refined duplex lifecycle candidate preallocates fixed playback
  and capture buffers, programs their stable DMA addresses together, and leaves the joint tables
  intact when only one ALSA direction changes. It now follows ALSA's established shared-transport
  model more completely by advertising synchronized start, assigning the card sync identifier,
  and completing linked same-card playback/capture triggers as one operation. An independent late
  stream reports a zero pointer while pending, becomes active on the next hardware-buffer wrap,
  and receives its first elapsed-period callback on the following 128-frame boundary. At
  44.1 kHz/512 frames the alignment wait is bounded by about 11.6 ms. The IRQ path recognizes a
  ring-counter crossing instead of depending on observing exact frame zero. Source
  `49a19aeb...0058` builds as module `ab0b231f...ade5`, srcversion
  `F54583811438D0400BD5585`; `git diff --check`, `checkpatch` 0/0, and `W=1` pass. This supersedes
  the earlier `304724c5...3376` offline design and had not yet been installed or activated at this
  checkpoint. The loaded
  QoS-only runtime control remains separate; no service restart, playback, capture, or device
  mutation occurred while building it.
- **Observed Linux installation boundary, 2026-08-16:** one exact PolicyKit controller invocation
  installed refined candidate module `ab0b231f...ade5` at mode 0644 and ran `depmod`. Both
  `modinfo` and `modprobe --show-depends` resolve to that file and report candidate srcversion
  `F54583811438D0400BD5585`. The kernel remains on loaded QoS-only srcversion
  `BB865ACB071304AE53DE91D`, so installation is complete but inactive. No reload, service restart,
  playback, capture, or hardware validation occurred. Activation requires a separate boundary.
- **Observed Linux incomplete activation boundary, 2026-08-16:** one exact PolicyKit controller
  invocation returned exit 1 without output and was not retried. Candidate srcversion
  `F54583811438D0400BD5585` is nevertheless loaded and bound to PCI `1c67:0104`; ALSA card `P2626`
  is present, all five user audio units are active, and playback reopened at 44.1 kHz, 26-channel
  S32_LE with 128/512 geometry while capture is closed. The 13 playback sinks returned, but all 26
  capture sources are absent after a five-second read-only settle window. WirePlumber logged an
  audio-adapter `proxy destroyed` activation and an invalid standard-link event. The kernel log has
  no xrun, timeout, DMA fault, BUG, oops, or panic. The module activation succeeded but desktop
  endpoint recovery did not; do not retry or restart without a separate exact authorization.
- **Observed Linux failed WirePlumber-only recovery, 2026-08-16:** one approved WirePlumber service
  restart exited 0 without restarting PipeWire, Pulse, or the driver. All five units report active,
  but full PipeWire inventory calls no longer complete and WirePlumber PID 850128 logged one pending
  linkable after 20 seconds. Both PCMs are closed. Candidate srcversion
  `F54583811438D0400BD5585` remains loaded and IRQ 213 remains registered. The endpoint inventory is
  now unavailable, so the preceding 13/0 observation is historical rather than current. No second
  restart, broader recovery, module action, or rollback occurred.
- **Observed Linux five-unit recovery result, 2026-08-16:** one approved restart targeted exactly
  the PipeWire and Pulse services/sockets plus WirePlumber and exited 0 without reloading the driver.
  Registry calls respond again and all five units are active, but the result remains 13 Quantum
  sinks and zero sources. Playback reopened at native 44.1 kHz, 26-channel S32_LE with 128/512
  geometry; capture is closed. Kernel discovery repeatedly completed capture-only prepare/start/stop
  at exact 44.1 kHz/128/512 without a DMA or kernel fault. WirePlumber again aborted one audio
  adapter as `proxy destroyed` and invalidated a standard link. This proves a reproducible desktop
  capture regression under the refined candidate. The new synchronized-start metadata and grouped
  trigger path are the narrow leading discriminator relative to the earlier persistent-buffer build,
  but that source attribution is not yet A/B-proven.
- **Implemented, unverified synchronized-start compatibility A/B, 2026-08-16:** the source removes
  exactly `SNDRV_PCM_INFO_SYNC_START`, `snd_pcm_set_sync()`, and same-card grouped trigger handling.
  Persistent duplex DMA buffers, shared-engine lifetime, late-direction pending state, IRQ
  wrap-crossing promotion, native rate profiles, 2-us QoS, and 128-frame periods remain unchanged.
  Source `f9de15ab...5d12` builds as module `06cb461b...1632`, srcversion
  `B684EFED2CAC8084DCF0D1B`; `git diff --check`, checkpatch 0/0, and `W=1` pass. The candidate is not
  installed or loaded. Exact module `ab0b231f...ade5` remains installed and active with the 13/0
  desktop graph; no service, PCM, or hardware mutation occurred while preparing this A/B.
- **Observed Linux compatibility-A/B installation boundary, 2026-08-16:** one exact PolicyKit
  controller invocation installed module `06cb461b...1632` at mode 0644 and ran `depmod`. `modinfo`
  resolves to candidate srcversion `B684EFED2CAC8084DCF0D1B`, while the kernel remains on loaded
  synchronized-start predecessor `F54583811438D0400BD5585`. Installation is complete but inactive;
  no reload, service restart, PCM operation, or runtime validation occurred.
- **Observed Linux compatibility-A/B activation V1 preflight failure, 2026-08-16:** one PolicyKit
  controller invocation returned exit 1 without output before stopping any service or reloading the
  module. Loaded srcversion remains `F54583811438D0400BD5585`, all five units remain active,
  playback remains native 44.1 kHz/128/512 with capture closed, and the graph remains 13/0. The
  installed compatibility module remains exact `06cb461b...1632`. A labeled read-only follow-up
  passed kernel, module, service, and graph predicates, so the exact transient failed predicate is
  unavailable. Do not retry that controller; a labeled successor requires fresh authority.
- **Observed Linux compatibility-A/B activation V2 failure, 2026-08-16:** one exact PolicyKit
  invocation ran labeled controller `a12e9e40...936c`. Preflight passed, the five user audio units
  were stopped, predecessor srcversion `F54583811438D0400BD5585` was unloaded, compatibility
  srcversion `B684EFED2CAC8084DCF0D1B` was loaded, and all five units returned active. The final
  graph nevertheless remained 13 Quantum sinks and zero sources, and the controller exited 1.
  Installed and loaded module hash is `06cb461b...1632`; playback is RUNNING at native 44.1 kHz,
  26-channel S32_LE, 128/512 and capture is closed. At 16:54:34, during repeated capture-only
  discovery, the kernel recorded `DMAR: [DMA Write NO_PASID] Request device [09:00.0] fault addr
  0x0 [fault reason 0x05] PTE Write access is not set`. Removing synchronized-start metadata and
  grouped-trigger handling therefore did not repair capture. A capture DMA stop/resource-lifetime
  race is now the leading hypothesis, but remains unconfirmed pending offline source diagnosis.
  No retry, rollback, or further service/module action occurred.
- **Implemented, unverified persistent DMA-table lifetime correction, 2026-08-16:** monotonic log
  timing places the address-zero DMAR fault at the capture stop/`hw_free` boundary after about 1 ms
  of capture-only activity and zero IRQs. The driver previously cleared both page-table MMIO
  addresses and freed both coherent tables after the last parameters were released, even though
  ALSA's fixed playback/capture buffers remain allocated for the card lifetime. The source now maps
  both complete fixed allocations once, retains the page tables and MMIO addresses through
  `hw_free`, rapid discovery probes, and stopped rate changes, and independently updates the active
  byte/frame geometry before prepare. Source `51639424...8cb` builds as module
  `279eae29...0c6b`, srcversion `69CC3718CA2E575A1DE5451`; `git diff --check`, checkpatch 0/0,
  and `W=1` pass. The loaded module remains `06cb461b...1632`; no install, reload, service action,
  PCM operation, or hardware mutation occurred while preparing this correction.
- **Observed Linux persistent DMA-table installation V1 preflight failure, 2026-08-16:** exact
  controller `64dd23eb...91ba` was invoked once through PolicyKit and exited 1 after its labeled
  loaded-predecessor preflight began but before the first install action. V1 authority is consumed
  and must not be retried. Read-back proves installed module `06cb461b...1632` and loaded srcversion
  `B684EFED2CAC8084DCF0D1B` are unchanged; PCI remains driver-bound, ALSA card `P2626` remains
  present, playback is RUNNING, and capture is closed. The failed predicate is classified: the
  controller incorrectly expected sysfs driver basename `snd_quantum2626` instead of the actual
  `snd-quantum2626`. No install, `depmod`, reload, restart, PCM operation, cleanup, or rollback
  occurred. A corrected successor requires a fresh seal and separate approval.
- **Observed Linux persistent DMA-table installation V2 boundary, 2026-08-16:** freshly approved
  corrected controller `93f26db3...45c3f` passed every labeled preflight, installed exact module
  `279eae29...0c6b`, srcversion `69CC3718CA2E575A1DE5451`, root-owned mode 0644, and ran `depmod`
  for the running kernel. Loaded srcversion remains predecessor `B684EFED2CAC8084DCF0D1B`; PCI is
  still bound, playback remains RUNNING, and capture is closed. Installation is complete but
  inactive. No reload, restart, PCM operation, or runtime validation occurred.
- **Observed Linux persistent DMA-table activation V1 result, 2026-08-16:** exact controller
  `c84ceac1...da03` passed every preflight, stopped the five user audio units, unloaded predecessor
  `B684EFED2CAC8084DCF0D1B`, loaded candidate `69CC3718CA2E575A1DE5451`, and restarted all five
  units. PCI/card and active-unit read-back passed, but the final graph remained 13 Quantum sinks
  and zero sources, so the controller exited 1 and its authority is consumed. Rapid capture-only
  discovery again ran many zero-IRQ start/stop cycles; unlike the predecessor, it emitted no
  DMAR/IOMMU fault, DMA-stop timeout, or page-table timeout. The persistent mapping therefore fixes
  the observed address-zero safety failure but not WirePlumber's recurring `proxy destroyed`
  adapter failure. User-session logs briefly named all 26 Quantum input stream IDs before those
  objects became invalid, consistent with publish-then-destroy behavior. Playback remains RUNNING
  at native 44.1 kHz, 26-channel S32_LE, 128/512 and capture is closed. No retry, rollback, second
  restart, playback command, or capture command occurred.
- **User-observed Linux playback regression, 2026-08-16:** with persistent-table srcversion
  `69CC3718CA2E575A1DE5451` active, ordinary playback has a new “weird static sound.” ALSA remains
  exact 44.1 kHz/26-channel S32_LE/128/512, capture is closed, and IRQ 213 advanced 1,036 times over
  three seconds versus about 1,034 expected. No DMAR/IOMMU, xrun, timeout, warning, BUG, or oops
  marker appeared. The only new playback-visible source variable is that both page tables now map
  the complete maximum ALSA allocation rather than only the active 512-frame buffer. Treat that
  maximum data-page extent as the leading cause. Preserve persistent coherent table allocation for
  DMA safety, but populate and link only active-buffer pages in the next offline correction. No
  runtime mutation or source correction occurred during this diagnosis.
- **Implemented, unverified persistent-table/active-page correction, 2026-08-16:** the source now
  allocates each coherent DMA table once at maximum capacity but separately populates only the
  current active buffer pages and links only the segments those pages require. The current
  53,248-byte/512-frame geometry therefore returns to exactly 13 data-page entries with no extra
  segment link, while stopped geometry changes rewrite the same allocation instead of releasing its
  DMA address. Source `1a11efe8...2d0e` builds as module `d54f2bf4...b45e`, srcversion
  `D1D19FA61C85B05A46E2A01`; `git diff --check`, checkpatch 0/0/0, and `W=1` pass. Installed and
  loaded maximum-map module `279eae29...0c6b` remains unchanged. No installation, reload, restart,
  PCM operation, or hardware mutation occurred during this offline correction.
- **Observed Linux active-page correction installation V1, 2026-08-16:** exact controller
  `fb182171...fe86` passed candidate, predecessor, loaded-runtime, PCI, and ALSA preflight, then
  installed module `d54f2bf4...b45e`, srcversion `D1D19FA61C85B05A46E2A01`, root-owned mode 0644
  and ran `depmod`. Installed read-back matches the candidate; loaded srcversion remains rejected
  maximum-map `69CC3718CA2E575A1DE5451`, playback remains RUNNING, and capture is closed.
  Installation is complete but inactive; no reload, restart, PCM operation, or runtime validation
  occurred.
- **Observed Linux active-page correction activation V1, 2026-08-16:** exact controller
  `9b3a5865...8b8d` passed all candidate, predecessor, configuration, device, service, graph, and
  geometry preflight; stopped the five audio units; unloaded rejected maximum-map srcversion
  `69CC3718CA2E575A1DE5451`; loaded active-page srcversion `D1D19FA61C85B05A46E2A01`; and
  restarted all five units. PCI/card and active-service read-back passed, but the stable graph
  remained 13 Quantum sinks and zero sources, consuming the gate with exit 1. Playback returned
  RUNNING at exact native 44.1 kHz/26-channel S32_LE/128/512 and capture is closed. Rapid capture
  probes emitted no DMAR/IOMMU fault, DMA-stop timeout, or page-table timeout. Audible validation
  of the previous static regression is pending. No retry, rollback, second restart, playback command,
  or capture command occurred.
- **User-observed Linux active-page playback acceptance, 2026-08-16:** ordinary playback on
  srcversion `D1D19FA61C85B05A46E2A01` “sounds pretty good now.” The weird static introduced by the
  maximum-map predecessor is not reproduced in this immediate interval, supporting persistent
  table allocation with active-only page population. Longer listening is still required before a
  durable no-pop claim; capture publication remains a separate 13/0 failure.
- **User-observed Linux sustained playback acceptance, 2026-08-16:** continued ordinary gaming use
  on active-page srcversion `D1D19FA61C85B05A46E2A01` produced “no pops at all,” was “great,” and
  remained “super stable.” The maximum-map static and earlier intermittent pops did not reproduce
  in this longer real-world interval. Treat this as the strongest current playback acceptance and
  the release-performance playback candidate, while keeping native-44.1 duplex validation open.
- **Observed Linux delayed capture-graph recovery, 2026-08-16:** the activation controller's
  bounded 10-second checkpoint ended at 13 sinks/0 sources, but a later direct read-only `pw-dump`
  snapshot found the complete 13-sink/26-source Quantum graph without another restart or module
  action. Input 1 is node 95, `PreSonus Quantum 2626 Mic / Instrument Input 1`, with one `MONO`
  channel, the intended `quantum2626_mono_in:P2626,0,0` ALSA path, and normal suspended state while
  unlinked. Reclassify the earlier 13/0 result as a bounded startup checkpoint rather than the final
  stable graph. Capture remains closed; this proves publication, not native-44.1 duplex audio.
- **Observed Linux NeuralRack routing correction, 2026-08-16:** the locally built standalone
  NeuralRack launched at 44.1 kHz with a 256-sample JACK buffer. Its ports are typed
  `neuralrack:in` for MIDI, `neuralrack:in_0` for mono audio, and `out_0`/`out_1` for stereo audio.
  An incorrect audio-source link to the MIDI port was accepted by PipeWire; after the audio input
  was also linked, NeuralRack emitted an xrun and segfaulted in its own `pw-data-loop`. The Quantum
  hardware had reached exact joint 44.1 kHz/26-channel S32_LE/128/512 geometry and no Quantum,
  DMAR, or IOMMU fault appeared. After the client exited, its links disappeared, capture closed,
  and Firefox playback remained linked at the same geometry. This malformed-route crash is a
  userspace NeuralRack result, not native-44.1 duplex validation. A retry must connect Input 1 only
  to `neuralrack:in_0`, with `out_0`/`out_1` connected to Main left/right.
- **Observed Linux clean NeuralRack routing retry, 2026-08-16:** a fresh standalone client remained
  running at 44.1 kHz/256 JACK frames with exactly three audio links: Input 1 `capture_MONO` to
  `neuralrack:in_0`, `out_0` to Main left, and `out_1` to Main right. Both ALSA directions are open
  at matching 44.1 kHz/26-channel S32_LE/128/512 geometry. NeuralRack printed one connection-time
  xrun, but its process and links remained present and the bounded kernel log contained no Quantum,
  DMAR, IOMMU, timeout, fault, BUG, or oops marker. Audible guitar validation is pending.
- **User-observed and offline-classified NeuralRack model-enable crash, 2026-08-16:** the user heard
  the correctly routed live input, proving Input 1 -> NeuralRack -> Main audio flow, then NeuralRack
  crashed when its saved JC-40 model was enabled. A second userspace segfault occurred at the same
  executable offset `0x3904e` on a different CPU. An exact unstripped relink maps that offset to the
  `memcpy` immediately after model processing in `NeuralModelLoader::compute()`. That callback uses
  variable-length stack arrays for its model and resampling buffers. The saved model is
  `JC40_414_HIGH_DIST.nam`, a 48-kHz NAM 0.7 `SlimmableContainer`; the local loader supports that
  format. After the app exited, its links disappeared, capture closed, Firefox playback remained at
  exact native 44.1 kHz/26-channel S32_LE/128/512, and no Quantum, DMAR, or IOMMU fault appeared.
  Classify this as a NeuralRack realtime stack/model-processing failure, not a driver or routing
  failure. The narrow app-side fix candidate is to replace the realtime variable-length arrays with
  buffers allocated outside the process callback; do not retry or alter the stable audio stack as
  part of this diagnosis.
- **Offline NeuralRack realtime-buffer fix built, 2026-08-16:** a separate temporary build now
  replaces both variable-length arrays in `NeuralModelLoader::compute()` with member buffers sized
  only from non-realtime setup paths. It also sizes the model-processing capacity for the 44.1-to-
  48-kHz resampling expansion and returns dry audio if a callback exceeds the prepared capacity.
  The standalone build completed with no new diagnostic, links to PipeWire's JACK library, and is
  hash `a26a3ed9...dee8`; disassembly shows a fixed 24-byte `compute()` stack frame and no allocator
  call in that callback. This is offline integrity evidence only. The binary remains under
  `/tmp/neuralrack-debug.gY9Hq1/bin/Neuralrack`; no app launch, link, driver change, service restart,
  or live model processing occurred after the build.
- **User-observed fixed-build NeuralRack runtime result, 2026-08-16:** the fixed temporary binary
  launched and survived enabling the saved JC-40 model, proving the prior repeatable userspace
  segfault is removed. The intended Input 1 -> `in_0` and stereo Main links remained present, and
  both ALSA directions stayed exact 44.1 kHz/26-channel S32_LE/128/512. The user heard processed
  audio but reported many pops. During an eight-sample live snapshot, Main used only 0.02--0.03 of
  its deadline and Input 1 effectively zero; their accumulated PipeWire error totals remained fixed,
  with no new kernel or userspace crash marker. An offline exact resampler probe identifies an
  app-side discontinuity: for 256 input frames the existing 44.1 -> 48 -> 44.1 chain returns 253,
  255, 256, or 257 frames, while `NeuralModelLoader::compute()` ignores the return count and always
  copies 256. This leaves stale tails on short blocks and discards samples on long blocks, matching
  the frequent pops. Preserve the driver and live geometry; fix output-frame accumulation in the
  NeuralRack resampling path before another model test.
- **Offline NeuralRack resampling-continuity fix built, 2026-08-16:** after the user closed the live
  app, the separate candidate gained a preallocated circular output queue with an eight-frame
  priming cushion (about 0.18 ms at 44.1 kHz). Every variable-length resampler result is now retained
  and exactly one JACK block is consumed per callback; no allocation or sample discard occurs in
  `compute()`. A one-million-block exact 44.1 -> 48 -> 44.1 probe bounded cumulative production at
  -3..0 frames, and a 10,000-block 1-kHz continuity probe reduced the old path's maximum adjacent
  step from 0.449398 to 0.150643 with five queued frames remaining. The standalone build succeeds at
  hash `4c2913b3...321f`; disassembly shows one fixed 40-byte callback stack frame and no allocator
  call. This is offline evidence only. The updated binary remains
  `/tmp/neuralrack-debug.gY9Hq1/bin/Neuralrack`; it has not been launched or linked, and the Quantum
  driver, PipeWire configuration, services, and stable geometry were not changed.
- **User-observed overnight playback recurrence, 2026-08-17:** after the host and audio services
  remained up overnight, ordinary Firefox playback again had occasional relatively mild pops.
  PipeWire, PipeWire Pulse, and WirePlumber have remained active since 17:52 on August 16 with zero
  systemd restarts. NeuralRack is absent, capture is closed, and playback remains exact native
  44.1 kHz/26-channel S32_LE/128/512. The active Main node still runs at quantum 256 with playback
  headroom 256; the metadata `clock.quantum=1024` is an unforced global default, not its active
  hardware quantum. At 20:22 PipeWire logged one `spa.audioconvert` `out of buffers` event with one
  suppressed repetition. Main now has 29 accumulated errors and the active Firefox stream one,
  compared with 19 and zero around the prior NeuralRack checkpoint. Both totals stayed fixed across
  a subsequent 30-second sample; Main used at most 0.03 of its deadline and Firefox effectively
  zero. The kernel has no Quantum xrun, timeout, DMA/IOMMU fault, BUG, or oops. IRQ 213 advanced
  exactly 1,040 times in about three seconds and ALSA `hw_ptr` advanced 132,695 frames, matching
  44.1 kHz. The long-running trigger epoch and zero `appl_ptr` are consistent with Main's
  `node.pause-on-idle=false`, infinite ALSA silence threshold, and continuous PipeWire driver-node
  policy; they are not standalone proof of a stale driver engine. Current evidence localizes the
  audible return event to PipeWire buffer exchange while leaving the rarer steady-state pop
  unresolved. Do not change geometry or restart solely from this snapshot.
- **Observed Linux transient-clipping proof, 2026-08-17:** gain read-back shows Quantum Main at
  exactly 100%/0.00 dB, both initially visible Firefox streams at 100%/0.00 dB, and no additional
  exposed ALSA mixer gain. Thus 100% is unity, not hidden amplification. An initial approved
  float32 Main-monitor capture received 704,512 samples and measured peak magnitude 1.136673689
  (about +1.11 dBFS), with 311 samples at or above 1.0. Because the second stream was an idle
  ChatGPT tab, its uncorked state did not prove two audible streams were summing. After the user
  closed it, read-back confirmed only YouTube Music remained. A second approved isolated capture
  still measured 1.127280354 (about +1.04 dBFS), with 4,200 samples at or above 0.95, 1,174 at or
  above 0.99, and 790 at or above 1.0 out of 704,512. This proves the YouTube-only path itself
  exceeds float full scale at transients before conversion to the S32_LE hardware stream and can
  explain at least part of the transient-correlated crack/pop report. The temporary monitor exited;
  its graph transition advanced Main's error total once from 29 to 30 while Firefox remained zero,
  so do not use that increment as spontaneous-playback evidence. No volume, persistent route,
  service, driver, or geometry change occurred. Keep the distinct 20:22 PipeWire `out of buffers`
  event separately classified; peak overload does not explain that log.
- **User-observed clipping A/B rejection, 2026-08-17:** the same transient-correlated digital
  artifact remained unchanged after the sole YouTube Music stream was attenuated to 73%/-8.31 dB.
  This is far more headroom than the measured +1.04 dBFS peak excess, so clipping is real at unity
  but is not the audible artifact's root cause. During the attenuated observation, Main and Firefox
  error totals remained fixed at 30 and zero and realtime load remained negligible. Classify the
  remaining sound as a sample discontinuity below PipeWire's live error accounting; return to the
  dshare/ALSA pointer and hardware-period data path rather than adding a limiter or reducing user
  volume as a driver workaround.
- **Implemented, unverified, 2026-08-17:** the dependency-free
  `scripts/quantum2626_loopback_soak.py` harness and
  `docs/LOOPBACK_CONTINUITY_TESTING.md` runbook prepare a Line Out 3 to explicitly selected input
  continuity test. Offline fault injection cleanly detects repeated and skipped 128-frame periods
  and corrupted content while accepting gain, DC offset, and noise. The live path is fail-closed on ambiguous
  endpoints, geometry drift from native 44.1 kHz/26-channel S32_LE/128/512, clipping, stalled or
  exited processes, initial acquisition failure, disk pressure, or the configured event limit;
  later correlation loss is retained as an event rather than silently discarded. No endpoint was
  opened in this preparation step. Physical output identification, short calibration, and overnight
  playback/capture remain unobserved and require separate live authority.
- **Observed Linux and user-connected hardware, 2026-08-18:** a bounded -36 dBFS pulsed 660 Hz
  signal on Line Out 3 returned on ADAT Input 1, zero-based hardware channel 10 / ALSA channel 11,
  with a 44.64 dB spectral margin over every other input. The five-second raw scan retained exact
  native 44.1 kHz, 26-channel S32_LE, 128/512 duplex geometry under loaded srcversion
  `D1D19FA61C85B05A46E2A01`; the endpoint graph remained 13/26, capture closed afterward, and no raw
  audio was retained. This verifies the current Line Out 3 -> patch bay -> Digimax D8 Input 1 ->
  ADAT Input 1 path. Because the return includes the Digimax ADC and ADAT clock path, it can detect
  playback discontinuities but cannot alone assign them to the Quantum playback DMA path. The soak
  harness now accepts the exact ADAT Input 1 node as a runtime parameter. A short calibration and
  any overnight run remain separate live checkpoints.
- **Observed Linux five-minute continuity calibration, 2026-08-18:** the approved -30 dBFS Line
  Out 3 to ADAT Input 1 run completed 300.009 seconds and 3,227 analysis blocks with zero events.
  Every telemetry sample had zero phase delta; absolute correlation stayed between 0.969441 and
  0.981008 and the maximum captured peak was -49.2974 dBFS, confirming that minimum Digimax gain is
  sufficient with large clipping headroom. Both PCMs stayed at exact native 44.1 kHz, 26-channel
  S32_LE, 128/512. The selected sink/source and `pw-record` counters remained zero; `pw-play` had one
  fixed connection-time error from the first sample. The 305.003-second DMA epoch delivered 105,083
  interrupts, exact period cadence, with no kernel xrun, DMA/IOMMU fault, timeout, warning, BUG, or
  oops. Capture closed, helper stderr remained empty, and no event audio was created. This validates
  the harness and current level through the Digimax/ADAT return, not playback-DMA causality. A
  post-teardown registry check retained all 13 sinks and 26 sources, including ADAT Input 1. Any
  overnight soak remains a separately approved live checkpoint.
- **Observed Linux loopback soak terminal result, 2026-08-18:** the approved 28,800-second run
  failed closed at its 1,000-event ceiling after 346.221 seconds and 3,689 blocks, preserving all
  evidence under `/tmp/quantum2626-loopback-overnight-20260818-1`. Exact native
  44.1-kHz/26-channel/S32_LE/128/512 geometry held. The first 53 seconds were clean; later bursts
  repeatedly recovered to about 0.98 correlation. The terminal events comprise 968 correlation
  drops and 32 recovered phase jumps, including 20 exact +/-256-frame changes matching the active
  PipeWire quantum. Line Out 3 advanced 0->52 errors, `pw-play` 1->194, ADAT Input 1 0->2, and
  `pw-record` 0->174. PipeWire logged playback `snd_pcm_mmap_commit` `Broken pipe` and buffer
  starvation during dense bursts, while the kernel logged no DMA/IOMMU fault, timeout, warning,
  BUG, or oops and delivered 121,005 interrupts over the approximately 351.2-second DMA epoch at
  expected cadence. Both PCMs are closed and all helper stderr files are empty after teardown.
  This proves bursty ALSA/PipeWire xruns, not clipping or slow rate drift, but does not localize the
  first fault to the driver because the Digimax/ADAT return remains a confound and the harness could
  amplify a loss: low-correlation recovery takes about 37 ms versus 1.1 ms normally while its old
  playback feeder shared the Python interpreter.
- **Offline diagnostic correction, 2026-08-18:** the loopback playback feeder now runs in a
  dedicated process forked before telemetry threading, preventing analyzer GIL contention from
  starving `pw-play`. Three consecutive offline self-tests, bytecode compilation,
  `git diff --check`, and the existing driver `W=1` build pass. No driver, module, service, endpoint,
  or installed configuration changed. A short corrected calibration is the next separately
  authorized live discriminator; do not install or restart on the contaminated event count alone.
- **Observed corrected five-minute loopback calibration, 2026-08-18:** the separately authorized
  isolated-feeder harness completed 300.035 seconds and 3,227 blocks over the existing -30 dBFS
  Line Out 3 -> Digimax/ADAT Input 1 return with zero continuity events, zero phase displacement,
  correlation 0.975788--0.981085, and maximum peak -49.3026 dBFS. Both PCMs held exact native
  44.1-kHz/26-channel/S32_LE/128/512 geometry. The selected sink, source, and `pw-record` error
  counts stayed zero; `pw-play` gained one fixed connection-time error at 0.31 seconds. The
  305-second DMA epoch delivered 105,092 interrupts at expected cadence; helper stderr and bounded
  service logs are empty; the kernel logged only prepare/start/stop. Both PCMs closed, loaded
  srcversion remains `D1D19FA61C85B05A46E2A01`, and all 13 sinks plus 26 sources survived. This
  confirms that the old shared-interpreter feeder materially amplified the prior 1,000-event run;
  that run is not autonomous-driver-failure evidence. It does not negate ordinary-playback pops or
  localize their cause, and the Digimax/ADAT path remains a confound. Any longer corrected soak is
  a fresh live checkpoint; do not install or restart from the contaminated result.
- **Observed corrected long-run continuity result, classified 2026-08-18:** the isolated-feeder
  run retained exact native 44.1-kHz/26-channel/S32_LE/128/512 duplex geometry for 5,838.383
  seconds and 62,834 blocks. It was event-free for 3,890.338 seconds before captured sequence
  displacements and PipeWire error bursts began. The selected sink advanced 0->33 errors,
  `pw-play` 1->160, the selected source 0->3, and `pw-record` 0->148 while all four nodes retained a
  256-frame graph quantum. IRQ and ALSA hardware-pointer cadence remained steady, sampled graph
  busy ratios stayed low, and the retained phase jumps include 17 at +256 and 9 at -256 frames.
  High-correlation 256-frame slices on the first two event captures prove real sequence jumps. The
  corrected analyzer now performs complete-reference reacquisition, records only one event per
  global-lock-loss episode, logs recovery separately, and stops after 16 consecutive globally lost
  blocks. Focused fixtures reacquire a +1,024-frame displacement once and collapse five corrupt
  blocks to one event. Read-only replay of all 1,000 immutable captures used the corrected adaptive
  threshold of 0.68496938: 893 of 961 old correlation drops globally reacquired, 36 of 39 original
  phase jumps remained above threshold, and 71 captures remained globally unclassifiable. Median
  global correlation was 0.97852768. Treat the old count, ceiling, and apparent burst length as
  analyzer inflation, while retaining the real intermittent PipeWire-visible continuity failure and
  globally unclassifiable blocks. The isolated feeder rejects old GIL amplification as the sole cause;
  steady IRQ/pointer cadence supplies no positive driver-fault evidence; and the Digimax/ADAT return
  keeps playback, capture, converter, and clock locus confounded. No live state changed. Any direct-
  ALSA versus PipeWire or dual-return experiment remains a separately authorized live checkpoint.
- **Observed direct-return no-signal stop, 2026-08-18:** one approved corrected-harness invocation
  targeted the exact Line Outputs 3-4 sink and Line Input 3 source at -30 dBFS on the reported
  balanced Out 3 -> Input 3 cable. Exact native 44.1-kHz/26-channel/S32_LE/128/512 geometry was
  admitted, but capture remained below -60 dBFS and the harness failed closed after 10.288 seconds
  with zero analyzed blocks and zero events. Sink/`pw-play`/source/`pw-record` error counts remained
  fixed at 33/1/0/0, helper stderr is empty, no matching kernel or user-audio fault appeared, and
  the services plus exact endpoints survived. This is physical-path readiness evidence only: no
  usable signal reached the selected source under the reported monitoring-off/minimum-gain state.
  It does not identify whether cable placement, input mode/routing, gain, or source identity is
  wrong. The invocation is consumed; do not retry or alter level/routing without new exact
  authority. Evidence remains under
  `/tmp/quantum2626-loopback-direct-calibration-20260818-1`.
- **Observed adjusted-gain direct-return no-signal stop, 2026-08-18:** after the user reported
  increasing Input 3 gain, one separately approved 30-second check used the same exact endpoints,
  -30 dBFS stimulus, and native 44.1-kHz/26-channel/S32_LE/128/512 geometry. Capture again remained
  below -60 dBFS and stopped after 10.312 seconds with zero analyzed blocks/events. Error counters
  stayed fixed at 33/1/0/0, helper stderr remained empty, no matching fault appeared, and services
  plus endpoints survived. Minimum gain alone is now a weaker explanation; physical jack/input
  mode, cable/output path, or source identity remains unresolved. The check is consumed; no retry or
  path change is authorized. Evidence remains under
  `/tmp/quantum2626-loopback-direct-levelcheck-20260818-1`.
- **Observed higher-gain direct-return level pass, 2026-08-18:** after Input 3 gain was raised
  further, one approved 30-second check completed 30.027 seconds and 320 blocks on the exact Line
  Out 3 -> Line Input 3 path with zero events/loss episodes and zero phase delta. Absolute
  correlation was 0.98098128--0.98515020, RMS stayed -57.6709 to -57.5692 dBFS, and maximum peak
  was -47.2137 dBFS. Exact native 44.1-kHz/26-channel/S32_LE/128/512 geometry held; counters stayed
  fixed at 33/1/0/0; helper stderr and bounded fault logs were empty; and services plus endpoints
  survived. This proves the direct cable, output route, Input 3 binding, and physical input path.
  Earlier no-signal stops were caused by insufficient gain at those settings, not bad wiring or
  source identity. Preserve the current gain position. Evidence remains under
  `/tmp/quantum2626-loopback-direct-levelcheck-20260818-2`; any five-minute or longer direct-return
  continuity run remains separately authorized.
- **Observed five-minute direct-return continuity result, 2026-08-18:** one separately approved run
  completed 300.052 seconds and 3,227 blocks on the proven Line Out 3 -> Line Input 3 cable at the
  preserved gain. Exact native 44.1-kHz/26-channel/S32_LE/128/512 duplex geometry held. The
  corrected analyzer recorded two locked +256-frame phase jumps and two one-block global-lock-loss
  episodes, recovering at +256 and +512 frames without inflating either episode into a burst. The
  selected sink/`pw-play`/source counters held at 33/1/0 after connection while `pw-record` advanced
  0->4. Signal remained stable (-57.7177 to -57.5067 dBFS RMS; -47.2113 dBFS maximum peak).
  Capture/playback hardware pointers advanced 13,210,086/13,210,087 frames and IRQ count advanced
  103,204 across 299.534 seconds of telemetry. Helper stderr is empty; all services and endpoints
  survived; teardown closed every ALSA stream; and the bounded kernel log contains only normal DMA
  prepare/start/stop messages. This excludes the Digimax/ADAT converter, return, and external clock
  as necessary causes. Captured sequence displacement and PipeWire capture-helper errors are
  positive evidence, but steady IRQ/pointer cadence and no kernel fault remain absent positive
  driver-fault evidence; PipeWire, ALSA PCM handling, the driver, and the Quantum's own data path
  are not yet distinguished. Evidence is immutable at
  `/tmp/quantum2626-loopback-direct-calibration-20260818-2`; summary/events/`pw-top` SHA-256 are
  `c9d97180e96c62c378bac42b8c6c2b14f190934d8dd139b2c036f1816f5a97bf`,
  `133b0557101808eb6a47c2f683742938b47d684e0b3776f3adcd5560502a66fc`, and
  `cdff459a925254d1e5e423a9aa695dbbe42c4d8e3d07eaee4e1fcba74915f1cc`. This invocation is consumed;
  no retry or direct-ALSA/PipeWire A/B is authorized.
- **Observed rejected direct-ALSA arm and offline harness correction, 2026-08-18:** one approved
  five-minute arm opened `hw:P2626,0` directly on the same Line Out 3 -> Line Input 3 loop and exact
  44.1-kHz/26-channel/S32_LE/128/512 geometry. The initial backend analyzed synchronously while
  draining all 26 capture channels. Capture was already `XRUN` in the first telemetry sample;
  `arecord` logged 1,002 overruns, whose recoveries produced 1,000 high-correlation phase jumps and
  hit the safety ceiling at 269.237 seconds/1,468 blocks. Six later `aplay` underruns accompanied
  normal DMA restart cycles. PipeWire stayed suspended with zero node errors, teardown closed both
  ALSA directions, and no DMA/IOMMU/kernel fault appeared. Reject the raw event count and this arm
  as an ALSA-versus-PipeWire result: analyzer backpressure created the xruns and recovery jumps.
  Evidence remains under `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-1`; summary,
  events, and `pw-top` hashes are `3e5be71a...52251`, `304a5774...e9ad`, and
  `7a6d7bd0...d9d9`. The offline harness now drains 26-channel capture in a dedicated extractor,
  forwards channel index 2 as mono, makes helper xruns fatal, and fails if either PCM leaves
  `RUNNING`. Focused compile/self-test proof passes; corrected script SHA-256 is
  `f4c46ce2ca9c5a95ede332f41c0fdba4551f83f17441d2be62bfe5a65faff379`. The invocation is consumed;
  a corrected direct-ALSA retry requires fresh exact authorization.
- **Observed corrected direct-ALSA startup failure, 2026-08-18:** one separately approved exact
  invocation used the isolated capture extractor and fatal-xrun helpers, but `arecord` hit a fatal
  overrun before ALSA geometry validation. The run failed closed after 0.370 seconds with zero
  analysis blocks, continuity events, loss episodes, or signal measurements. `aplay` was
  interrupted during teardown and the extractor received a short final block after capture exited.
  Both PCMs closed; all three audio services, exact endpoints, and the complete 13/26 graph
  survived; and bounded kernel and user-audio run-window searches contained no matching fault. No
  IRQ or hardware-pointer cadence was admitted. This is positive direct-ALSA capture-helper xrun
  evidence, not positive driver-fault evidence. It neither reproduces nor excludes the PipeWire
  arm's four continuity events, so the ALSA-versus-PipeWire discriminator remains unresolved.
  Immutable evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-2`; summary/events/`pw-top` SHA-256 are
  `965b46e9...3b03`, `0113919e...21e`, and `44a9cf4b...77c0`. The invocation is consumed; do not
  retry, repair the harness, or switch backend under this authority.
- **Offline direct-ALSA startup correction, 2026-08-18:** the live failure is localized to harness
  process ordering. The old path started `arecord` before its Python extractor; 26-channel S32_LE
  capture produces 4,586,400 bytes/second, filling this host's 65,536-byte pipe in 14.289 ms versus
  an 11.610-ms 512-frame hardware buffer. The failed extractor's 66,560-byte final read matches
  that startup ceiling. The harness now starts the extractor first, waits for an explicit readiness
  signal, and only then launches `arecord` into the draining pipe. Focused bytecode compilation,
  analyzer/extractor fixtures, the new readiness-handshake fixture, and `git diff --check` pass.
  Corrected script SHA-256 is `d42b8cb5...d9c7b`. This is offline proof only; no driver, service,
  module, endpoint, or device state changed. A live validation requires fresh exact authority.
- **Observed readiness-corrected direct-ALSA result, 2026-08-18:** the exact live arm admitted
  native 44.1-kHz/26-channel/S32_LE/128/512 duplex geometry and analyzed 576 blocks for 53.879
  seconds before failing closed. The startup overrun did not recur. All admitted blocks had zero
  phase delta and zero continuity events/loss/recovery; absolute correlation remained at least
  0.98082945, RMS was -27.2228 to -27.1022 dBFS, and maximum peak was -16.8142 dBFS. Across 53.179
  seconds of telemetry, both hardware pointers advanced 2,345,311 frames and IRQ count advanced
  18,323 at exact cadence. Capture/playback `avail_max` reached 483/494 of 512 immediately before
  `arecord` reported a fatal overrun and `aplay` a fatal underrun; capture EOF then stopped the
  analyzer. PipeWire kept the exact nodes suspended at zero errors. Both PCMs closed, all services
  and the 13/26 graph survived, and bounded fault logs were empty. This proves PipeWire is not
  necessary for this direct-ALSA duplex xrun, but no direct-ALSA continuity event preceded it, so
  it does not establish that the PipeWire arm's four sequence events share the same cause. Exact
  cadence and empty fault logs remain absent positive driver-fault evidence. Evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-3`; summary/events/`pw-top` hashes are
  `513b8494...f79a2`, `bb312953...ba622`, and `2c09420d...1f416`. The invocation is consumed; no
  retry or repair is authorized by this gate.
- **Offline direct-ALSA starvation diagnosis and instrumentation, 2026-08-18:** steady-state phase
  analysis costs 1.211 ms median/1.967 ms p95 per 92.880-ms block; the 117.967-ms maximum belongs
  to initial full-reference acquisition. The failed live arm performed no later global search, and
  its old mono pipe held about 371.5 ms, so analyzer throughput did not cause the terminal xrun.
  The execution context has `RLIMIT_RTPRIO=0`, and `aplay`, `arecord`, and Python have no scheduler
  capabilities; absent explicit promotion they run `SCHED_OTHER`, unlike PipeWire's current
  `SCHED_RR/20` data loops. The old 65,536-byte raw pipes held only 14.289 ms of 26-channel audio.
  The harness now requires 1-MiB playback, raw-capture, and mono-analysis pipes, adding 228.6 ms of
  raw and 5.94 seconds of mono headroom without changing ALSA's 128/512 geometry. It also records
  policy, priority, nice level, context switches, runtime, scheduler wait, and timeslices for all
  four direct helper processes each second. Compile/self-test, pipe-resize, telemetry fixtures, and
  `git diff --check` pass; script SHA-256 is `fe7a9f0b...aa634`. No scheduling policy, driver,
  service, endpoint, module, or device state changed. RTKit promotion remains a separate hypothesis,
  not an authorized or evidence-backed correction yet.
- **Observed 1-MiB-pipe direct-ALSA result, 2026-08-18:** the exact live arm admitted native
  44.1-kHz/26-channel/S32_LE/128/512 duplex geometry and analyzed 999 blocks over 93.181 seconds.
  Phase delta and continuity/loss/recovery counts stayed zero; absolute correlation remained at
  least 0.98110169, RMS was -27.2492 to -27.0798 dBFS, and maximum peak was -16.8142 dBFS. Across
  91.988 seconds of telemetry, capture/playback pointers advanced 4,056,916/4,056,907 frames and
  IRQ count advanced 31,695 at exact cadence. All four helper processes were `SCHED_OTHER` nice +6.
  Their largest sampled wait increments were 7.355 ms (`arecord`), 7.545 ms (`aplay`), 2.093 ms
  (extractor), and 1.667 ms (feeder). Capture/playback `avail_max` peaked at 380/326, below the prior
  arm's 483/494. After the final sample, `arecord` hit one fatal overrun and capture EOF stopped the
  analyzer; `aplay` was interrupted only during teardown and did not report an underrun. PipeWire
  stayed suspended at zero errors, both PCMs closed, services and the 13/26 graph survived, and
  bounded fault logs were empty. Larger pipes removed the reproduced playback-side failure in this
  arm but did not prevent a later direct-capture overrun. The terminal 0.627-second gap lacks a final
  scheduler snapshot, so scheduling causation remains unproven; stable cadence and empty fault logs
  remain absent positive driver-fault evidence. Evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-4`; summary/events/`pw-top` hashes are
  `de872eff...fb11`, `f701b6a8...df9e`, and `6de43a35...c4870`. The invocation is consumed; no retry,
  RTKit change, or repair is authorized by this gate.
- **Offline terminal-evidence correction, 2026-08-18:** live supervision now detects helper exit
  without reaping via `waitid(..., WNOWAIT)`. A failure writes current ALSA status/geometry and any
  still-exposed pointers, IRQ count, final helper process/scheduler counters, and non-reaped
  child-exit state to `terminal_snapshot` before any teardown; an already-closed PCM is recorded as
  closed rather than reconstructed. `teardown_complete` and summary return codes then order
  teardown-induced exits separately. The offline fixture proves the exited child remains readable
  until explicit reaping. Compile/self-test and `git diff --check` pass; script SHA-256 is
  `d8e28c0d...51eb0`. No live audio, scheduling promotion, driver/service/device change, or new
  causal conclusion occurred. Another discriminator run remains a separately approved boundary.
- **Observed terminal-evidence direct-ALSA result, 2026-08-18:** the consumed exact arm admitted
  44.1-kHz/26-channel/S32_LE/128/512 geometry and all three 1-MiB pipes, then analyzed 452 clean
  blocks over 42.431 seconds before capture EOF. It recorded zero phase/continuity/loss/recovery
  events, minimum absolute correlation 0.98068229, RMS -27.2139 to -27.1011 dBFS, and maximum peak
  -16.8108 dBFS. The terminal snapshot proved `arecord` had exited 1 as an unreaped zombie after
  one fatal overrun while playback and the other helpers were still running; playback remained
  `RUNNING`, had empty stderr, and exited 0 only during teardown. Maximum sampled one-second
  cumulative scheduler-wait increases were 160.109 ms (`arecord`), 247.997 ms (`aplay`), 23.022 ms
  (extractor), and 10.114 ms (feeder); terminal-interval capture/playback increases were
  103.170/232.168 ms. This is positive severe scheduler contention aligned with the failure, but
  cumulative wait does not prove a single stall exceeded the 11.610-ms buffer. IRQ cadence was
  344.548/s versus 344.531/s expected, playback pointer cadence was 44,101.6 frames/s, and the
  driver logged 14,615 normal interrupts plus only normal DMA start/stop. PipeWire nodes remained
  suspended at zero errors, both PCMs closed, services/endpoints 186/77 survived, and no driver
  fault appeared. Evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-calibration-20260818-5`; summary/events/`pw-top` hashes are
  `2d8d6bc7...91056`, `d432b361...ea4c9`, and `c7613584...987c0`. The gate is consumed; no retry or
  RTKit change is authorized. A separately approved RTKit/per-dispatch-latency A/B is now the
  appropriate discriminator while exact native transport and the active-page driver candidate
  remain unchanged.
- **Offline RTKit direct-helper A/B readiness, 2026-08-18:** the active host RTKit service supports
  same-user `MakeThreadRealtimeWithPID`, maximum RR priority 20, and 200,000-us RT runtime. The
  harness now has a direct-ALSA-only `--rtkit-helper-priority 20` mode that applies RTKit's bounded
  RTTIME/reset-on-fork prerequisites to only `aplay`/`arecord`, requests RR/20 for their main
  threads, and fails unless that policy remains exact at admission and every telemetry sample.
  Feeder/extractor remain `SCHED_OTHER`; exit removes promotion, with no global reset or service,
  driver, or geometry change. Offline prerequisite/command/policy fixtures, PipeWire rejection,
  compile/self-test, and `git diff --check` pass; script SHA-256 is `84b2755a...04a67`. `perf` is
  absent and `/proc/<pid>/sched` has no individual wait maximum, so no per-dispatch latency claim is
  available. No RTKit request or audio open occurred. The exact live A/B is a fresh one-shot gate.
- **Observed rejected RTKit A/B, 2026-08-18:** the consumed exact gate received successful RTKit
  replies and proved both ALSA helpers RR/20 with reset-on-fork through 13.779 seconds. It analyzed
  156 clean blocks with zero continuity/loss/recovery events, minimum correlation 0.98118544, RMS
  -27.1882 to -27.1276 dBFS, and maximum peak -16.8122 dBFS. RT runqueue wait stayed at only
  18,718/4,286 ns for playback/capture. At 14.802 seconds, both helpers and PCMs were still running
  at exact 44.1-kHz/26-channel/S32_LE/128/512 geometry but both policies simultaneously reverted to
  `SCHED_OTHER`/0 with reset-on-fork cleared, so the harness failed closed before any xrun.
  `arecord` stderr is empty; playback/extractor errors are teardown-induced. RTKit logs prove the
  initial promotions but contain no reset marker. Its default 5-second canary/10-second watchdog is
  timing-consistent with the demotion, but watchdog or external reset remains inferred; recorded
  helper runtime stayed below the 200-ms RTTIME bound. Pointer/IRQ cadence remained exact, the
  driver logged only normal start/stop and 5,099 interrupts, PipeWire counters stayed zero, PCMs
  closed, and services/endpoints 186/77 survived. Evidence is under
  `/tmp/quantum2626-loopback-direct-alsa-rtkit-calibration-20260818-6`; summary/events/`pw-top`
  hashes are `dd396b59...b2295`, `72daa03c...57433`, and `54acc737...2c09e`. The gate is
  `consumed_failed`; no retry, RTKit reset/service change, or clean-A/B claim is authorized.
- **Read-only RTKit demotion attribution, 2026-08-18:** the active exact System76 Scheduler override
  (`48f1743e...ee677`) enables execsnoop but excepts only PipeWire binaries; `aplay`/`arecord` are
  unexcepted. Exact installed source commit `8651bbf` already proves that a profile without
  `sched=` defaults to `SCHED_OTHER`, walks every thread, and calls `sched_setscheduler()`;
  execsnoop applies assignments to new processes independently of the 60-second refresh. That
  positive config/source path matches the helpers' joint creation and simultaneous normalization.
  Conversely, RTKit logged no compiled-in canary-starvation or known-thread-demotion marker, helper
  runtime stayed below RTTIME, and the identical `aplay`/`arecord` ELF plus `libasound` import no
  scheduler-changing API. Classify System76 Scheduler as the high-confidence demoter while keeping
  the exact untraced setter call inferred. No live or host state changed. A future A/B requires one
  privileged gate to add only the two helper exceptions and reload System76 Scheduler, then a
  separately approved audio gate; neither is authorized by this attribution.
- **Consumed-failed System76 helper-exception gate, 2026-08-18:** the exact host-view preflight
  passed immediately before the one approved invocation, proving the sealed controller
  (`2289ed59...0f6`), checkout, config, unit, daemon, service, exception counts, target digest, and
  absent backup/temp paths. The exact `sudo` command was invoked once and exited 1 because a
  terminal was required to read the password; the controller never started. Post-failure read-back
  keeps `/etc/system76-scheduler/config.kdl` at the before hash (`48f1743e...ee677`), `root:root`
  mode 0644, with exceptions `pipewire=1`, `pipewire-pulse=1`, `aplay=0`, and `arecord=0`; target
  hash `01fe04b4...846` was not installed. The backup/receipt and temporary candidate paths remain
  absent. Unit (`e97648c1...f88d`), daemon (`77889453...7775`), and loaded/active/running,
  reload-capable service state remain exact; the current `ReloadResult=success` predates or is
  otherwise unattributable to this failed invocation. The gate is `consumed_failed`, attempt count
  one, with no retry or recovery authority. No repository, config, service, audio, module,
  endpoint, device, or process-policy state changed. Never replay V1; helper-exception recovery and
  a later RTKit direct-ALSA A/B each require a newly sealed, separately approved gate.
- **Offline System76 helper-exception V2 readiness, 2026-08-18:** a genuinely new controller
  (`ec6485e4...0cce`) and gate packet (`07304f4a...fc84`) use fresh V2 backup/temp paths and preserve
  the same exact two-line candidate (`01fe04b4...f0846`). Exact entry is now desktop-authenticated
  `/usr/bin/pkexec /bin/bash /tmp/quantum2626-task002-system76-helper-exceptions-v2.sh --execute`;
  host inspection proves the sealed `pkexec` binary (`441f1eb9...2dbf`), root-owned mode 4755, and
  administrator-authenticated PolicyKit action. The host-view preflight passes against the exact
  before config, service artifacts/state, exception counts, target digest, checkout, and absent V2
  paths. This is offline readiness only: attempt count is zero, authority is unconsumed, and exact
  approval of the now-sealed invocation plus a one-shot task are still required. V2 authorizes no
  audio, fallback, retry, repair, cleanup, rollback, or later A/B.
- **Consumed-failed System76 helper-exception V2 result, 2026-08-18:** the exact approved PolicyKit
  invocation began once; the controller exited 0 and reported completion after checking its backup
  and candidate, the installed config, reload result, service-process and active-enter continuity,
  and the unit/daemon anchors. Independent bounded read-back proves
  `/etc/system76-scheduler/config.kdl` is exact target `01fe04b4...f0846`, `root:root` mode 0644,
  with exceptions `pipewire=1`, `pipewire-pulse=1`, `aplay=1`, and `arecord=1`. The scheduler remains
  loaded/active/running and reload-capable with `ReloadResult=success`; unit (`e97648c1...f88d`) and
  daemon (`77889453...7775`) hashes remain exact, and the active temporary config is absent. The V2
  backup directory exists `root:root` mode 0700, but the independent reader could not traverse it,
  so presence and hashes for the backup, candidate, and receipt remain unknown; descendant `absent`
  results are permission projections, not absence evidence. The missing required independent
  artifact read-back makes the single-use gate `consumed_failed` despite positive installed-config
  and controller proof. Never replay V1 or V2 or use privileged access to fill the missing hashes.
  Any later RTKit direct-ALSA A/B remains a fresh, separately sealed and explicitly approved
  one-shot audio gate; this result authorizes no audio, retry, repair, cleanup, rollback, or gate
  preparation.
- **Offline RTKit direct-ALSA post-exception gate readiness, 2026-08-18:** fresh gate
  `TASK-002-DIRECT-ALSA-RTKIT-AFTER-EXCEPTIONS-V1` holds the same five-minute native
  44.1-kHz/26-channel/S32_LE/128/512, -30-dBFS, direct channel-3 return, 1-MiB-pipe, and helper RR/20
  comparison as spent arm `-6`, using absent output path
  `/tmp/quantum2626-loopback-direct-alsa-rtkit-calibration-20260818-7`. Its intended causal
  prerequisite delta is only the installed aplay/arecord scheduler exceptions. Exact preflight
  (`84197a85...c7fb3a`) passes against the protected checkout and harness, config, active-page
  module, installed desktop defaults, 13/26 graph and endpoints, services, RTKit limits, closed
  PCMs, offline self-test, and output absence. Gate packet (`7e8a9013...0206e`) is sealed; attempt
  count remains zero and authority unconsumed. No audio or RTKit request occurred. Execution still
  requires fresh exact approval confirming the Output 3 to selected Input 3 return and direct
  monitoring off; preparation approval does not authorize the run.
- **Observed clean five-minute post-exception RTKit direct-ALSA result, 2026-08-18:** the separately
  authorized `-7` gate completed once in 300.05 seconds at exact native
  44.1-kHz/26-channel/S32_LE/128/512 duplex geometry. It analyzed 3,227 blocks with zero continuity
  events, loss episodes, recoveries, lost blocks, or phase delta; minimum absolute correlation was
  0.9807085, RMS stayed -27.2806 to -27.0435 dBFS, maximum peak was -16.8119 dBFS, and every
  telemetry sample remained locked. RTKit successfully promoted both helpers, and all 295 samples
  from admission through the 294 telemetry points kept `aplay`/`arecord` at `SCHED_RR/20` with
  reset-on-fork true; feeder/extractor remained `SCHED_OTHER/0`. Maximum cumulative sampled wait
  was 3.929/3.100 ms for playback/capture and 6.759/7.754 ms for feeder/extractor. Both PCMs stayed
  `RUNNING`, `avail_max` peaked at 180/275 frames, pointer deltas matched at about 44,102.066
  frames/s, and IRQ cadence was 344.545/s versus 344.531/s expected. ALSA helper and `pw-top`
  stderr were empty. Duration stop preceded teardown, so capture-helper exit 1 and the extractor's
  interruption/short final block are teardown-induced. Kernel evidence contains only normal DMA
  prepare/start/stop and no positive driver or general fault marker. PCMs closed afterward;
  services, endpoints, the 13/26 graph, and exact config/module/UCM/WirePlumber/checkout anchors
  survived unchanged. Evidence remains immutable under
  `/tmp/quantum2626-loopback-direct-alsa-rtkit-calibration-20260818-7`; summary/events/`pw-top`
  hashes are `020af763...d796`, `abbdf4e7...1eef`, and `f0c419a7...4eca`. Spent arm `-6` used the
  same comparison but lost both successful RTKit policies at 14.802 seconds; the intended
  prerequisite delta was the installed exact System76 exceptions for `aplay`/`arecord`. This
  supports the exceptions as preventing that observed demotion and permitting the clean five-minute
  run. The precise untraced System76 setter call, permanent scheduling or audible-crackle
  elimination, and PipeWire equivalence remain inferred or unproven. The event-free sequence covers
  only the reported direct Line Out 3 -> Line Input 3 analog return; it excludes the Digimax/ADAT
  return confound but does not validate other physical or digital routes. Empty driver-fault logs
  are absent positive evidence, not proof of impossibility. The gate is consumed; never replay `-6`
  or `-7` or infer another live, privileged, repair, cleanup, or publication action.
- **Observed Linux:** the user manually installed exact module `c4e874b6...88bc` and invoked
  corrected activation controller `8a32bf0f...33e2`. Loaded srcversion
  `7B1636C1FDE52CD275CAC7C` now owns PCI `1c67:0104`; all five user-audio units are active and the
  complete 13-sink/26-source Quantum graph returned. Playback reopened at 44.1 kHz, 26-channel
  S32_LE, 128/512 geometry with capture closed, and the bounded kernel log has no xrun, DMA fault,
  timeout, warning, BUG, or oops. This validates activation and preserves the playback-only
  control; it does not yet validate a capture late join or capture teardown.
- **Observed Linux and offline A/B preparation, 2026-08-16:** before capture opened, persistent
  YouTube Music pops survived a ten-second pause. Playback stayed at native 44.1 kHz, 26-channel
  S32_LE and 128/512; PipeWire and kernel logs showed no xrun or fault, IRQ cadence remained exact,
  CPU0 C2/C3 stayed frozen, and PipeWire's data loops remained `SCHED_RR/20`. This makes the loaded
  duplex candidate's playback-side buffer-lifecycle change the next discriminator rather than a
  failed QoS, scheduling, geometry, or capture transition. The source is now byte-exact to the
  prior QoS-only control `a99ce31b...ef937`; checkpatch 0/0, `W=1`, and `git diff --check` pass, and
  the rebuilt module is exact `b6f261d0...025b`, srcversion `BB865ACB071304AE53DE91D`. The duplex
  module remains installed and loaded pending separately authorized A/B installation and activation.
- **Observed Linux installation boundary, 2026-08-16:** fresh one-shot controller
  `bf3cee9d...7c69` installed exact QoS-only module `b6f261d0...025b`, srcversion
  `BB865ACB071304AE53DE91D`, root-owned mode 0644. The loaded duplex srcversion remains
  `7B1636C1FDE52CD275CAC7C`; all five audio units stayed active and playback stayed RUNNING at
  native 44.1 kHz, 26-channel S32_LE, 128/512. Installation is complete but inactive; no module
  reload, service restart, capture operation, or runtime validation occurred.
- **Observed Linux QoS-only playback A/B activation, 2026-08-16:** fresh controller
  `ae35ee91...e4ac` returned exit 1 without output after one invocation, but bounded read-back proves
  the complete requested state: exact srcversion `BB865ACB071304AE53DE91D` is loaded, PCI is bound,
  all five audio units are active, the 13/26 graph returned, and playback reopened at native
  44.1 kHz, 26-channel S32_LE, 128/512. IRQ cadence remained exact and CPU0 C2/C3 stayed frozen;
  no kernel fault appeared. One old-process `out of buffers` marker occurred at activation time and
  did not establish a settled error. The gate is completed by read-back with no retry. Listening
  now distinguishes this prior QoS-only playback implementation from the duplex candidate.
- **User-observed QoS-only playback A/B result, 2026-08-16:** pops remain, perhaps somewhat reduced.
  The duplex persistent-buffer change is therefore not the root cause, although it may modestly
  worsen susceptibility. The defect survives native 44.1 kHz/128/512, 256-frame device headroom,
  `slowptr true`, 2-us QoS, correct average IRQ cadence, and real-time PipeWire loops without a
  settled xrun marker. Test graph scheduling separately before changing the driver again.
- **Observed Linux rejected graph-quantum A/B, 2026-08-16:** forcing PipeWire's runtime graph
  quantum from automatic to 512 changed Main from 256 to 512 while native 44.1 kHz and hardware
  128/512 remained intact. Two switch-time PipeWire errors then stayed flat, but the user heard
  roughly double-speed, corrupted playback. The separately authorized reset to
  `clock.force-quantum=0` restored Main quantum 256 and normal Firefox timing without a restart.
  Do not use forced graph quantum 512 as a crackle fix.
- **Observed Linux graph recovery, 2026-08-16:** because the existing stream remained audibly
  corrupted after the metadata reset, a separately authorized restart of only the five user audio
  units rebuilt the graph. The driver was not reloaded. All five units are active, the full 13/26
  graph returned, force-quantum remains 0, Main is RUNNING at quantum 256 with zero fresh errors,
  Firefox is RUNNING with zero errors, and native hardware geometry remains 44.1 kHz/128/512.
- **User-observed immediate recovery acceptance, 2026-08-16:** playback returned to normal speed
  with no audible pops. Main and Firefox stayed at zero errors, IRQ cadence remained exact, and
  CPU0 C2/C3 remained frozen. The repeated `out of buffers` journal lines were emitted by the
  pre-restart PipeWire PID 766239; current PID 788726 has no matching error. Preserve this graph
  for longer listening before claiming durable resolution.
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
3. Preserve native 44.1 kHz, 128/512 hardware geometry, playback `slowptr true`, 256-frame
   playback headroom, and the proven scheduler policy. Exact active-page module
   `d54f2bf4...b45e`, srcversion `D1D19FA61C85B05A46E2A01`, is installed and loaded; its delayed
   settled graph is 13/26 with Input 1 correctly published. The next live boundary is launching
   only the separately built fixed NeuralRack binary, routing Input 1 `capture_MONO` to its audio
   `in_0`, then `out_0`/`out_1` to Main left/right, and enabling the saved JC-40 model without a
   restart or configuration change. Do not route audio to NeuralRack's MIDI-only `in` port.
   Do not combine it with IRQ affinity, geometry, higher-rate, external-clock, hot-removal, or
   playback-default changes.
