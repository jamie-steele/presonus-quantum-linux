# TASK-017 Distribution Compatibility Regression Coverage

## Status

Active (local validation complete; authorized hosted validation and publication next)

## Objective

Fix the reported Pop!_OS 22.04 APT dependency failure without replacing system
DKMS, and prevent similar packaging failures on supported distro bases.
Follow-up to [TASK-016](closed/native-package-distribution.md).

## Decisions

- Keep the official RFC driver unchanged. Increase the native packaging revision
  to 2 instead of replacing published revision-1 assets or inventing a new RFC.
- Accept DKMS >= 2.8.7 in the DEB; retain the RPM dependency floor.
- Gate native packages on Ubuntu 22.04/24.04, Debian 12/13, Fedora 43 and openSUSE.
  Retain Arch source coverage. Run native tests on PRs without publishing.
- Test signed-APT dependency resolution against real distro indexes, not just
  signature validity or a synthetic installed-package database.
- Cover Mint 21/22 and Pop!_OS through their Ubuntu bases without claiming these
  container checks prove derivative kernels, desktop sessions or physical audio.
- Use equivalent explicit UCM Syntax-4 values instead of Syntax-6 macros; keep
  all routing, PCM geometry, priorities and labels unchanged. Native packages use
  current packaging-owned audio files and record their hashes. Old source tarballs
  remain immutable; future source bundles inherit the compatible profile/helper.
- No host module loads, driver installs, service changes or audio tests.

## Validation

- 24 Python tests, focused ShellCheck, actionlint 1.7.7 and YAML index/path
  validation passed. The original Syntax-6 and rewritten Syntax-4 profiles produce
  identical complete ALSA JSON dumps on the host parser; no PCM was opened.
- Jammy DKMS 2.8.7 built/installed/removed the unchanged RFC on kernel
  `5.15.0-194-generic`. Its first full run exposed the older WirePlumber flag and
  UCM Syntax-6 incompatibilities; these are corrected, not waived.
- Debian 12 native install, reinstall, upgrade, config preservation, remove and
  purge passed on kernel `6.1.0-53-amd64` before the equivalent profile rewrite.
- Jammy signed APT tests passed, including real dependency resolution and
  rejection of tampered and expired metadata.
- Jammy ALSA parsed the rewritten profile with exact 13/26 channel coverage.
- Rebuilt native revision 2 passed install, reinstall, synthetic revision-3
  upgrade, configuration preservation and removal/purge on Ubuntu 22.04
  (`5.15.0-194-generic`), Ubuntu 24.04 (`6.8.0-142-generic`) and Debian 12
  (`6.1.0-53-amd64`) and Debian 13 (`6.12.107+deb13-amd64`). The installed UCM
  profile was parsed at each install step. Hosted Fedora/openSUSE/Arch gates
  remain pending.
- Local package-test evidence is under `/tmp/quantum-distro-compat-validation`.
- The user explicitly authorized commit, merge, revision-2 publication, live APT
  verification and master synchronization into staging/dev after successful checks.

## Boundaries

Do not overwrite original release assets or describe this fix as live until
publication and a fresh signed-feed consumer check have succeeded. Preserve
the user-reported unrelated HashiCorp key error as a separate repository issue.
