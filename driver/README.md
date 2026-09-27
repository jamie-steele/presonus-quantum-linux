# PreSonus Quantum 2626 Linux driver

This directory contains an experimental out-of-tree ALSA PCI driver for the
locally verified PreSonus Quantum 2626 PCI function, `1c67:0104`.

Two build-selectable backends are available here:

- `upstream` (default) builds Nicholas Johnson's pinned 2026-08-20 RFC from an
  external verified cache as `snd-quantum.ko`;
- `inhouse` builds the locally developed `snd-quantum2626.ko` fallback.

The backends are intentionally separate implementations. This makes the RFC
usable as the forward integration base while retaining an immediate source
fallback to the hardware-tested in-house driver. `upstream.lock` is the
reviewable provenance and version boundary; Nicholas's source is not stored in
this repository. See [the original RFC](https://lore.kernel.org/all/20260820083646.11383-2-nicholas.johnson-opensource@outlook.com.au/),
[EMATech's unofficial collaboration tree](https://github.com/EMATech/quantum), and
[contribution instructions](../CONTRIBUTING.md). Experimental DKMS distribution
is described in [RELEASES.md](../docs/RELEASES.md).

## Duplex contract

The in-house fallback exposes one duplex PCM:

- ALSA card ID `P2626`, device 0;
- 44.1/48 kHz with 26 interleaved S32_LE channels;
- 88.2/96 kHz with 18 interleaved S32_LE channels;
- 176.4/192 kHz with 8 interleaved S32_LE channels;
- fixed 128-frame periods;
- 2 through 64 periods per buffer.

The detailed transport description above applies to the locally developed
in-house backend. Its 48-kHz playback, capture, and bounded PipeWire duplex paths
are live-proven; 44.1-kHz testing has useful but mixed lifecycle and continuity
evidence. Rates above 48 kHz, physical S/PDIF/ADAT routing, and hot removal remain
unproven.

The pinned upstream backend has separate evidence. It builds offline and has
bound the device, but one 44.1-to-48-kHz desktop discovery transition produced
DMA/IOMMU faults and command timeouts. A later cold boot returned the complete
13/26 graph and a good listening interval, but the active PCM rate was not
captured before playback closed. Do not transfer in-house acceptance to the
upstream implementation or treat the cold-boot interval as sustained acceptance.
Read `../notes/CURRENT_STATUS.md` before any activation or duplex validation.

The original RFC uses card ID `Quantum2626` by default, exposes 26 channels at
all advertised rates, and accepts 32-512-frame periods. It contains RawMIDI,
mixer/clock controls, and removal handling. Source implementation is not physical
validation of those features. Use the actual ALSA card ID from `aplay -l`;
`hw:P2626,0` is the in-house default, not the RFC's default.

## Build

Synchronize the pinned upstream revision explicitly, then build:

```bash
make upstream-sync
make
```

The sync target downloads Patchwork's raw mirror into
`${XDG_CACHE_HOME:-$HOME/.cache}/quantum2626/upstream`, verifies the downloaded
patch and extracted source tree, and creates the ignored `.upstream-src`
Kbuild bridge. `make`, `make upstream`, and verification never download
anything themselves; if the cache is missing or altered they fail with an
instruction to run `make upstream-sync`.

Inspect or re-verify the selected revision without network access with:

```bash
make upstream-status
make upstream-verify
```

Select the in-house fallback explicitly with:

```bash
make QUANTUM_DRIVER=inhouse
```

The equivalent convenience targets are `make inhouse` and `make upstream`.
An unknown `QUANTUM_DRIVER` value fails the build instead of silently choosing
a backend.

## Install

Choose the installed and next-boot backend explicitly:

```bash
make upstream-sync # once, as the ordinary user
sudo make install-upstream
# or: sudo make install-inhouse
```

The full install writes `/etc/modprobe.d/quantum2626-backend.conf`. The upstream
mode blacklists the in-house module's identical PCI alias; the in-house mode
blacklists the upstream alias. It then refreshes the target kernel's initramfs,
so only the selected backend participates in automatic binding on a later boot.
Both module files may remain installed and the unselected module remains
available for an explicitly controlled live swap.

Installation never unloads or loads a module and does not change the current
binding. Generic `make install` and `make install-module` require an explicit
`QUANTUM_DRIVER=upstream|inhouse` value and fail otherwise. The named install
targets are the preferred operator surface because they make the selection
visible in the command itself.

The narrower `install-module`, `install-backend-selection`, and `install-ucm`
targets are available for packaging. `DESTDIR` stages audio and modprobe files
without updating an initramfs; the kernel build's normal `INSTALL_MOD_PATH`
controls module staging. A full staged installation should set both roots to
the same temporary directory. `UCM2_DIR`, `MODPROBE_DIR`, and
`WIREPLUMBER_MAIN_LUA_DIR` / `WIREPLUMBER_CONF_DIR` may override their paths.
WirePlumber is detected automatically; use `WIREPLUMBER_SERIES=0.4|0.5` for
cross-distro staging. Real installation selects `update-initramfs`, `dracut`, or
`mkinitcpio`, with `INITRAMFS_TOOL` as an explicit override, and fails if none is
available. This is a single-kernel source install; release bundles use DKMS for
kernel upgrades.

Loading the module starts the TCI control path and binds the PCI function.
Treat module load/unload, desktop-audio restart, and playback as live hardware
tests; use the approval and evidence procedure in
`../docs/agents/hardware-testing.md`.

## Playback routing

The raw multichannel PCM is `hw:Quantum2626,0` for the original RFC and
`hw:P2626,0` for the in-house default. The UCM files in `../alsa/` expose a
normal Main stereo endpoint plus Line 3-4, Line 5-6, Line 7-8, S/PDIF 1-2, and
ADAT 1-16 as stereo pairs sharing the same hardware stream. Matching mono input
sources independently expose Mic/Instrument 1-2, Line 3-8, S/PDIF 1-2, and
ADAT 1-16. See
`../notes/CHANNEL_ROUTING.md` for the complete zero-based binding table.

## Debug module parameters

The in-house source retains narrow reverse-engineering parameters for single register
reads/writes and a small MMIO scan. They are not ordinary operating controls.
Do not use a write or scan parameter without an explicitly scoped hardware
experiment grounded in current register evidence.
