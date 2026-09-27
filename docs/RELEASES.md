# Experimental RFC releases

The main driver is Nicholas Johnson's `snd-quantum` RFC. Source bundles contain
that GPL-2.0 driver unchanged, a DKMS build wrapper, our 48 kHz UCM profile, and
WirePlumber 0.4/0.5 policy. The release manifest identifies the exact mailing-list
messages, patch hashes, reconstructed source hash, and packaging commit.

## Install a release

Download `quantum-<version>.tar.gz` and `SHA256SUMS` from the same release. Check
`sha256sum -c SHA256SUMS` before extracting. The source package works across the
listed distributions; it is not a Debian/RPM package or a precompiled module.

Install dependencies for your distribution and running kernel first:

| Distribution | Dependencies |
| --- | --- |
| Debian | `sudo apt install build-essential dkms linux-headers-$(uname -r) alsa-utils alsa-ucm-conf wireplumber initramfs-tools` |
| Ubuntu / Ubuntu-based systems | Same command; use your distribution's exact kernel header package for custom kernels. |
| Fedora | `sudo dnf install gcc make dkms kernel-devel-$(uname -r) kernel-headers alsa-utils alsa-ucm alsa-ucm-utils wireplumber dracut` |
| openSUSE Tumbleweed | `sudo zypper install gcc make dkms kernel-default-devel alsa-utils alsa-ucm-conf wireplumber dracut` |
| Arch | `sudo pacman -S --needed base-devel dkms linux-headers alsa-utils alsa-ucm-conf wireplumber mkinitcpio` |

On Arch use `linux-lts-headers` for `linux-lts`; other alternate kernels also need
matching headers. After an update, boot the kernel for which headers are installed
or supply `--kernel <release>` explicitly. The installer fails before copying files
when the target headers, DKMS, WirePlumber version, or initramfs tool are missing.

Back up any locally customized Quantum UCM, WirePlumber, and
`/etc/modprobe.d/quantum2626-backend.conf` files before installation. From the
extracted `quantum-<version>` directory:

```bash
sudo bash install.sh
# Alternatively target a specifically installed kernel:
# sudo bash install.sh --kernel <kernel-release>
```

The installer adds/builds/installs `quantum/<version>` through DKMS, installs the
desktop profile and appropriate WirePlumber policy, blacklists the legacy
`snd-quantum2626` autoload alias, and regenerates initramfs. It does not unload
modules, restart services, or open an audio device. Reboot when ready, then verify
`lspci -nnk` reports `snd_quantum` for the Quantum PCI function. Custom
`modules-load.d` entries or initramfs rules that explicitly load the old driver
must be reconciled separately. Do not load both drivers against the device.

DKMS handles subsequent kernel rebuilds. Secure Boot may reject an untrusted
module: use your distro's DKMS signing and key-enrollment procedure, then confirm
the signer with `modinfo`. Automated compilation does not prove key enrollment.

`WIREPLUMBER_SERIES=0.4|0.5` and
`INITRAMFS_TOOL=update-initramfs|dracut|mkinitcpio` override detection. For offline
packaging inspection use `WIREPLUMBER_SERIES=0.5 bash install.sh --stage /tmp/quantum-stage`.
Staging performs no DKMS, depmod, service, or initramfs operation. An existing source
directory for the same version is deliberately not overwritten; inspect a failed
installation before retrying.

## Remove or roll back

Record the installed version with `dkms status`, then run
`sudo dkms remove -m quantum -v <version> --all` to remove that release's modules.
Keep or restore the UCM/WirePlumber files according to your chosen fallback.
Restore the saved backend policy, or install the in-house backend explicitly from
the repository using `sudo make -C driver install-inhouse`. Refresh initramfs with
the selected distro tool after any manual policy restoration, then reboot. Removing
a module on disk does not safely replace a driver that is already loaded.

Once DKMS has removed the version, its `/usr/src/quantum-<version>` source directory
can be removed after inspection. Never delete a different DKMS version or an
unrelated audio profile. The installer does not automatically remove older versions.

## Automated publication

`.github/workflows/rfc-release.yml` runs on changes for verification and polls
Patchwork every six hours on the GitHub default branch. A manual run can specify
a Patchwork **series ID**, or detect the oldest unpublished matching series.
The workflow must be merged/pushed to the default branch and Actions enabled;
GitHub may delay or disable scheduled runs in inactive repositories.

Discovery requires the ALSA project, Nicholas's exact public submitter address,
Quantum in the series name, an RFC subject, and a complete series. This is
source filtering, not cryptographic email authentication. A contributor branch
push does not count as an RFC. Changed author addresses or a transition from RFC
to merge-ready PATCH series require a reviewed detector update.

Each complete series is reconstructed in an empty temporary source tree, hashed,
and bundled. The original series is also checked against `driver/upstream.lock`.
Multipart full driver submissions work; incremental patches needing a kernel base
or a changed module layout fail visibly and require a packaging update. No failed
candidate is silently published or skipped. Backlogs drain one series per run.

The same archive is checked on Ubuntu 24.04, Debian 13, Fedora 43, openSUSE
Tumbleweed, and Arch x86_64. Each disposable container installs its own kernel
headers and tests DKMS build/install/remove, UCM parsing, and staged copies of both
WirePlumber formats and backend policy. Logs record image digest, distro, and exact
kernel. Rolling images can reveal new kernel incompatibilities and block release.

Only a successful full matrix permits publication. The publisher has a separate
write token, does not build upstream code, and uploads all assets to a draft before
marking it as a prerelease. Published tags are immutable in this workflow; an
interrupted draft can be retried. Tags include RFC date, revision, and Patchwork
series ID, so two submissions cannot silently replace each other.

Release snapshots do not advance the checkout's source pin. Update
`driver/upstream.lock` separately after reviewing a new RFC; keep the default source
build reproducible. GitHub's automatic repository source archives are the packaging
repository; download the attached `quantum-*.tar.gz` for the complete driver bundle.

## What the checks establish

Local container verification on 2026-09-27 passed for all five targets with the
original RFC. The exact kernel versions and evidence limits are recorded in
[TASK-015](https://github.com/jamie-steele/presonus-quantum2626-linux/blob/HEAD/docs/agents/tasks/closed/rfc-release-integration.md).
This is local container proof;
the first hosted GitHub Actions run and publication still require activation.

The matrix proves source and DKMS compatibility with the recorded packaged kernels
and validates staged integration. It does not prove boot, initramfs inclusion,
Secure Boot enrollment, Thunderbolt enumeration, or physical audio on those distros.
VM boot tests can extend that evidence, but emulated machines without the interface
cannot validate its DMA/audio path. Known upstream rate-transition and discovery
failures remain in `notes/CURRENT_STATUS.md`; every RFC release is experimental.
