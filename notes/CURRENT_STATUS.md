# Quantum 2626 Linux Driver — Current Status

**Last updated:** 2026-08-16
**TL;DR:** Static analysis of the vendor's macOS DriverKit extension recovered the TCI mailbox,
audio page tables, IRQ contract, rate setter, and rate-dependent channel order. The installed Linux
module reaches the solid-blue ready state and implements native 44.1/48/88.2/96/176.4/192 kHz
selection with 26/18/8-channel profiles. Direct and ordinary Firefox playback at 44.1 kHz are now
live-proven at 26-channel S32_LE with 128-frame periods and a 512-frame buffer; the first native-rate
desktop listening result had no clicks and zero graph errors. Direct capture, physical
headphone-left/right output, and bounded PipeWire duplex remain live-proven at 48 kHz. Higher rates,
mixer controls, MIDI, hot removal, and physical S/PDIF/ADAT routing remain unproven.

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
  `74422a1675292015f0e622f21a8cc99550adb975d1ab1650c97c416fa6608a28`, srcversion
  `1DA82813C64453A1BC965D9`.
- **Observed Linux:** WirePlumber is active with 13 Quantum sinks and 26 mono Quantum sources; Main
  is the configured default sink.
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
3. Preserve the active 44.1 kHz desktop configuration and use longer ordinary listening to assess
   whether the earlier intermittent crackle is fully eliminated. Keep explicit capture tests and
   every higher-rate profile out of that observation.
   Do not test 88.2/96/176.4/192, external clocking, latency QoS, hot removal, or JACK in that first
   rate-switch checkpoint.
