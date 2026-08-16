# Desktop Audio Integration

Load this guide for ALSA UCM, PipeWire, JACK, or user-facing channel mapping
work.

## Read First

1. `notes/CURRENT_STATUS.md`
2. `notes/CHANNEL_ROUTING.md`
3. `alsa/README.md`
4. `alsa/ucm2/P2626/HiFi.conf`
5. `driver/snd-quantum2626.c` for the current PCM constraints

## Boundaries

- Keep every advertised format, rate, channel count, period, and buffer value
  within the kernel driver's real ALSA constraints.
- Do not expose capture until the driver registers a capture PCM.
- Do not expose high-rate profiles merely because static vendor tables exist;
  the driver must switch rate and channel geometry safely first.
- Preserve one shared multichannel backing stream when publishing stereo pairs
  so Main, Line, S/PDIF, and ADAT endpoints do not compete for exclusive access.
- A parsed UCM profile is offline evidence only. PipeWire discovery, concurrent
  opens, physical digital lock, and audible output are separate live results.
- Installing UCM files, restarting user audio services, loading the module, or
  opening a device crosses into `docs/agents/hardware-testing.md`.

## Verification

Use an isolated `ALSA_CONFIG_UCM2` tree to parse the UCM profile without a live
card. Confirm the verb, device inventory, stereo playback counts, mono capture
counts, and first/last bindings. Stage
`make -C driver install-ucm DESTDIR=<temporary-root>` and compare the installed
files with the tracked sources. Live desktop checks require a fresh
hardware-test boundary.
