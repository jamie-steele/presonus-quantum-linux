# TASK-023 In-house driver responsibility split

## Status

Closed — completed 2026-10-25.

## Objective

Replace the monolithic fallback implementation with cohesive kernel C components,
preserving existing function bodies, PCI/module identity, module parameters,
locking and resource lifetimes. Keep the pinned upstream backend independent.

## Scope

PCI lifecycle, rate-profile policy, mailbox control, audio DMA, ALSA PCM, and IRQ
handling under `driver/inhouse/`; shared internal contracts and a single Kbuild
definition consumed by normal, migration-test, and cleanup-test builds.

## Changes

- `driver/inhouse/rates.c` owns hardware-independent rate/channel policy.
- `tci.c`, `dma.c`, `pcm.c`, `irq.c`, and `pci.c` own mailbox, audio resources,
  ALSA adaptation, IRQ handling, and card/module lifecycle respectively.
- Shared device state and internal cross-component contracts stay in `quantum.h`;
  immutable profiles and register definitions have dedicated headers.
- Only functions actually called across files receive external module-internal
  linkage; none are exported kernel symbols. The immutable rate table is shared
  with the existing ALSA constraint rules.
- `driver/inhouse/Kbuild` defines the existing composite module. Both disposable
  fixtures stage only source/header files and reuse that same object list.
- Updated current agent/source routing, the ALSA source comment, driver layout
  documentation, and the canonical status note. Archived evidence commands keep
  their historical source filename, explained by the new layout guide.

## Validation

- Baseline monolithic fallback, split fallback, default upstream, and standalone
  source-only fixture builds all passed against the running kernel headers with
  `W=1`, in temporary copies. Original checkout build artifacts were not cleaned.
- All 39 function bodies, 71 original macros, four shared structs, nine tables,
  and the module-parameter/metadata block match the pre-refactor source.
- `modinfo` readback confirms unchanged name, PCI alias, parameter definitions,
  license, author, description and vermagic against the baseline module.
- Kernel checkpatch reports zero errors and warnings across all six C files and
  three headers. Whitespace checks, fixture shell syntax, driver documentation
  links, and agent/task indexes pass.
- Existing Python tooling suite: 57 tests passed.
- BTF generation was skipped because vmlinux is unavailable. The kernel build
  reports existing compiler-name and pahole-version differences.
- Full distro lifecycle matrices and live hardware/audio tests were not run.
  Source/body preservation and successful compilation do not prove runtime
  equivalence or hardware acceptance of the new composite module.

## Closure

The fallback is organized by responsibility without changing its native module
name or backend selector. Pinned upstream sources, source lock, and default build
path remain separate. The original source and validation-only build copies are
retained under `/tmp/quantum-driver-refactor-syiefrwv` for this session.

## Boundaries

No hardware tests, module installation/loading, MMIO execution, audio-service
changes, commits, or publication. Existing runtime evidence is historical and
does not establish acceptance of the restructured module.
