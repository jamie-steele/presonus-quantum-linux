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

The current source also tightens ALSA's per-substream CPU-latency QoS request
to 2 microseconds after a successful PCM prepare. A temporary userspace request
at that value eliminated audible pops during the first bounded listening
interval. The driver implementation is now installed and loaded, and startup
PCM probes complete cleanly. Initial ordinary playback nevertheless crackles;
live evidence proves the QoS request is active and instead identifies the newly
active `msbits=24` metadata as the leading regression variable pending an exact
QoS-only A/B. The current source removes that precision constraint while
retaining the 2-microsecond QoS update. That exact discriminator is now
installed and loaded; PipeWire returned to 32 resolution bits and startup PCM
probes remain clean. The first ordinary Firefox playback result was audibly
excellent and clean with zero graph errors, correct IRQ cadence, and deep idle
suppressed. Longer listening remains appropriate before a durable no-pop claim.
The request follows ALSA's configured PCM lifetime and can reduce deep
CPU idle, increasing power use while a PCM remains prepared.

The current source contains a WirePlumber-compatibility duplex A/B candidate.
It preallocates persistent playback and capture DMA buffers, keeps the joint page
tables stable when one direction opens or closes, and aligns an independent late
direction at the next hardware-ring wrap. It deliberately omits ALSA synchronized
start metadata and grouped trigger completion because the installed build carrying
those additions reproducibly left WirePlumber 0.4 with 13 sinks and no capture
sources. The compatibility A/B is installed and loaded, but it reproduced the
same 13-sink/0-source graph. Capture discovery also caused an IOMMU DMA-write
fault from the Quantum PCI function to address zero at the stop/teardown
boundary, excluding synchronized-start handling as the cause. The current
source corrects that lifetime window by mapping the fixed maximum ALSA buffers
once and retaining both DMA page tables across `hw_free` and rapid discovery
cycles while programming active geometry separately. It builds cleanly and is
now installed and loaded. The same rapid probe storm no longer triggers a
DMAR/IOMMU fault, but WirePlumber still destroys the capture adapter and leaves
13 sinks with no stable sources. User listening also found a new static artifact
despite exact geometry and IRQ cadence. The full maximum-buffer data-page mapping
is the leading regression variable; this runtime candidate is rejected. The next
source correction now keeps the coherent page-table allocation stable while
populating and linking only active-buffer pages, and builds cleanly offline. It
is installed and loaded; native 44.1 kHz/128/512 playback returned without a
DMA/IOMMU fault, and initial user listening sounds good without reproducing the
maximum-map static artifact. Continued ordinary gaming use remained super stable
with no audible pops. A later read-only PipeWire snapshot, taken after a longer
settle than the activation controller allowed, found all 13 sinks and 26 sources;
capture remains closed and native-44.1 duplex is not yet validated.
Consult `../notes/CURRENT_STATUS.md` before any further activation or duplex
validation.

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
