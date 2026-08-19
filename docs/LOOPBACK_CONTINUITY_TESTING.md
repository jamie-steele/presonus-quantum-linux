# Quantum 2626 Analog Loopback Continuity Testing

## Purpose

This test turns an intermittent audible pop into timestamped sample-continuity evidence. It sends a
deterministic low-level sequence through one Quantum 2626 line output, returns it directly to one
Quantum 2626 line input, and tracks the captured sequence for skipped, repeated, or corrupted
samples. It also records ALSA pointer state and IRQ count once per second.

The test is deliberately split into offline preparation, a short live calibration, and a longer
soak. Building or running the offline self-test does not authorize opening playback or capture.

## Exact Test Path

The preferred direct analog path is:

```text
PipeWire Line Outputs 3-4, left channel
  -> physical Quantum Line Out 3
  -> one direct balanced patch cable
  -> physical Quantum Line Input 3
  -> PipeWire Line Input 3 mono source
```

The repository's current channel map identifies both hardware channels as zero-based channel 2.
The harness requires one unique PipeWire sink containing
`quantum2626_stereo_out_P2626_0_2_3__sink` and one unique source containing
`quantum2626_mono_in_P2626_0_2__source`. It stops if either endpoint is absent or ambiguous.

The currently connected patch was measured on 2026-08-18 as:

```text
Quantum physical Line Out 3
  -> patch bay
  -> Digimax D8 analog Input 1 and ADC
  -> optical ADAT
  -> Quantum ADAT Input 1
  -> hardware zero-based channel 10 / ALSA channel 11
```

A five-second 660 Hz scan found the signature on ADAT Input 1 with a 44.64 dB margin over every
other input while exact 44.1-kHz/26-channel/S32_LE/128/512 duplex geometry held. For this wiring,
pass `quantum2626_mono_in_P2626_0_10__source` explicitly as the capture fragment. This path is
useful for finding playback discontinuities, but it includes the Digimax ADC and ADAT clock path;
it is not equivalent to the preferred direct Quantum analog return.

The mixer may be used briefly to identify physical Line Out 3 at the patch bay. It must not remain
in the final loop. The overnight path is Quantum output directly to Quantum input.

## Safety And Invariants

Before any live command:

1. Turn direct/input monitoring off so the returned signal cannot feed back to the output.
2. Disconnect or mute speakers and headphones while identifying the patch.
3. Confirm either the preferred direct Line Input 3 return or the documented Digimax Input 1 to
   ADAT Input 1 return. Do not include a synth output or active mixer bus.
4. Begin at the harness default `-30 dBFS`. The harness refuses levels above `-20 dBFS` or below
   `-50 dBFS`.
5. Preserve the accepted desktop baseline: native 44.1 kHz, 26-channel S32_LE, 128-frame hardware
   periods, and a 512-frame hardware buffer. Do not combine this test with a service restart,
   module change, UCM/WirePlumber edit, graph-quantum override, or CPU-policy experiment.

After it opens both directions, the harness reads `/proc/asound/P2626` and aborts unless both PCMs
have the exact baseline geometry. It also aborts on endpoint/process loss, capture at or above 0.95
full scale, failure to acquire the sequence, loss of the required geometry, low disk space, the
configured event limit, or failure to regain global phase lock within 16 analysis blocks (about
1.49 seconds of captured audio).

The harness opens the test playback first and then joins capture 250 ms later. This preserves the
accepted playback-first control and intentionally exercises the driver's late-capture path. It does
not restart the graph or unload/reload the driver before or after the run.

## Offline Preparation

The analyzer is self-contained Python 3 and does not require NumPy, SciPy, JACK, a DAW, or a new
system package. Its offline proof injects clean/noisy transport, repeated and skipped 128-frame
periods, a displacement beyond the former local search window, and persistent loss followed by
recovery:

```bash
cd /home/jamie/source/Quantum2626
python3 -m py_compile scripts/quantum2626_loopback_soak.py
python3 scripts/quantum2626_loopback_soak.py self-test
```

Expected distinguishing output includes:

```json
{"beyond_window_delta_frames":1024,"capture_extractor_ready_handshake":true,"direct_alsa_pipe_bytes":1048576,"isolated_pipewire_capture":true,"persistent_loss_events":1,"pipewire_capture_buffer_seconds":5.944308,"pipewire_capture_pipe_bytes":1048576,"pipewire_data_loop_telemetry":true,"pipewire_error_transition_telemetry":true,"process_scheduling_telemetry":true,"recovered_after_blocks":5,"repeated_period_delta_frames":-128,"result":"pass","rtkit_helper_ab_prepared":true,"skipped_period_delta_frames":128,"terminal_snapshot_before_reap":true,"thread_scheduling_telemetry":true}
```

