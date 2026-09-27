# TASK-015 Official RFC Release Integration

## Status

Closed (implementation and local verification; publication not activated)

## Objective

Make Nicholas Johnson's official upstream RFC the unambiguous main backend in
current documentation, retain this repository's research/integration role, and
prepare automatic, distro-verified experimental releases for new official RFCs.

## Scope And Decisions

- Preserve existing dirty work and the in-house research/recovery backend.
- Credit Nicholas and link the original lore message. EMATech/quantum is explicitly
  unofficial collaboration infrastructure; it never drives release detection.
- Poll official linux-sound submissions via ALSA Patchwork, filter author/project/RFC,
  require complete series, and process each unreleased series oldest first.
- Ship source/DKMS bundles rather than kernel-ABI-specific binaries. Preserve SPDX,
  GPL text, raw patches, source hashes, and packaging provenance.
- Require Ubuntu, Debian, Fedora, openSUSE, and Arch container checks before publication.
  Separate read-only source/build jobs from the release-write job; publish experimental
  prereleases only after all assets are uploaded to a draft.
- Keep source lock updates reviewed and separate from release snapshots. No commit,
  push, live hardware test, or existing host installation was requested for this work.

## Changes

- Root/contribution/install/testing/agent/status docs now distinguish the main RFC,
  fallback evidence, and unofficial collaboration. Obsolete probe guides are historical.
- Added official RFC discovery, reconstruction, deterministic archives, and provenance.
- Added DKMS installer, WirePlumber 0.5 policy, and distro-native initramfs selection.
- Added disposable distro verification and tests for discovery, source boundaries,
  retries, reproducibility, and host-tool dispatch.

## Validation

Verified 2026-09-27 against the original RFC, version `20260820.rfc1.s1148921`:

| Distro container | Packaged kernel | Result |
| --- | --- | --- |
| Ubuntu 24.04 | `6.8.0-142-generic` | DKMS build/install/remove, UCM parse, both policy staging formats passed. |
| Debian 13 | `6.12.107+deb13-amd64` | Same checks passed. |
| Fedora 43 | `7.2.7-100.fc43.x86_64` | Same checks passed. |
| openSUSE Tumbleweed | `7.2.7-1-default` | Same checks passed. |
| Arch | `7.2.7-arch1-1` | Same checks passed. |

- Source reconstructed to `54e58b84a3a799b02a994032d682d5e5e8232e300772acb8ecb34bd420407fa6`,
  matching the existing lock exactly. Live official-feed discovery selected series 1148921;
  GitHub's public release list was empty at inspection.
- Both repository backends rebuilt with `W=1` against `7.1.1-76070101-generic` in a
  temporary build copy. BTF generation was skipped because no vmlinux was available;
  compiler-name/pahole notices were environmental, with no source build failure.
- Release/host-tool unit tests passed (12 cases), including unofficial-author rejection,
  incomplete series, API errors, draft retries, pagination, multipart reconstruction,
  archive reproducibility, and all three native initramfs command forms.
- Actionlint, ShellCheck, task-index path/YAML checks, and `git diff --check` passed.
- Local UCM JSON validation proved exactly 13 stereo outputs and 26 mono inputs covering
  each channel once. WirePlumber 0.5 parsed with spa-json-dump and its node regex matched
  a representative Quantum node. Both repository install formats staged successfully.
- Initial failed distro checks exposed header-path, module-index, and split UCM-package
  assumptions in the test harness. They were fixed without modifying RFC source. Raw
  failed and successful logs remain outside Git; CI records these as workflow artifacts.
- No host module, audio service, initramfs, installed desktop configuration, or PCM changed.

Image digests used (public container images, x86_64):

- Ubuntu: `sha256:b3cc40b72b93588182b5410f723c7aaf142363311c2aa993d8a453ddcbb3ae15`
- Debian: `sha256:9cc080028c43b27d2074d63a5f9caf7166d731494965616c1a6d2827a004585c`
- Fedora: `sha256:a651ddf48ea28a06ed4e1e6519f51c9f47e7a5a138722ade87369b8fbb7e5b42`
- openSUSE: `sha256:e6241c6a2e2b3a1edcc44603ba5fc3a56c38ba6703e3cbdc69196cb8ecdd0153`
- Arch: `sha256:f3691b4dde62ba4c4b6f0ae2c1fbf28e8c0c8c4b9a35c7e06dc1f70e21aa29f6`

## Remaining Work

- Publish/activate the workflow on the repository's default branch only through the
  user's normal commit/push process. No GitHub release has been created locally.
- VM boot, Secure Boot enrollment, and physical Quantum audio remain separate evidence.

## Closure Summary

Local implementation and verification completed 2026-09-27. Official RFC monitoring,
source/DKMS releases, five distro checks, and current documentation are ready for
review in the existing checkout. Commit, push, and the first hosted workflow/publication
remain unperformed; the scheduler is not active solely because these files exist locally.
