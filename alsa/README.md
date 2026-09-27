# ALSA desktop routing

The files under `ucm2/` describe the live-proven playback geometry and the
implemented capture geometry to ALSA UCM and desktop audio servers such as
PipeWire:

- fixed 48 kHz desktop default, interleaved S32_LE, 26-channel hardware playback;
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

The default RFC's direct endpoint is `hw:Quantum2626,0`; the in-house fallback
uses `hw:P2626,0`. Both directions use the selected card's device 0. UCM selects
the live-proven 48 kHz/26-channel desktop profile while
the kernel backends advertise native rates through 192 kHz. Direct `hw:` users
can bypass this UCM default, but rate-dependent desktop profiles must not be
published until their channel geometry is live-validated. Direct playback,
clock switching, all 13/26 desktop endpoints, capture, and bounded PipeWire
duplex operation are proven at 48 kHz/26 channels on the in-house path. The
upstream backend has mixed live evidence and does not inherit those results;
higher-rate kernel capability remains separate from this desktop default.

## Install

The profile uses UCM Syntax 4 and explicit device values so the same routing can
be parsed by Ubuntu 22.04's ALSA 1.2.6 as well as newer releases. Keep the 13 stereo
output and 26 mono input bindings identical when changing its representation.
Do not introduce newer UCM macros without testing the oldest supported parser.
This is parser compatibility, not proof of a working desktop session or hardware.

`make install-audio` from `driver/` installs the UCM files and the matching
WirePlumber 0.4 Lua or 0.5 SPA-JSON rule, selected from the installed version.
Set `WIREPLUMBER_SERIES=0.4|0.5` explicitly for staging. `make install-ucm` and `make install-wireplumber`
remain available for packaging each component separately. The complete
module-plus-desktop-audio targets are `make install-upstream` and
`make install-inhouse`; an unqualified full install fails closed.

For packaging or inspection, the file mapping is:

```text
alsa/ucm2/P2626/P2626.conf
  -> /usr/share/alsa/ucm2/P2626/P2626.conf
alsa/ucm2/P2626/HiFi.conf
  -> /usr/share/alsa/ucm2/P2626/HiFi.conf
alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf
  -> /usr/share/alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf
alsa/ucm2/conf.d/snd-quantum/snd-quantum.conf
  -> /usr/share/alsa/ucm2/conf.d/snd-quantum/snd-quantum.conf
alsa/wireplumber/51-quantum2626.lua
  -> /usr/share/wireplumber/main.lua.d/51-quantum2626.lua
alsa/wireplumber/51-quantum2626.conf
  -> /usr/share/wireplumber/wireplumber.conf.d/51-quantum2626.conf
```

Only the rule matching the target WirePlumber series is installed. WirePlumber
0.5 no longer loads Lua configuration; see its
[migration guide](https://pipewire.pages.freedesktop.org/wireplumber/daemon/configuration/migration.html).
Future upstream profile submission is described in [CONTRIBUTING.md](../CONTRIBUTING.md).

The two `conf.d` entries map the distinct `snd-quantum2626` and `snd-quantum`
ALSA driver names to the same `P2626` profile. Installing both mappings does not
choose the kernel backend; the explicit full driver install owns that choice
through `/etc/modprobe.d/quantum2626-backend.conf`. The `P2626` entry also
permits direct inspection with `alsaucm -c P2626`. The WirePlumber rule matches
only the Quantum UCM node
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
negotiated hardware period or buffer. It adds approximately 5.3 ms at 48 kHz;
longer ordinary listening remains the acceptance test.

The 512-frame geometry is the current live-proven transport candidate, not a
proven crackle fix. Installing it, restarting the user audio server, and
performing live playback remain separate hardware-test steps. Do not infer
physical ADAT lock or routing merely from a configuration parse: connect a
clock-compatible receiver and validate each pair at a controlled level.