`replay` performs a read-only global classification of every retained event capture. It validates
the log sequence, capture names, uniqueness, and exact block size, but creates or changes no file in
the artifact directory:

```bash
python3 scripts/quantum2626_loopback_soak.py replay \
  --artifact-dir /tmp/quantum2626-loopback-overnight-corrected-20260818-2
```

`globally_reacquired` means an old correlation-drop capture has a stable global match and was an
artifact of local loss-of-lock. `global_correlation_drop` means even the global search remains below
the adaptive lock threshold; it is retained as genuinely unclassifiable captured content.

`inspect` reads the current PipeWire registry but does not open either audio direction. For the
currently connected Digimax/ADAT return, use:

```bash
python3 scripts/quantum2626_loopback_soak.py inspect \
  --capture-fragment quantum2626_mono_in_P2626_0_10__source
```

It must return exactly the intended Line Outputs 3-4 sink and Line Input 3 source. Endpoint names
are treated as test inputs, not guessed or silently replaced.

## Live Calibration

Playback and capture are live hardware operations. Run calibration only after the direct cable is
in place and that exact action is approved.

Use a new output directory; the harness refuses to overwrite one:

```bash
python3 scripts/quantum2626_loopback_soak.py run \
  --duration 05:00 \
  --output-dir /tmp/quantum2626-loopback-calibration \
  --level-dbfs -30 \
  --capture-fragment quantum2626_mono_in_P2626_0_10__source \
  --live-ack OUT3-PATCHED-TO-SELECTED-INPUT-MONITOR-OFF
```

Calibration is accepted only when all of the following hold:

- the physical path is confirmed as Out 3 to the explicitly selected return endpoint;
- both ALSA directions read back as 44.1 kHz, 26-channel S32_LE, 128/512;
- the captured peak remains below -6 dBFS and above the no-signal floor;
- initial absolute correlation is at least 0.45 and stays stable;
- the program reaches `duration_complete` without a fail-closed stop;
- any detected continuity event can be compared with the user's audible observation.

A short calibration may show a stable nonzero phase offset. That is normal converter, graph, and
buffer latency. A phase offset that suddenly changes is the continuity defect of interest.

### Direct-ALSA RTKit A/B

`--rtkit-helper-priority 20` is an opt-in live scheduling mutation for the direct-ALSA discriminator;
it is invalid with PipeWire transport and requires its own exact approval. Before each helper exec,
the harness sets RTKit's required 200,000-us `RLIMIT_RTTIME` and `SCHED_RESET_ON_FORK`, then requests
RR/20 only for the `aplay` and `arecord` main threads through
`MakeThreadRealtimeWithPID`. The feeder and extractor remain `SCHED_OTHER` controls. The harness
fails before geometry admission unless both ALSA helpers read back as RR/20 with reset-on-fork, and
it revalidates that policy every telemetry interval. Process exit removes the promotion; the mode
does not reset RTKit globally, restart a service, change ALSA geometry, or change the driver.

The A/B command retains the exact direct transport and adds only:

```bash
--transport alsa --rtkit-helper-priority 20
```

This host does not provide `perf`, and its `/proc/<pid>/sched` view has no per-dispatch wait maximum.
Therefore `schedstat` remains cumulative contention evidence. The controlled RR/20 outcome is the
causal discriminator: a clean full-duration arm supports scheduling sensitivity; another overrun
with policy continuously verified moves diagnosis back toward ALSA/capture-period accounting.

## Overnight Soak

Do not begin the long run merely because the cable is connected. First review the calibration
summary and the physical level. The long run is a second live boundary.

After the short run passes, use a fresh output directory:

```bash
python3 scripts/quantum2626_loopback_soak.py run \
  --duration 08:00:00 \
  --output-dir /tmp/quantum2626-loopback-overnight \
  --level-dbfs -30 \
  --capture-fragment quantum2626_mono_in_P2626_0_10__source \
  --live-ack OUT3-PATCHED-TO-SELECTED-INPUT-MONITOR-OFF
```

The test does not retain eight hours of raw PCM. It writes:

- `summary.json`: terminal result, duration, block/event counts, correlation/peak bounds, terminal
  snapshot status, and helper teardown return codes;
- `events.jsonl`: immutable start geometry, one-second telemetry, continuity events, stop, a failure
  snapshot before helper reaping, and the later teardown-complete ordering marker;
- `event-*.s32le`: one 4,096-frame mono capture block for each detected event;
- `pw-top.filtered.log`: timestamped Quantum/test-stream PipeWire load and error-counter rows;
- `pw-errors.jsonl`: the initial ERR state and every observed counter transition for the exact
  playback node, capture node, `pw-play`, and `pw-record` rows;
