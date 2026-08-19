# PreSonus Quantum Linux

Experimental Linux audio support for the PreSonus Quantum family. The current
out-of-tree ALSA PCI driver targets the Quantum 2626 Thunderbolt interface
(`1c67:0104`) and is based on static protocol recovery from the macOS DriverKit
extension plus bounded tests on owned hardware.

The long-term goal is support for the full Quantum family. That is a roadmap,
not a claim that every model works today: the Quantum 2626 is presently the
only enabled and hardware-tested device.

Project home: <https://github.com/jamie-steele/presonus-quantum-linux>

## Quantum family support

Legend: ✅ confirmed on physical hardware · 🧪 experimental/in progress ·
❌ not currently supported · 🎯 planned

| Model | Connection | Device support | Playback | Capture | Desktop integration | Current state |
| --- | --- | :---: | :---: | :---: | :---: | --- |
| Quantum 2626 | Thunderbolt 3 / PCIe | ✅ | ✅ | ✅ | ✅ | 🧪 Active development; usable, but stability and performance work continues |
| Quantum | Thunderbolt 2 / PCIe | ❌ | ❌ | ❌ | ❌ | 🎯 Roadmap; needs model-specific hardware and protocol validation |
| Quantum 2 | Thunderbolt 2 / PCIe | ❌ | ❌ | ❌ | ❌ | 🎯 Roadmap; static family identity only, with no Linux hardware proof yet |
| Quantum 4848 | Thunderbolt 2 / PCIe | ❌ | ❌ | ❌ | ❌ | 🎯 Roadmap; static family identity only, with no Linux hardware proof yet |
| Quantum ES 2 | USB-C | ❌ | ❌ | ❌ | ❌ | 🎯 Long-term roadmap; different USB transport |
| Quantum ES 4 | USB-C | ❌ | ❌ | ❌ | ❌ | 🎯 Long-term roadmap; different USB transport |
| Quantum HD 2 | USB-C | ❌ | ❌ | ❌ | ❌ | 🎯 Long-term roadmap; different USB transport |
| Quantum HD 8 | USB-C | ❌ | ❌ | ❌ | ❌ | 🎯 Long-term roadmap; different USB transport |

A green check means that capability has been observed on owned physical
hardware. A red X means the repository does not currently support or validate
that capability; it does not mean the model can never be supported. New device
IDs will not be enabled from names or static similarity alone.

PreSonus groups the legacy Thunderbolt and current USB-C models under the
[Quantum family](https://support.presonus.com/hc/en-us/categories/115000740086-Quantum-Family).
Its connection guide distinguishes the Quantum 2626's Thunderbolt 3 connection
from the Thunderbolt 2 connections used by Quantum, Quantum 2, and Quantum 4848:
[Quantum-series connection guide](https://support.presonus.com/hc/en-us/articles/360040368472-Quantum-2626-Connecting-Quantum-Quantum-2-or-Quantum-4848).

## Linux audio works

> [!IMPORTANT]
> **The Quantum 2626 is producing real audio on Linux.** The current driver
> initializes the interface to its solid-blue ready state, plays ordinary
> desktop audio through PipeWire, captures real input data, and runs playback
> and capture concurrently on physical Quantum 2626 hardware.

This is no longer a fake-pointer or register-probing proof of concept. The
driver uses the recovered TCI mailbox, hardware DMA page tables, real audio
interrupts, and the hardware position counter. The result has been heard
through the interface's headphone output and exercised through both direct
ALSA and normal desktop applications.

### What works today

- The recovered TCI mailbox reaches the device-ready state; the interface's
  indicator is solid blue after the Linux handshake.
- Direct ALSA playback is stable in the proven 48 kHz, 26-channel, S32_LE,
  128-frame-period configuration.
- Playback channels 1 and 2 are physically confirmed through the left and
  right headphone outputs.
- Ordinary YouTube audio plays through the Quantum PipeWire sink and is
  physically audible through the connected headphones.
- The bundled ALSA UCM profile exposes Main plus every 48 kHz output pair over
  a shared multichannel stream. WirePlumber publishes all 13 named playback
  sinks.
- A 26-channel capture PCM is live-proven through direct ALSA and concurrent
  PipeWire playback/capture. UCM publishes all 26 Mic/Line/S/PDIF/ADAT inputs
  as independent mono sources—including a standalone, live-tested Line Input
  5 instead of a forced 5/6 stereo pair.
- Playback and capture run concurrently through the shared hardware engine;
  bounded duplex tests completed without an xrun, DMA timeout, or stop failure.

The current live-proven contract remains fixed at 48 kHz. The repository source
now implements native 44.1, 48, 88.2, 96, 176.4, and 192 kHz selection with the
recovered 26/18/8-channel profiles, but that new clock-changing path has passed
only offline build and static checks. Other analog outputs, physical S/PDIF/ADAT
paths, and every non-48 kHz profile still need bounded hardware validation.

The canonical evidence and current limitations are in
[`notes/CURRENT_STATUS.md`](notes/CURRENT_STATUS.md). The exact channel layout
is in [`notes/CHANNEL_ROUTING.md`](notes/CHANNEL_ROUTING.md).

## Build

```bash
make -C driver
```

The build requires headers for the running kernel. Compilation proves source
compatibility only; it does not prove a hardware path safe.

## Install

From `driver/`, the install target places both the kernel module and the ALSA
UCM desktop profile:

```bash
cd driver
sudo make install
sudo modprobe snd-quantum2626
```

Module load/unload, audio-service changes, playback, capture, and hardware
probing are live tests. Follow
[`docs/agents/hardware-testing.md`](docs/agents/hardware-testing.md) and
establish a fresh test boundary before running them.

## Repository map

| Path | Purpose |
| --- | --- |
| `driver/` | Kernel module and build/install targets. |
| `alsa/` | UCM desktop routing for the proven 48 kHz duplex layout. |
| `notes/CURRENT_STATUS.md` | Canonical consolidated hardware and implementation status. |
| `notes/CHANNEL_ROUTING.md` | Vendor channel order plus Linux playback-pair and mono-input bindings. |
| `notes/TCI_PROTOCOL.md` | Recovered mailbox registers and command framing. |
| `scripts/ghidra/` | Reproducible analysis helpers; proprietary inputs stay outside the repo. |
| `docs/agents/` | Agent guidance and durable task routing. |

## Known limits

- Only the Quantum 2626 PCI ID is enabled. The other models in the family
  support matrix are roadmap targets and are not claimed or probed by this
  driver.
- The tracked UCM desktop profile remains fixed to the live-proven 48 kHz,
  26-channel layout. Direct ALSA/DAW use of the new native-rate source requires
  the matching full raw frame: 26 channels at 44.1/48, 18 at 88.2/96, and 8 at
  176.4/192 kHz.
- No mixer controls, MIDI, live-proven high-rate profile, or hot-removal proof
  exists yet.
- End-to-end latency and release-performance tuning are not complete; no sub-millisecond or
  professional real-time performance claim is made yet.
- Capture is live-proven at 48 kHz through direct ALSA and PipeWire duplex tests.
- ADAT routing is statically identified, not physically confirmed on Linux.

This repository contains no proprietary driver binary or bulk decompiler
output. Local reverse-engineering artifacts are intentionally ignored.
