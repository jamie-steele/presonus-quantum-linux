# TASK-016 Native Packages And Signed APT Distribution

## Status

Closed (local implementation and verification; hosted activation not performed)

## Objective

Ship native DEB/RPM DKMS installers from verified official RFC releases and prepare
a signed APT feed for normal Ubuntu/Debian updates.

## Decisions

- Reuse published, checksummed source bundles. Never use EMATech as the RFC source.
- Package source, not kernel-specific binaries; native package and DKMS versions
  include an independent packaging revision for fixes without inventing a new RFC.
- Test the same DEB on Ubuntu 24.04 and Debian 13; use dependency-specific Fedora 43
  and openSUSE RPMs. Keep Arch on the existing tested source installer.
- Native assets can be added to an existing tar-only release. Existing assets are
  never replaced; changed content needs a new packaging revision.
- Signed APT metadata is opt-in, expires after 14 days, and refreshes daily.
  Keep signing in a separate protected environment; no credentials in the repo.
- No host driver/service changes, push, release mutation, signing-key creation for
  production, or Pages activation as part of local implementation.

## Validation

Verified on 2026-09-27 with RFC `20260820.rfc1.s1148921` and synthetic packaging
revision upgrade `-1` to `-2`:

| Container | Packaged kernel | Native lifecycle |
| --- | --- | --- |
| Ubuntu 24.04 | `6.8.0-142-generic` | Install, reinstall, upgrade, config preservation, remove and purge passed. |
| Debian 13 | `6.12.107+deb13-amd64` | Same DEB, same lifecycle checks passed. |
| Fedora 43 | `7.2.7-100.fc43.x86_64` | RPM install, reinstall, upgrade, config preservation and erase passed. |
| openSUSE Tumbleweed | `7.2.7-1-default` | Same lifecycle checks with the SUSE dependency variant passed. |

- Module presence was checked using DKMS status and `modinfo`; old registrations
  and package-owned source files were checked after upgrade/removal. Original
  source-bundle DKMS and UCM staging checks also passed. No module was loaded.
- Real APT and GPG in an isolated Ubuntu container accepted a disposable signing
  key, verified/downloaded a DEB, selected the newer revision for an installed old
  version, and rejected tampered and expired signed metadata. No production key
  was created. This was a file-backed test feed, not deployed HTTPS/Pages proof.
- 22 Python tests passed. ShellCheck, actionlint, Git whitespace, and indexed task
  path/ID checks passed. The DEB was byte-identical across two consecutive builds.
- Downloaded the published release and verified its SHA256SUMS. The previously
  prepared test source bundle differed only in README/provenance metadata; driver,
  build files, install tools, raw RFC patches, and audio policy were identical.
- Earlier failures exposed RPM depmod behavior, unversioned-module replacement,
  same-version RPM reinstall handling, runtime-query macro escaping, and older
  apt-ftparchive silently omitting Valid-Until. These are corrected and covered by
  subsequent lifecycle/expiry checks. Failed logs were retained outside Git.
- Fedora's header-only container emitted dracut hostonly/logging/ldconfig warnings
  despite successful scriptlet exits. No container result proves a bootable
  initramfs, Secure Boot enrollment, Thunderbolt enumeration, or physical audio.
- Local logs remain outside Git under `/tmp/quantum-native-validation-v3/evidence`
  (DEB) and `/tmp/quantum-native-validation-v4/evidence` (RPM). CI uploads analogous
  evidence for each published revision, including signed-feed tests.

## Remaining Work

- Maintainer: merge/push through the normal review process, run native packaging
  for the first release, and provision/announce the APT key plus dedicated Pages
  hosting using `docs/RELEASES.md`. No release assets, settings, or secrets changed.
- VM boot, Secure Boot, and physical audio remain separate validation boundaries.

## Closure Summary

Local native packaging, signed-feed tooling, release integration, documentation,
and lifecycle verification completed. No new active task is needed merely for
the documented maintainer activation steps. Production publication remains
explicitly unperformed.
