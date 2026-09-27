# TASK-016 Native Packages And Signed APT Distribution

## Status

Closed (local verification and subsequent authorized hosted activation completed)

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

- Maintainer: renew the dedicated signing key before 2027-09-27 and retain its
  private backup/revocation material securely. Rotate client keyrings deliberately.
- VM boot, Secure Boot, and physical audio remain separate validation boundaries.

## Closure Summary

Local native packaging, signed-feed tooling, release integration, documentation,
and lifecycle verification completed. The later explicit user request authorized
commit, push, merge, and production signing/Pages activation.

## Hosted Activation, 2026-09-27

- PR #24 merged as `391add5686378153bb816ad3bd0a9720b90a3352` after passing all five
  source-distro checks. Native run `36344718365` then passed all four lifecycle
  jobs plus the signed-feed test and attached revision-1 packages to the existing
  `rfc-20260820.rfc1.s1148921` release without replacing its source assets.
- A dedicated RSA-4096 signing key was provisioned separately from the tests;
  public fingerprint `5F839BAB8E48F6572044A442D98AC6B03628D7BE`, expiry 2027-09-27.
  Only its public export is in Git. The private key is backed up in a user-owned
  mode-0700 local GPG directory and stored as an environment-scoped Actions secret.
- `apt-signing` and `github-pages` environments permit only `master`. Pages uses
  Actions deployment with HTTPS; `APT_REPOSITORY_ENABLED=true` activates successful
  release-triggered and daily refreshes.
- Run `36344954793` successfully signed/deployed
  `https://jamie-steele.github.io/presonus-quantum-linux/`.
- A fresh Ubuntu container pinned the public fingerprint, ran real HTTPS
  `apt update`, simulated dependency resolution, and downloaded the authenticated
  revision-1 DEB. Its SHA-256 was
  `1c3c56cb998226f5f41e08e7da9dff016474b37a4d51a448348897472fbc97cc`.
  No driver was installed or loaded in that live-feed check or on the host.
