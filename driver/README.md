# PreSonus Quantum 2626 Linux driver

This directory contains an experimental out-of-tree ALSA PCI driver for the
locally verified PreSonus Quantum 2626 PCI function, `1c67:0104`.

## Duplex contract

The driver currently exposes one duplex PCM:

- ALSA card ID `P2626`, device 0;
- 44.1/48 kHz with 26 interleaved S32_LE channels;
- 88.2/96 kHz with 18 interleaved S32_LE channels;
- 176.4/192 kHz with 8 interleaved S32_LE channels;
- fixed 128-frame periods;
- 2 through 64 periods per buffer.

It performs the recovered TCI mailbox startup, builds the vendor-style DMA
page tables, programs the full-buffer and 128-frame block lengths, handles the
real audio IRQ, and reports the packed hardware position to ALSA. A bounded
five-second silence run completed with the exact expected 1,875 interrupts and
no xrun. Playback channels 1 and 2 were physically audible through headphone
left and right.

Capture is live-proven at the 48 kHz/26-channel geometry. Native rate switching
is implemented from the recovered TCI setter contract but has not yet been
loaded or exercised on hardware; 48 kHz remains the control case. Physical
S/PDIF/ADAT validation and hot removal are also unproven. WirePlumber
discovers every UCM playback sink and capture source, and bounded PipeWire
playback/capture concurrency completed cleanly. YouTube playback through the
desktop path is physically audible on the connected headphones; read
`../notes/CURRENT_STATUS.md` for the exact evidence before another live test.

## Build

```bash
make
```

Equivalent kernel command:

```bash
make -C /lib/modules/$(uname -r)/build M=$PWD W=1 modules
```

## Install

`make install` installs both the module and the UCM desktop-routing profile:

```bash
sudo make install
sudo modprobe snd-quantum2626
```

The narrower `install-module` and `install-ucm` targets are available for
packaging. `DESTDIR` and `UCM2_DIR` may override the UCM staging destination;
the kernel build's normal `INSTALL_MOD_PATH` controls module staging.

Loading the module starts the TCI control path and binds the PCI function.
Treat module load/unload, desktop-audio restart, and playback as live hardware
tests; use the approval and evidence procedure in
`../docs/agents/hardware-testing.md`.

## Playback routing

The raw multichannel PCM is `hw:P2626,0` in both directions. The UCM files in `../alsa/` expose a
normal Main stereo endpoint plus Line 3-4, Line 5-6, Line 7-8, S/PDIF 1-2, and
ADAT 1-16 as stereo pairs sharing the same hardware stream. Matching mono input
sources independently expose Mic/Instrument 1-2, Line 3-8, S/PDIF 1-2, and
ADAT 1-16. See
`../notes/CHANNEL_ROUTING.md` for the complete zero-based binding table.

## Debug module parameters

The source retains narrow reverse-engineering parameters for single register
reads/writes and a small MMIO scan. They are not ordinary operating controls.
Do not use a write or scan parameter without an explicitly scoped hardware
experiment grounded in current register evidence.
