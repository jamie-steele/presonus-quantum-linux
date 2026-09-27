# TASK-014 Upstream Backend Cleanup

## Status

Closed

## Objective

Stabilize repository-owned build, install, and boot selection after the upstream
`snd-quantum` switch while preserving the external pinned source, the in-house
fallback, and the fixed 48-kHz desktop profile.

## Scope

- Make upstream and in-house installation modes explicit and reversible.
- Prevent both installed PCI aliases from racing during automatic boot binding.
- Keep normal builds offline and retain both module artifacts.
- Reconcile the directly affected UCM, install, status, and task documentation.
- Verify both backends and a staged audio/backend-selection installation offline.

## Out Of Scope

- Module load/unload, PCI rebinding, audio-service restart, playback, capture,
  reboot, network synchronization, commit, push, or publication.
- Editing or importing the pinned external RFC source.
- Driver transport, DMA, IRQ, page-table, or sample-rate algorithm changes.
- Deleting ambiguous switch or diagnostic artifacts.

## Evidence And Decisions

- 2026-08-21: both installed modules expose the identical PCI modalias for
  `1c67:0104`; effective modprobe configuration contained no backend blacklist
  or ordering policy. Upstream therefore auto-bound after reboot despite the
  retained in-house artifact.
- 2026-08-21: preserve the upstream default for ordinary source builds, but
  require full installation to name `upstream` or `inhouse` explicitly.
- 2026-08-21: install one backend-specific modprobe file at the stable path
  `/etc/modprobe.d/quantum2626-backend.conf`. It blacklists only the alternate
  module's PCI alias, so the selected backend is the sole automatic candidate
  while both artifacts remain manually recoverable.
- 2026-08-21: a real full install refreshes the target kernel initramfs and
  fails closed if `update-initramfs` is unavailable. `DESTDIR` staging installs
  the exact policy without mutating an initramfs.
- Live upstream evidence remains mixed: the fixed-48-kHz profile's full graph
  returned after a cold boot and the user listening interval was good, but the
  active rate was not captured and
  an earlier discovery transition produced DMA/IOMMU faults and command
  timeouts. No backend receives new live acceptance from this cleanup.

## Changes

- Added reviewable upstream and in-house modprobe templates. Each full install
  places only the selected template at the stable backend-policy path.
- Added explicit `install-upstream` and `install-inhouse` targets. Unqualified
  full/module installation fails before mutation, while ordinary upstream and
  in-house source builds retain their existing selection semantics.
- Full host installation refreshes the target kernel initramfs; staged installs
  skip that host action and retain exact packageable output.
- Updated the UCM/install/status/task documentation around the fixed 48-kHz
  desktop default, mixed upstream evidence, and separate higher-rate kernel
  capability.

## Validation

- `make -C driver QUANTUM_DRIVER=inhouse W=1`: exit 0; module SHA-256
  `d54f2bf411430c5ed350b5999d07795e9d7de6aa3801332c9e0d97152fa9b45e`.
- `make -C driver QUANTUM_DRIVER=upstream W=1`: exit 0 from the already pinned,
  verified external cache without a network operation; module SHA-256
  `bec996b8695380018b2db9a7a961c46897ed6def5922e01742528ee4e33e0ff4`.
- `make -C driver install-inhouse` and `install-upstream` with matching isolated
  `DESTDIR`/`INSTALL_MOD_PATH`: exit 0. Each tree contained only its selected
  module and exact copies of both UCM selectors, the shared profile,
  WirePlumber policy, and its backend modprobe file.
- Modprobe dry resolution against the in-house policy selected only
  `snd-quantum2626.ko`; the upstream policy selected only `snd-quantum.ko`.
- Isolated UCM parsing over the staged overlay enumerated exactly 13 playback
  and 26 capture PCMs; both shared directions are pinned to 48000.
- Unqualified `make -C driver install` failed with the explicit-backend error.
  `git diff --check` and task-index YAML parsing passed.
- No host selector was installed, no initramfs was changed, and no live device,
  service, PCM, or module action occurred.

## Remaining Work

- Installing one selected backend and proving its owner after a cold boot remain
  separately authorized host/live boundaries. TASK-013 retains the unresolved
  upstream DMA and sustained-listening evidence.

## Closure Summary

Closed 2026-08-21. Repository-owned source, install, audio, and documentation
surfaces now expose explicit, reversible upstream and in-house modes without an
automatic PCI-alias race. Offline and staged proof is complete; host activation
was intentionally not performed.
