# Quantum 2626 Channel Routing

**Last updated:** 2026-08-15

This note records physical channel order recovered from the x86_64 macOS
DriverKit extension. Labels in the tables are **static analysis** unless an
entry explicitly says otherwise. Proprietary binaries and raw analysis output
remain outside the repository.

## Playback at 44.1 or 48 kHz

The vendor table contains 26 playback channels in this order:

| ALSA channel | Zero-based index | Physical route |
| ---: | ---: | --- |
| 1 | 0 | Main Out L / Line Out 1 / Headphone Out L |
| 2 | 1 | Main Out R / Line Out 2 / Headphone Out R |
| 3-8 | 2-7 | Line Out 3-8 |
| 9-10 | 8-9 | S/PDIF Out 1-2 |
| 11-26 | 10-25 | ADAT Out 1-16 |

**Observed Linux and user-observed hardware:** channels 1 and 2 were audible
on headphone left and right respectively during bounded 48 kHz tests. The
other physical outputs, including rear Main, S/PDIF, and ADAT, have not yet
been independently listened to or measured on Linux.

## Capture at 44.1 or 48 kHz

The vendor table contains 26 capture channels in this order:

| ALSA channel | Zero-based index | Physical route |
| ---: | ---: | --- |
| 1-2 | 0-1 | Mic / Instrument In 1-2 |
| 3-8 | 2-7 | Line In 3-8 |
| 9-10 | 8-9 | S/PDIF In 1-2 |
| 11-26 | 10-25 | ADAT In 1-16 |

The Linux driver registers a capture PCM and the UCM profile exposes all 13
input pairs through one `dsnoop` stream. **Observed Linux:** a five-second raw
26-channel capture completed with exactly 1,875 period IRQs and changing data
on analog inputs 1-8 and ADAT inputs 1-8. S/PDIF and ADAT inputs 9-16 remained
zero with nothing connected. PipeWire now publishes all 26 channels as named
mono sources. A bounded Line Input 5 recording contained changing samples from
only binding 4, while the earlier paired Mic/Instrument test ran concurrently
with Main playback.
Physical source identity beyond the statically recovered order still requires
an applied signal or clock-compatible digital sender.

## Rate-dependent channel counts

The vendor model database uses a different channel profile for each rate
family:

| Sample-rate family | Playback | Capture | Digital channels present |
| --- | ---: | ---: | --- |
| 44.1 / 48 kHz | 26 | 26 | S/PDIF 1-2 and ADAT 1-16 |
| 88.2 / 96 kHz | 18 | 18 | S/PDIF 1-2 and ADAT 1-8 |
| 176.4 / 192 kHz | 8 | 8 | None; analog 1-8 only |

At 88.2/96 kHz the order is analog 1-8, S/PDIF 1-2, then ADAT 1-8. At
176.4/192 kHz only the eight analog channels remain. The repository driver
source now exposes these exact rate/channel pairs to ALSA and implements the
recovered TCI rate setter, but only 48 kHz/26 channels are live-proven. The
non-48 kHz rows must be treated as implemented, unverified hardware paths.

## Desktop mapping

`alsa/ucm2/P2626/HiFi.conf` divides the proven 48 kHz playback frame into
named stereo endpoints backed by a single ALSA `dshare` stream:

| Endpoint label | Zero-based bindings |
| --- | --- |
| Main / Line 1-2 / Headphones | 0, 1 |
| Line 3-4 | 2, 3 |
| Line 5-6 | 4, 5 |
| Line 7-8 | 6, 7 |
| S/PDIF 1-2 | 8, 9 |
| ADAT 1-2 through ADAT 15-16 | 10, 11 through 24, 25 |

The shared stream is fixed to the driver contract: 48 kHz, S32_LE, 26
channels, 128-frame periods, and a 256-frame buffer. **Observed Linux:** after
one WirePlumber restart, PipeWire published all 13 named sinks with the intended
first and last bindings. A bounded Main stream advanced through 1,941 hardware
IRQs and stopped cleanly. **User-observed hardware:** subsequent YouTube audio
through the Quantum desktop sink is audible through the connected headphones.
Physical Line, S/PDIF, and ADAT output and sustained concurrent endpoint use
still require bounded live validation.

The matching capture endpoints use each zero-based binding independently over
the same shared fixed geometry. **Observed Linux:** PipeWire published 26 mono
sources from Mic/Instrument Input 1 through ADAT Input 16. A bounded Line Input
5 capture opened binding 4 alone and produced a 48 kHz/S32_LE mono WAV with
changing samples. The earlier paired capture test also ran while Main playback
was active; no xrun or timeout was observed.