- `pw-play.stderr`, `pw-record.stderr`, and `pw-top.stderr`: process diagnostics.
- `capture-extractor.stderr`: diagnostics from the isolated capture drainer.

The playback feeder runs in a dedicated process. This is intentional: global recovery is
substantially more expensive than normal tracking, and keeping playback in a Python thread would
allow analyzer GIL contention to amplify one discontinuity into additional `pw-play` underruns.
Both transports now start a dedicated capture extractor before the capture helper. PipeWire passes
its mono stream through unchanged; direct ALSA extracts hardware channel index two from the
26-channel stream. Raw capture and extracted mono each use a required 1 MiB pipe, enough for 5.944
seconds of mono S32_LE at 44.1 kHz and longer than the analyzer's 1.486-second fail-closed loss
window. Missing capacity fails before geometry admission.

Every telemetry sample records scheduler policy, priority, nice level, context switches, runtime,
wait time, and timeslices for the helpers, feeder, extractor, and their individual threads.
PipeWire runs additionally require and record the same-user server's `data-loop*` or
`pw-data-loop` threads. These
fields distinguish helper/client scheduling and analyzer backpressure from stable IRQ/pointer
cadence; they do not promote a process or change graph or ALSA geometry.
If the analyzer fails, it first reads the volatile ALSA status and hardware parameters (including
an explicit closed/unavailable result), IRQ count, and each helper's final `/proc/<pid>/status` and
`schedstat`. Pointers are retained when ALSA still exposes them; a helper that already closed its
PCM cannot be made to reveal an earlier pointer. Child exit is detected with a non-reaping wait, so
an exited helper remains inspectable until this `terminal_snapshot` is durable. Only then does
fail-closed teardown signal or reap helpers and append `teardown_complete`. This orders the analyzer
trigger, already-exited helpers, and teardown-induced exits without treating a teardown interruption
as the initiating xrun.

Normal analysis searches near the expected phase. If that match falls below the adaptive threshold,
the analyzer searches the full reference. A globally matched displacement is one phase-jump event
and becomes the new expected phase. If global lock is absent, the expected timeline continues
without accepting an untrusted phase: the first block records one correlation-drop event, subsequent
lost blocks remain part of that episode, and recovery is logged without incrementing the event
count. Sixteen consecutive globally unlocked blocks stop the run fail-closed.

At 44.1 kHz, each analysis block is about 92.9 ms. A phase jump is reported in frames; an exact
`+128` or `-128` change is especially relevant to the hardware period. A correlation drop without
a stable phase jump records corrupted content that cannot be classified as a simple skip/repeat.

## Interpretation

The preferred direct analog loop includes the Quantum DAC, cable, and ADC. The currently connected
path instead includes the Quantum DAC, cable, Digimax ADC, optical link, and Quantum ADAT receiver.
Neither can by itself assign a defect to the playback DMA path, return capture path, converters, or
clocking. Both provide a shared monotonic timeline and reject explanations above the selected
PipeWire endpoints.

For the PipeWire discriminator, interpret the structured scheduling and ERR evidence together:

- Output-node plus `pw-play` transitions with stable helper/data-loop scheduling favor the playback
  graph or its ALSA adapter.
- `pw-record` transitions are capture-client evidence only after the isolated extractor and both
  1 MiB capacities remain admitted; a zero capture-node ERR count does not itself prove clean
  captured content.
- Simultaneous scheduling wait growth across separate playback and capture graphs favors a shared
  scheduling boundary. `pw-top` ERR samples remain interval evidence, not exact causal timestamps.
- Missing helper-thread or server-data-loop telemetry invalidates directional classification and
  must fail the run rather than falling back to process-main scheduling.

- A detected phase jump aligned with an audible pop proves a sample-continuity discontinuity.
- A repeated exact 128-frame delta points toward one hardware-period handoff, but remains a
  localization hypothesis until driver-side IRQ/pointer evidence agrees.
- A correlation drop with stable ALSA/PipeWire counters proves those counters are insufficient to
  describe the artifact; it does not prove DMA corruption by itself.
- No event during one overnight run is strong acceptance evidence for that fixed configuration,
  not proof that every rate, buffer geometry, endpoint, or duplex lifecycle is correct.
- Clipping invalidates the run. Lowering the stimulus for a fresh run is a measurement correction,
  not an audio-driver workaround.

Retain the generated directory until its summary and any events have been classified. Do not commit
raw event audio or host-specific telemetry to the repository. Record only sanitized conclusions in
`notes/CURRENT_STATUS.md` and the active task.
