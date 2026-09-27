# PreSonus Quantum Linux

Discovery, research, desktop audio integration, and experimental releases for
PreSonus Quantum Thunderbolt interfaces. **Nicholas Johnson's upstream RFC
driver, `snd-quantum`, is now the main driver and default build backend.**
The earlier in-house `snd-quantum2626` driver remains an explicit research and
recovery fallback.

"Upstream RFC" means a proposal submitted for Linux kernel review; it does not
mean the driver has been merged into mainline Linux. This independent project
is not affiliated with PreSonus or Fender.

## Driver and collaboration

- Nicholas Johnson authored the [original RFC patch](https://lore.kernel.org/all/20260820083646.11383-2-nicholas.johnson-opensource@outlook.com.au/)
  and its [cover letter](https://lore.kernel.org/all/20260820083646.11383-1-nicholas.johnson-opensource@outlook.com.au/).
- [EMATech/quantum](https://github.com/EMATech/quantum) is an **unofficial contributor
  collaboration repository**, with an editable, out-of-tree adaptation of the RFC.
  It is not the official RFC or its publication channel. Its commits do not trigger
  our releases; we monitor the official linux-sound submission through Patchwork/lore.
- This repository retains protocol discovery, hardware findings, test tools,
  distro release integration, and ALSA UCM/WirePlumber profiles. Future UCM
  contributions belong in `alsa-ucm-conf`, with separate validation and submission.
- [Contributing](CONTRIBUTING.md) explains RFC review replies, kernel patch
  submission, collaboration-tree changes, and ALSA profile contributions.

## Status and support

Only Quantum 2626 (`1c67:0104`, Thunderbolt 3 / PCIe) is currently enabled and
hardware-tested. Quantum, Quantum 2, and Quantum 4848 remain research targets;
USB Quantum ES/HD devices use a different transport and are not supported by
this PCI driver.

The desktop profile is fixed at **48 kHz, 26-channel S32_LE**, exposing 13 stereo
outputs and 26 mono inputs. Physical analog playback/capture and bounded duplex
tests have succeeded with the in-house driver. The RFC has separate, mixed
hardware evidence: a successful cold-boot listening interval, but also DMA/IOMMU
faults and command timeouts during rate changes and desktop discovery.

The RFC implements MIDI, mixer/clock controls, and removal handling; these are
not established hardware acceptance results here. Its original PCM code exposes
26 channels at all advertised rates. The in-house backend's separate 26/18/8
channel constraints must not be attributed to the RFC. Higher rates, physical
S/PDIF/ADAT routing, sustained stability, and cross-distro hardware behavior need
further testing. See [current evidence](notes/CURRENT_STATUS.md).

## Releases

The [release page](https://github.com/jamie-steele/presonus-quantum2626-linux/releases)
is the distribution point for experimental RFC snapshots. The release workflow
checks the ALSA Patchwork feed every six hours and publishes each complete new
Nicholas Johnson Quantum RFC only after the distro build matrix passes.
An RFC remains an experimental prerelease even when compilation succeeds.

Releases contain the original driver source, DKMS build support, UCM profiles,
WirePlumber 0.4/0.5 configuration, provenance, checksums, and distro build logs.
Debian, Ubuntu, Fedora, openSUSE Tumbleweed, and Arch are the x86_64 CI targets;
derivatives and other kernels require their own validation. There is no universal
precompiled `.ko`: DKMS builds for the installed kernel and rebuilds on upgrades.

See [installation, distro dependencies, and release operation](docs/RELEASES.md).
The workflow must be on the GitHub default branch with Actions enabled before
scheduled publication operates. No release is implied merely by adding these files.

## Build from this repository

Install matching kernel headers, a compiler, Make, Git, and curl, then run:

```bash
make -C driver upstream-sync
make -C driver W=1
```

`driver/upstream.lock` pins the original RFC by URL and hashes. The explicit sync
downloads into an external cache; ordinary builds are offline. Automated releases
carry their own RFC manifest and do not silently change this reviewed source pin.
For the in-house fallback, use `make -C driver QUANTUM_DRIVER=inhouse W=1`.

Choose the backend explicitly when installing:

```bash
sudo make -C driver install-upstream
# Fallback: sudo make -C driver install-inhouse
```

Installation writes the chosen module, desktop configuration, and a modprobe
policy blacklisting the alternate backend, then refreshes initramfs using
`update-initramfs`, `dracut`, or `mkinitcpio`. It does not load/unload modules or
restart audio services. The selected driver takes effect on a later boot.
Existing explicit module-load rules can override blacklist-based autoload policy;
verify the actual binding after reboot. Secure Boot needs a trusted module signature.

## Repository map

| Path | Purpose |
| --- | --- |
| `driver/upstream.lock` | Reviewed default RFC source and hashes. |
| `driver/` | Build/install integration and in-house research fallback. |
| `alsa/` | Fixed-48-kHz UCM routing and WirePlumber policy. |
| `scripts/release/`, `packaging/`, `.github/workflows/` | RFC detection, source releases, and distro verification. |
| `notes/CURRENT_STATUS.md` | Canonical hardware evidence and limitations. |
| `notes/CHANNEL_ROUTING.md`, `notes/TCI_PROTOCOL.md` | Channel layout and recovered protocol. |
| `scripts/ghidra/`, `driver-reference/` | Discovery helpers; proprietary inputs remain ignored. |
| `docs/agents/` | Focused agent guidance and durable task records. |

Older findings remain available as research history. Use the current status and
[testing guide](docs/LINUX_TESTING.md) before acting on old commands. This cleanup
does not grant new hardware acceptance or authorize register sweeps.

Repository-authored material retains its existing license. RFC release bundles
preserve Nicholas Johnson's authorship, source SPDX notices, and GPL-2.0 text;
the root MIT license does not relicense the upstream driver.
