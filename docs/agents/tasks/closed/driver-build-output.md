# TASK-024 Isolated native driver build output

## Status

Closed — completed 2026-10-25.

## Changes

- Native upstream and fallback output now lives under
  `build/driver/upstream/` and `build/driver/inhouse/` respectively, ignored by Git.
- `driver/Kbuild` owns backend object selection; `driver/Makefile` remains the
  native build/install entry point and accepts an optional `BUILD_ROOT` override.
- `driver/scripts/prepare-build.sh` stages individual source links and Kbuild
  inputs in each output tree. Object files never pass through a source-directory
  symlink. This uses ordinary external-module `M=` builds rather than depending
  on the newer separate-output kernel feature.
- Clean visits both backend output directories. Installation selects the same
  output directory as compilation. Updated existing module-path callers and
  documented the new locations.

## Validation

- Both native backends built with `W=1` in the actual checkout; both modules and
  intermediates are under `build/driver/`. No generated artifacts appear under
  `driver/`, and upstream cache/source verification passes after the builds.
- Native clean removed both backends' modules and objects; subsequent native and
  named DockPipe builds recreated them only under the output tree.
- Existing Python suite: 57 tests passed. Shell syntax, staged-input overwrite
  protection, Git ignore handling, and whitespace checks passed.
- Reviewed the install-module dry run for the updated output path; no installation
  or hardware-facing script body was executed.
- BTF generation remains skipped without vmlinux. Live hardware and the full
  distro matrix were not rerun; current-kernel builds do not qualify older kernels.

The source cache, backend identities, and module behavior are unchanged. No
module loads, service changes, commits, pushes, or publication occurred.
