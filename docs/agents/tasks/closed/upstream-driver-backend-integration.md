# TASK-012 Upstream Driver Backend Integration

## Status

Closed

## Objective

Pin Nicholas Johnson's 2026-08-20 upstream RFC as an externally synchronized,
build-selectable out-of-tree backend while preserving the current in-house
driver as the explicit fallback.

## Scope

- Preserve RFC provenance, authorship, and exact hashes without storing its
  source in this repository.
- Require an explicit networked sync into an external cache; keep ordinary
  builds offline and fail closed when the cache is absent or altered.
- Add one fail-closed build selector for the in-house and upstream backends.
- Keep the current UCM routing discoverable under either module driver name.
- Compile both selections offline and document any compatibility delta.

## Out Of Scope

- Module installation, module load/unload, PCI rebinding, service restarts, or
  playback/capture tests.
- Merging the two implementations internally.
- Integrating the second developer's changes before their exact source and
  contract are available.
- Claiming that upstream review or merge has completed; this source is RFC v1.

## Relevant Context

- `driver/snd-quantum2626.c` is the hardware-tested in-house implementation.
- `driver/upstream.lock` pins the RFC and `driver/scripts/upstream-source.sh`
  owns external synchronization and verification.
- Upstream message ID:
  `<20260820083646.11383-2-nicholas.johnson-opensource@outlook.com.au>`.
- `notes/CURRENT_STATUS.md` remains authoritative for live in-house evidence.

## Constraints

- The upstream RFC is the default build; the in-house backend remains the
  explicit rollback selection.
- Exactly one backend is selected per build invocation.
- Upstream revision changes must update the reviewable URL and hashes in
  `driver/upstream.lock`; no upstream source may be committed here.
- Live device mutation requires separate user approval.
- Preserve the unrelated dirty loopback/task changes already in the checkout.

## Plan

1. Pin and fingerprint the RFC source.
2. Add the out-of-tree build selector and UCM driver-name mapping.
3. Compile both backends against the current kernel headers.
4. Record validation and any source-level compatibility corrections.
5. Leave the upstream backend as the target for a later, separately scoped
   second-developer integration.

## Evidence And Discoveries

- 2026-08-20: the RFC is a complete six-C-file ALSA PCI implementation with
  PCM, DMA, TCI, MIDI, mixer, CPU-latency, XRUN, and removal paths; it is not a
  narrow patch to the in-house driver.
- 2026-08-20: decoded patch SHA-256 is
  `859821e026da60f033ad240cfaba1c5a6b26b201d1392f5225eea53295b8ee49`.
- 2026-08-20: only the RFC's `sound/pci/quantum/` subtree was imported; its
  in-tree documentation, MAINTAINERS, and parent Kconfig/Makefile edits are not
  part of this out-of-tree integration.

## Decisions

- 2026-08-20: use a build-time backend selector rather than a runtime module
  parameter. Exactly one implementation is compiled per invocation and the
  separate artifacts preserve a clean fallback.
- 2026-08-20: name the selector `QUANTUM_DRIVER`, default it to `upstream`,
  retain `inhouse` as the explicit fallback, and reject unknown values.
- 2026-08-20: the initial exact import proved the build and live activation
  boundary, but it is superseded before commit by a pinned external-cache
  workflow at the user's request.
- 2026-08-20: normal builds must never fetch implicitly. `upstream-sync` is the
  only networked target; `upstream-verify` and every build validate the pinned
  external tree without network access.
- 2026-08-21: later live installation left both artifacts present. Because both
  expose the same PCI alias, build selection alone does not control automatic
  boot binding. TASK-014 supersedes the install semantics with an explicit,
  persistent modprobe/initramfs selector while preserving this closed task's
  external-source and build evidence.

## Changes

- Added `driver/upstream.lock` with lore provenance, Patchwork raw-patch hash,
  decoded-message patch hash, and extracted source-tree hash.
- Added explicit external-cache sync/status/verify tooling and an ignored
  `.upstream-src` Kbuild bridge; removed the vendored `driver/upstream/` tree.
- Added `QUANTUM_DRIVER=inhouse|upstream` routing in `driver/Makefile`.
- Added an upstream-driver-name UCM mapping with the same P2626 profile.
- Documented selection, module names, provenance, and safety boundaries.

## Validation

- `make -C driver QUANTUM_DRIVER=inhouse W=1`: exit 0 against the current
  7.0.11 headers; retained `snd-quantum2626.ko` SHA-256
  `d54f2bf411430c5ed350b5999d07795e9d7de6aa3801332c9e0d97152fa9b45e`.
- `make -C driver QUANTUM_DRIVER=upstream W=1`: exit 0; compiled all six RFC
  objects from the external cache and linked `snd-quantum.ko` with SHA-256
  `bec996b8695380018b2db9a7a961c46897ed6def5922e01742528ee4e33e0ff4`.
  Its srcversion remains `65A6D16B4AFEEDFEEA3CF43`; the module-file hash
  differs from the initial vendored-path build because Kbuild records the
  compilation path.
- `modinfo` reports module names `snd_quantum2626` and `snd_quantum`; the RFC
  artifact retains Nicholas Johnson's author metadata.
- `make -C driver QUANTUM_DRIVER=invalid`: expected exit 2 with the explicit
  accepted-value error, proving fail-closed selection.
- The extracted external C, header, Kconfig, and Makefile tree hashes exactly
  to the locked RFC source-tree digest.
- Patchwork raw SHA-256 `52c6b88d...172a` extracts the same source tree SHA-256
  `54e58b84...fa6`; the external cache status is `verified` and contains no
  repository-tracked source.
- `upstream-verify` fails when pointed at an absent cache, while
  `QUANTUM_DRIVER=inhouse` still builds with that same absent-cache override.
  Verification also follows the pinned ignored bridge under a root-style
  `$HOME`, so an unprivileged sync remains valid for the later `sudo make
  install` step.
- A DESTDIR-staged `install-ucm` run installed both driver-name mappings and
  the shared P2626 profile without touching the host UCM installation.
- `git diff --check` and YAML parsing of `docs/agents/tasks/index.yml` pass.
- Compiler basename and unavailable/mismatched pahole/BTF warnings are
  environmental; GCC versions match and both module links completed.
- Live install, load, bind, playback, capture, MIDI, removal, and listening
  validation were intentionally skipped because no live hardware action was
  authorized.

## Remaining Work

- Review and integrate the second developer's changes after their source is
  supplied, using this upstream backend as the proposed forward base.
- Any install/load/listening A/B requires a separately approved live task.

## Closure Summary

Closed 2026-08-20. The exact RFC driver is pinned as an explicitly synchronized,
offline-verified default backend without storing its source in this repository;
the in-house driver remains the explicitly selected fallback. No live device or
host audio state was changed by the external-source migration.
