# Ubuntu cleanup and reinstall

The cleanup helper removes recognized installations of this project's in-house
`snd-quantum2626` and RFC `snd-quantum` backends. It handles `make` installations,
the published tar/DKMS installer, the native `quantum-dkms` DEB, and residual DEB
configuration. It does not diagnose or promise to fix missing audio or high CPU.

The revision-3 DEB adds automatic migration of recognized legacy installs
(described in [the release guide](RELEASES.md#automatic-legacy-migration-in-deb-revision-3)).
It is prepared for review and not yet published. Once available, normal migration
to that package does not require a separate full cleanup. This helper remains
optional for recovery, uninstalling, and custom states requiring inspection.

From a reviewed repository checkout, preview first:

```bash
python3 scripts/maintenance/cleanup-ubuntu.py
```

No root access is needed for the normal preview. If files are unreadable, stop and
inspect the error rather than assuming nothing is installed. To also inspect the
known per-user Quantum overrides, name the affected user's home explicitly:

```bash
python3 scripts/maintenance/cleanup-ubuntu.py --user-home /home/YOUR_USER
```

Review the JSON plan. `files`, `sources`, `dkms_versions`, and `package` describe
recognized removal candidates; `review` lists preserved or unfamiliar items.
When ready, use the same options with `--apply`:

```bash
sudo python3 scripts/maintenance/cleanup-ubuntu.py --user-home /home/YOUR_USER --apply
```

The script checks for Ubuntu and creates a root-only backup under
`/var/backups/quantum-cleanup/` **before** purging the package, removing recognized
DKMS versions, or deleting files. The backup contains `plan.json` and the original
files under `files/`, preserving their absolute-path layout. A backup failure stops
before removal. A package/DKMS/removal failure stops immediately; inspect the
printed backup path and error before retrying. The script is not transactional:
previous successful removal steps are not automatically rolled back.

It refreshes module indexes and existing Ubuntu initramfs images. It never unloads
modules, restarts audio services, changes the active sound device, clears logs,
or removes build dependencies. The running driver can remain active until reboot.
Save work and reboot when ready. A cleanup with no recognized installation does
nothing, making a repeat preview useful for checking the result.

APT subscription stays configured for a reinstall. To also remove the standard
Quantum source and its dedicated keyring, add `--remove-apt-source` to both preview
and apply. A customized source file is preserved for review.

## What remains for manual review

The helper preserves other packages' files, modules in the distro's
`kernel/sound` tree, symlinks, unfamiliar source/DKMS identities, and custom or
shared audio configuration. It searches common system modprobe, modules-load,
PipeWire and WirePlumber directories for Quantum references and reports them.
Shared `/etc/asound.conf`, `/etc/modules`, and the selected user's `.asoundrc`
are also reported when they reference Quantum. Only the explicit user home's
three known Quantum override filenames are eligible
for removal; it does not search every account or erase general PipeWire state.
A `review` entry means cleanup is incomplete for that custom item. Do not delete a
shared file wholesale: remove only the Quantum-specific lines after inspection.

Files loaded directly with `insmod` from an arbitrary source checkout are not
installed files the helper can locate. It does not delete source checkouts,
external build caches, custom Secure Boot keys, or unrelated distro packages.
Future distro-provided Quantum drivers and profiles are preserved by location and
package ownership. Removing this project's blacklist can allow a distro driver
to bind at the next boot; cleanup is not a promise to disable all Quantum support.

## Reinstall or recover

Use the [release installation guide](RELEASES.md) to install headers for the kernel
you will boot, then install the current package. Keep the backup until the new
installation has been checked. Restore customized audio configuration selectively
by comparing the saved `files/` entries with the new installation. Reinstall a
package or tar release to recover driver binaries and DKMS registrations; copying
old `.ko` files or DKMS caches back is not a safe generic rollback.

If audio still fails, capture the installed package version, `uname -r`,
`dkms status`, `modinfo snd-quantum`, `lspci -nnk -d 1c67:0104`,
`/proc/asound/cards`, and `wpctl status`. A file reported by `modinfo` is the module
on disk, not proof that the same build is currently loaded. Follow
[no sound diagnostics](NO_SOUND_DEBUG.md) before making further changes. For high
CPU, identify the busy process/thread and corresponding logs before attributing
it to a driver. Share sanitized output rather than full system journals.

## Verification boundaries

Unit tests cover conservative file selection, package ownership, symlink
preservation, backup failures, package-purge failures, and repeat cleanup. The
container test below installs real published artifacts, builds the manual fallback
and DKMS modules, and exercises cleanup without attaching host devices:

```bash
dockpipe workflow validate workflows/quantum-cleanup-test/config.yml
dockpipe --no-vault --no-compile-deps --workflow quantum-cleanup-test \
  --var QUANTUM_CLEANUP_INPUT=/absolute/release-downloads \
  --var QUANTUM_CLEANUP_EVIDENCE=/absolute/cleanup-evidence
```

The input directory must contain the published `quantum-<version>.tar.gz`, its
`SHA256SUMS`, the revision-2 DEB, and `native-2-SHA256SUMS` from the same release.
The DockPipe workflow runs unit tests and the Ubuntu 22.04/24.04 matrix. Its
host-side wrapper starts Docker containers with read-only source/input mounts.
The harness uses disposable container state, never mounts host `/lib/modules`,
and never loads a module. Container success is installation/removal evidence;
a VM can additionally test boot/initramfs behaviour, while audible output,
Thunderbolt enumeration, and physical capture require actual hardware.

Verified on 2026-10-23 with DockPipe 0.6.24: both Ubuntu 22.04 (kernel headers
5.15.0-198) and 24.04 (6.8.0-147) passed the manual-module, tar/DKMS, native DEB,
partial-install, residual-conffile, backup, repeat-cleanup, reinstall and ownership
checks. Header-only containers emitted initramfs warnings about missing full
kernel metadata; these results do not establish bootable images. Ubuntu 26.04
and physical audio were not tested by this matrix.
