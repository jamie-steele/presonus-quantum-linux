# Experimental RFC releases

The main driver is Nicholas Johnson's `snd-quantum` RFC. Source bundles contain
that GPL-2.0 driver unchanged, a DKMS build wrapper, our 48 kHz UCM profile, and
WirePlumber 0.4/0.5 policy. The release manifest identifies the exact mailing-list
messages, patch hashes, reconstructed source hash, and packaging commit.

## Native packages

The native-package workflow adds `quantum-dkms` DEB and RPM assets to an existing
RFC release after install/upgrade/removal tests. These are **source/DKMS packages**,
not precompiled kernel modules. Native packages currently target **x86_64 only**:
Ubuntu 24.04, Debian 13, Fedora 43, and openSUSE Tumbleweed. Arch continues to use
the source installer below. No live host installation is implied by these checks.

Download the package for your distro and its `native-<revision>-SHA256SUMS` from
the same release. Verify your selected file with `sha256sum` against its entry;
`sha256sum --ignore-missing -c native-<revision>-SHA256SUMS` checks downloaded assets.
The revision suffix is independent of the RFC: packaging fixes increase `-1` to
`-2` without claiming a new upstream submission. DKMS uses that full version too.

Install headers for the kernel you will boot before installing the package:

```bash
# Ubuntu / Debian: then use the exact downloaded filename in place of <version>.
sudo apt install linux-headers-$(uname -r)
sudo apt install ./quantum-dkms_<version>_amd64.deb

# Fedora 43:
sudo dnf install kernel-devel-$(uname -r)
sudo dnf install ./quantum-dkms-<version>.fc43.x86_64.rpm

# openSUSE Tumbleweed (default kernel):
sudo zypper install kernel-default-devel
sudo zypper install ./quantum-dkms-<version>.suse.x86_64.rpm
```

The package manager installs runtime/build dependencies. RPM files are currently
unsigned standalone release assets, not a signed RPM repository; verify the
release checksum and review any local-package trust prompt. Do not disable your
system's repository signature checks. Alternate kernels require matching headers.

Native scripts build for installed kernels with usable headers, refresh module
indexes and existing boot images, and never load/unload modules or restart audio.
A missing header tree fails configuration. On Debian/Ubuntu install the headers
and run `sudo dpkg --configure quantum-dkms`; on RPM systems inspect scriptlet
errors, install headers, and reinstall the package. Reboot when ready and verify
`lspci -nnk` reports `snd_quantum`. Secure Boot still requires your distro's DKMS
key enrollment. Installation success alone is not boot or audio acceptance.

### Migrating from the tar installer

Back up customized Quantum UCM/WirePlumber files and
`/etc/modprobe.d/quantum2626-backend.conf`. Native packages own the same profile
paths; compare/reapply local profile edits after installation. The backend policy
is a Debian conffile / RPM `%config(noreplace)` file: retain local settings only
after confirming they do not blacklist the new `snd-quantum` driver. Review any
`.dpkg-dist` or `.rpmnew` file. Reconcile custom `modules-load.d` rules separately.

Run `dkms status`. Remove the **old tar-installed Quantum version only**, for example
`sudo dkms remove -m quantum -v 20260820.rfc1.s1148921 --all`, before the first native
install. Do not remove unrelated modules or run the tar installer over the native
package. This does not unload the currently running module. Subsequent native
upgrades/removals are handled by the package manager.

Remove with `sudo apt remove quantum-dkms`, `sudo dnf remove quantum-dkms`, or
`sudo zypper remove quantum-dkms`. Debian retains the backend conffile until
`sudo apt purge quantum-dkms`; RPM may retain modified config as `.rpmsave`.
Removal does not load a fallback driver. Plan a reboot and explicitly restore your
chosen fallback policy if needed.

## APT updates

**Not activated by this code change:** the signed APT feed requires maintainer
setup below. Until a production fingerprint and live URL are announced, use the
release DEB. A local `.deb` installation alone does not subscribe to new releases.

Once activated, use the announced HTTPS Pages base URL as `APT_URL`. Download
`quantum-archive-keyring.gpg` and `quantum.sources` from that URL. Inspect the source
file and compare `gpg --show-keys --with-fingerprint quantum-archive-keyring.gpg`
against the fingerprint published by the maintainer in this repository, not just a
fingerprint downloaded from the same APT server. Then:

