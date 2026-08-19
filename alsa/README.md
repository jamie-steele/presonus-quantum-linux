# ALSA desktop routing

The files under `ucm2/` describe the live-proven playback geometry and the
implemented capture geometry to ALSA UCM and desktop audio servers such as
PipeWire:

- fixed 44.1 kHz, interleaved S32_LE, 26-channel hardware playback;
- one default stereo endpoint for Main / Line 1-2 / Headphones;
- stereo endpoints for Line 3-4, Line 5-6, Line 7-8, and S/PDIF 1-2;
- eight stereo ADAT endpoints covering ADAT 1-16;
- one shared `dshare` stream so those stereo endpoints can be used together;
- an experimental playback-only `slowptr true` request for more precise dshare pointer updates;
- an experimental playback-only 256-frame PipeWire ALSA headroom request;
- one shared `dsnoop` stream exposing Mic/Instrument 1-2, Line 3-8,
  S/PDIF 1-2, and ADAT 1-16 as 26 independent mono capture sources;
- an experimental request for a fixed 128-frame hardware period with four
  periods (512 frames total) on both shared directions.

The underlying direct multichannel endpoint remains `hw:P2626,0` for both
directions. UCM currently selects the live-proven 44.1 kHz/26-channel profile
while the repository driver source implements the recovered 26/18/8-channel
native-rate families. A rate-dependent UCM topology must not be published until
each reduced channel profile is live-validated. Direct playback, clock
switching, all 13/26 desktop endpoints, and ordinary Firefox playback are
proven at 44.1 kHz/26 channels; the first listening result had no clicks.
Capture and bounded PipeWire duplex operation remain proven only at 48 kHz/26
channels, and longer listening is still needed for intermittent-crackle acceptance.

## Install

`make install-audio` from `driver/` installs the UCM files and the matching
WirePlumber 0.4 node rule. `make install-ucm` and `make install-wireplumber`
remain available for packaging each component separately. The complete
module-plus-desktop-audio target is `make install`.

For packaging or inspection, the file mapping is:

```text
alsa/ucm2/P2626/P2626.conf
  -> /usr/share/alsa/ucm2/P2626/P2626.conf
alsa/ucm2/P2626/HiFi.conf
  -> /usr/share/alsa/ucm2/P2626/HiFi.conf
alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf
  -> /usr/share/alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf
alsa/wireplumber/51-quantum2626.lua
  -> /usr/share/wireplumber/main.lua.d/51-quantum2626.lua
```

The `conf.d` entry matches the ALSA card driver name set by
`snd-quantum2626`. The `P2626` entry also permits direct inspection with
`alsaucm -c P2626`. The WirePlumber rule matches only the Quantum UCM node
names and aligns `api.alsa.period-num = 4` with the UCM direct-plugin slave's
`periods 4`. With the current driver, alsa-lib 1.2.8, and WirePlumber 0.4,
ordinary PipeWire playback has live-resolved to four 128-frame periods and a
512-frame hardware buffer. A configuration parse alone still does not prove
that geometry; verify the active ALSA PCM.

The playback dshare currently enables `slowptr true` as a bounded diagnostic
for longer-running grain that occurs without PipeWire errors or lost hardware
interrupt cadence. It does not change rate, format, period, buffer, capture, or
direct `hw:P2626,0` access. Keep it only if longer listening proves a benefit.

The WirePlumber rule keeps capture at the same 128/512 request and adds 256
frames of `api.alsa.headroom` to playback only. This is two hardware periods of
userspace safety margin for the pointer-timing path; it does not change the
negotiated hardware period or buffer. It adds approximately 5.8 ms at 44.1 kHz
and is currently installed and active; longer ordinary listening remains the
acceptance test.

The 512-frame geometry is the current live-proven transport candidate, not a
proven crackle fix. Installing it, restarting the user audio server, and
performing live playback remain separate hardware-test steps. Do not infer
physical ADAT lock or routing merely from a configuration parse: connect a
clock-compatible receiver and validate each pair at a controlled level.
