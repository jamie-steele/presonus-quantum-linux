# TASK-019 Ubuntu Installation Cleanup

## Status

Active

## Objective

Address issue #30 with a conservative Ubuntu cleanup helper and reproducible
installation/removal evidence. Keep physical audio diagnosis separate.

## Decisions

- Preview is the default; apply requires root and Ubuntu.
- Back up recognized files before mutation. Purge only quantum-dkms through dpkg,
  remove only known RFC DKMS identities, and remove manual modules only under
  updates/extra. Never erase distro kernel/sound modules or other packages' files.
- Preserve symlinks, unknown source trees, and shared/custom configuration for
  review. Optional per-user cleanup requires an explicit home path.
- Leave the APT subscription unless explicitly requested. Never unload modules,
  restart audio, remove unrelated packages, or touch Secure Boot enrollment.
- File/package/DKMS cleanup tests cannot establish the reporter's high-CPU cause
  or missing sound-card cause. No current loaded-driver evidence was supplied.

## Changes

- scripts/maintenance/cleanup-ubuntu.py: discovery, backup, narrow apply, read-back.
- tests/test_cleanup.py: file selection and failure/preservation boundaries.
- scripts/maintenance/test-cleanup-ubuntu.sh: real release lifecycle in containers.
- workflows/quantum-cleanup-test/config.yml and test-cleanup-matrix.sh: DockPipe
  unit/matrix entrypoint; ignore generated bin/.dockpipe state.
- docs/UBUNTU_CLEANUP.md and docs/RELEASES.md: preview, recovery and limitations.

## Validation

- 38 Python tests passed (11 cleanup tests plus 27 existing tests).
- ShellCheck passed for the container harness.
- DockPipe 0.6.24 workflow validation and execution passed. Ubuntu 22.04 with
  headers 5.15.0-198 and Ubuntu 24.04 with headers 6.8.0-147 both passed real
  fallback compilation/manual install, published tar/DKMS install, revision-2
  DEB install, partial package unpack, residual conffile purge, repeated cleanup,
  backup preservation, reinstall and preservation of other packages' files.
- Checksummed the published native DEB and source archive before execution.
  Disposable containers had no host device/module mounts or module-load capability.
- Evidence is outside Git at `/tmp/quantum-cleanup-validation/evidence/dockpipe/`.
  Earlier direct Docker runs also passed; the first attempt with all capabilities
  dropped stopped at APT user switching and was corrected with standard package
  capabilities. The final workflow retains no-new-privileges and drops NET_RAW/MKNOD.
- Initramfs tools ran successfully with expected header-only container warnings
  for missing full kernel metadata. No VM boot, Ubuntu 26.04, or physical audio
  acceptance is claimed.
- Added merged-/usr ownership coverage so a `/lib` alias cannot hide an owner
  recorded under `/usr/lib`. Shared ALSA/modules and per-user configuration are
  reported rather than deleted.
- Workflow YAML, ShellCheck, indexed task paths/IDs and Git whitespace passed.

## Remaining Work

- Local implementation and validation complete; commit and a separate PR were
  authorized on 2026-10-23. Merge and user-facing instructions await review.
- A booted VM can test initramfs/reboot behaviour; physical audio remains untested.
- No public issue response or cleanup of the real host has been performed.