```bash
sudo install -d -m 0755 /etc/apt/keyrings
sudo install -m 0644 quantum-archive-keyring.gpg /etc/apt/keyrings/
sudo install -m 0644 quantum.sources /etc/apt/sources.list.d/quantum.sources
sudo apt update
sudo apt install linux-headers-$(uname -r) quantum-dkms
```

The feed uses a dedicated `Signed-By` key and an opt-in `experimental` suite.
After explicitly installing `quantum-dkms`, ordinary `apt upgrade` can select newer
versions. Every version is still an experimental, unmerged RFC. APT configuration
does not automatically add this origin to unattended-upgrades. Remove
`/etc/apt/sources.list.d/quantum.sources` to stop receiving feed updates.

The feed retains published native versions, publishes checksums and signed
`InRelease`/`Release.gpg`, and expires metadata after 14 days. A daily workflow
refreshes signatures even without new RFCs. If expiry or signature validation
fails, repair publication/key configuration; never use `trusted=yes` or disable
APT authentication to work around it. Key rotation requires explicit review and
updating the installed keyring.

## Maintainer activation

1. Merge the packaging changes onto the default branch. Run **Quantum native
   packages** manually with tag `rfc-20260820.rfc1.s1148921` to add packages to the
   first tar-only release. Later RFC publications call it automatically. For CLI:
   `gh workflow run native-packages.yml -f tag=rfc-20260820.rfc1.s1148921`.
2. Use **Settings > Pages > Source: GitHub Actions** only if this repository's
   Pages site can be dedicated to this feed. Deployment replaces the whole site;
   do not overwrite an existing documentation site. Otherwise adapt hosting first.
3. Provision a dedicated, expiring GPG signing key for this APT feed, not a personal
   or kernel-module signing key. Store its ASCII-armored private export as the
   `APT_SIGNING_KEY` secret in the protected `apt-signing` environment, restricted
   to the default branch. The noninteractive workflow expects an unencrypted
   automation key protected by GitHub's secret storage and environment access.
   Keep an offline backup/revocation certificate and plan renewal before expiry.
4. Set repository variable `APT_SIGNING_FINGERPRINT` to its full 40-character
   fingerprint. Publish the public key/fingerprint in a reviewed repository change
   and announce the Pages URL before asking users to trust it. No production key
   or fingerprint is created by the build scripts or the container tests.
5. Set repository variable `APT_REPOSITORY_ENABLED=true`, then run **Quantum signed
   APT repository**. Protect the `github-pages` environment and verify a client
   `apt update` against the deployed URL. Signing runs never install release code.
   Successful native/RFC workflows and the daily schedule then refresh the feed.

Published native assets are immutable. Re-running a partially uploaded revision
can reuse byte-identical assets; different content fails instead of overwriting.
Increment `packaging/native/revision` for packaging changes, then rerun the native
workflow on the same RFC tag. Only the tested revision is published, not the
synthetic next revision used by upgrade tests. APT includes a revision only after
its checksum and build-evidence assets are present.

The package publisher and APT signer are separate jobs/workflows with scoped
permissions. See [GitHub's Pages workflow requirements](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
and [APT's Signed-By documentation](https://manpages.debian.org/bookworm/apt/sources.list.5.en.html).

## Install a source release

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

[TASK-016](agents/tasks/closed/native-package-distribution.md) records local native
install/reinstall/upgrade/removal checks for Ubuntu, Debian, Fedora, and openSUSE,
plus signed APT download, upgrade selection, tamper rejection, and expiry rejection.
The APT test used a disposable key and local file transport, not deployed Pages.
Fedora's header-only container emitted dracut diagnostics despite successful
scriptlet exits; bootable initramfs contents still require separate boot validation.

Local container verification on 2026-09-27 passed for all five targets with the
original RFC. The exact kernel versions and evidence limits are recorded in
[TASK-015](https://github.com/jamie-steele/presonus-quantum2626-linux/blob/HEAD/docs/agents/tasks/closed/rfc-release-integration.md).
The first hosted release, `rfc-20260820.rfc1.s1148921`, subsequently published
successfully. Native package attachment and signed APT deployment are separate
activation steps described above.

The matrix proves source and DKMS compatibility with the recorded packaged kernels
and validates staged integration. It does not prove boot, initramfs inclusion,
Secure Boot enrollment, Thunderbolt enumeration, or physical audio on those distros.
VM boot tests can extend that evidence, but emulated machines without the interface
cannot validate its DMA/audio path. Known upstream rate-transition and discovery
failures remain in `notes/CURRENT_STATUS.md`; every RFC release is experimental.
