# PreSonus Quantum Linux

Discovery, research, desktop audio integration, and experimental releases for
PreSonus Quantum Thunderbolt interfaces. **Nicholas Johnson's upstream RFC
driver, `snd-quantum`, is now the main driver and default build backend.**
The earlier in-house `snd-quantum2626` driver remains an explicit research and
recovery fallback.

"Upstream RFC" means a proposal submitted for Linux kernel review; it does not
mean the driver has been merged into mainline Linux. This independent project
is not affiliated with PreSonus or Fender.

**[Install with APT](#install-with-apt) | [Download DEB/RPM packages](#package-downloads) | [All releases](https://github.com/jamie-steele/presonus-quantum-linux/releases)**

## Install with APT

**Recommended for Ubuntu, Debian, Pop!_OS, and Linux Mint on x86_64.** Install
`quantum-dkms` through our signed repository; no Git clone or manual driver build
is needed. DKMS builds the module for your kernel and handles future kernel
updates when matching headers are installed. Only the **Quantum 2626 Thunderbolt**
interface is currently enabled; the driver remains experimental.

Ubuntu 22.04/24.04 and Debian 12/13 are tested package bases. See the
[compatibility table](docs/RELEASES.md#distribution-compatibility) for Mint/Pop,
desktop audio, and custom-kernel limits. **Already installed an older driver?**
Back up custom audio settings and read the
[migration notes](docs/RELEASES.md#migrating-from-the-tar-installer) first.

### 1. Add the signed repository

With `curl` and `gpg` installed, download the repository configuration and public key:

```bash
APT_URL=https://jamie-steele.github.io/presonus-quantum-linux
curl -fsSLo quantum-archive-keyring.gpg "$APT_URL/quantum-archive-keyring.gpg"
curl -fsSLo quantum.sources "$APT_URL/quantum.sources"
gpg --show-keys --with-fingerprint quantum-archive-keyring.gpg
cat quantum.sources
```

**Stop if the key fingerprint does not match:**

```text
5F83 9BAB 8E48 F657 2044 A442 D98A C6B0 3628 D7BE
```

The [public key](packaging/native/apt-signing-key.asc) expires on **2027-09-27**.
Check that `quantum.sources` points to the APT URL above and uses
`Signed-By: /etc/apt/keyrings/quantum-archive-keyring.gpg`, then install both files:

```bash
sudo install -d -m 0755 /etc/apt/keyrings
sudo install -m 0644 quantum-archive-keyring.gpg /etc/apt/keyrings/
sudo install -m 0644 quantum.sources /etc/apt/sources.list.d/quantum.sources
```

### 2. Install the driver

```bash
sudo apt update
sudo apt install --no-install-recommends --no-remove linux-headers-$(uname -r) quantum-dkms
```

Review the proposed package changes before accepting. Reboot when convenient,
then check:

```bash
lspci -nnk -d 1c67:0104
```

The driver-in-use line should report **`snd-quantum`**. Secure Boot may require
your distro's DKMS key enrollment. Installation does not restart audio services;
test playback and inputs after reboot. Future published versions arrive through
normal `sudo apt update` / `sudo apt upgrade`.

## Package downloads

Prefer a standalone package? These are the **`20260820.rfc1.s1148921-2`** release
assets. APT above automatically selects newer published versions as they arrive.

| Distribution | Download |
| --- | --- |
| Ubuntu / Debian / compatible derivatives | [quantum-dkms AMD64 DEB][quantum-deb] |
| Fedora 43 | [quantum-dkms x86_64 RPM][quantum-fedora] |
| openSUSE Tumbleweed | [quantum-dkms x86_64 RPM][quantum-opensuse] |

Verify the downloaded package against [revision-2 checksums][quantum-checksums],
then follow the [native package installation commands](docs/RELEASES.md#native-packages).
Installing a downloaded DEB alone does not subscribe to APT updates. Arch users
can follow the [source/DKMS installation guide](docs/RELEASES.md#install-a-source-release).

Downloads are attached to [GitHub Releases](https://github.com/jamie-steele/presonus-quantum-linux/releases),
not the sidebar's **Packages** registry. [GitHub Packages' supported formats](https://docs.github.com/en/packages/learn-github-packages/introduction-to-github-packages#support-for-package-registries)
do not include APT/DEB or RPM; our signed APT repository is hosted on GitHub Pages.

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

The [release page](https://github.com/jamie-steele/presonus-quantum-linux/releases)
is the distribution point for experimental RFC snapshots. The release workflow
checks the ALSA Patchwork feed every six hours and publishes each complete new
Nicholas Johnson Quantum RFC only after the distro build matrix passes.
An RFC remains an experimental prerelease even when compilation succeeds.

Releases contain the original driver source, DKMS build support, UCM profiles,
WirePlumber 0.4/0.5 configuration, provenance, checksums, and distro build logs.
Debian, Ubuntu, Fedora, openSUSE Tumbleweed, and Arch are the x86_64 CI targets;
derivatives and other kernels require their own validation. There is no universal
precompiled `.ko`: DKMS builds for the installed kernel and rebuilds on upgrades.

Start with [APT installation](#install-with-apt) or the [DEB/RPM downloads](#package-downloads)
above. [The full release guide](docs/RELEASES.md) covers distro dependencies,
migration, package removal, signing, and release operation. Source builds below
are for development and research; they are not required for package users.

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

[quantum-deb]: https://github.com/jamie-steele/presonus-quantum-linux/releases/download/rfc-20260820.rfc1.s1148921/quantum-dkms_20260820.rfc1.s1148921-2_amd64.deb
[quantum-fedora]: https://github.com/jamie-steele/presonus-quantum-linux/releases/download/rfc-20260820.rfc1.s1148921/quantum-dkms-20260820.rfc1.s1148921-2.fc43.x86_64.rpm
[quantum-opensuse]: https://github.com/jamie-steele/presonus-quantum-linux/releases/download/rfc-20260820.rfc1.s1148921/quantum-dkms-20260820.rfc1.s1148921-2.suse.x86_64.rpm
[quantum-checksums]: https://github.com/jamie-steele/presonus-quantum-linux/releases/download/rfc-20260820.rfc1.s1148921/native-2-SHA256SUMS
