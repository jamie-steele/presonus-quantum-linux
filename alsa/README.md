# ALSA desktop routing

The files under `ucm2/` describe the live-proven playback geometry and the
implemented capture geometry to ALSA UCM and desktop audio servers such as
PipeWire:

- fixed 48 kHz, interleaved S32_LE, 26-channel hardware playback;
- one default stereo endpoint for Main / Line 1-2 / Headphones;
- stereo endpoints for Line 3-4, Line 5-6, Line 7-8, and S/PDIF 1-2;
- eight stereo ADAT endpoints covering ADAT 1-16;
- one shared `dshare` stream so those stereo endpoints can be used together;
- one shared `dsnoop` stream exposing Mic/Instrument 1-2, Line 3-8,
  S/PDIF 1-2, and ADAT 1-16 as 26 independent mono capture sources.

The underlying direct multichannel endpoint remains `hw:P2626,0` for both
directions. UCM intentionally does not advertise 96 or 192 kHz: the current
driver is fixed to 48 kHz with 26 channels. Playback, capture, and bounded
PipeWire duplex operation are live-proven at that geometry.

## Install

`make install-ucm` from `driver/` installs the files into the system UCM2
tree. The complete module-plus-profile target is `make install`.

For packaging or inspection, the file mapping is:

```text
alsa/ucm2/P2626/P2626.conf
  -> /usr/share/alsa/ucm2/P2626/P2626.conf
alsa/ucm2/P2626/HiFi.conf
  -> /usr/share/alsa/ucm2/P2626/HiFi.conf
alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf
  -> /usr/share/alsa/ucm2/conf.d/snd-quantum2626/snd-quantum2626.conf
```

The `conf.d` entry matches the ALSA card driver name set by
`snd-quantum2626`. The `P2626` entry also permits direct inspection with
`alsaucm -c P2626`.

Restarting the user audio server and performing live playback are separate
hardware-test steps. Do not infer physical ADAT lock or routing merely from a
configuration parse: connect a clock-compatible receiver and validate each
pair at a controlled level.
