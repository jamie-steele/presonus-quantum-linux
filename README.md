# PreSonus Quantum 2626 Linux driver

Experimental out-of-tree ALSA PCI driver for the PreSonus Quantum 2626
Thunderbolt interface (`1c67:0104`). The project is based on static protocol
recovery from the macOS DriverKit extension and bounded tests on owned hardware.

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

The current proven contract is fixed at 48 kHz. Other analog outputs and the
physical S/PDIF/ADAT paths still need connected-hardware validation, and
sample-rate switching is not implemented yet.

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

- Only the Quantum 2626 PCI ID is enabled; related Quantum models are not
  claimed or probed by this driver.
- Playback is fixed to 48 kHz and 26 channels internally. Applications should
  use the UCM stereo endpoints or intentionally provide a full raw frame.
- No mixer controls, MIDI, high-rate profile, or hot-removal proof exists yet.
- Capture is live-proven at 48 kHz through direct ALSA and PipeWire duplex tests.
- ADAT routing is statically identified, not physically confirmed on Linux.

This repository contains no proprietary driver binary or bulk decompiler
output. Local reverse-engineering artifacts are intentionally ignored.
