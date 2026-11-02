# TASK-021 Repository organization

## Status

Closed — completed 2026-10-25.

## Objective

Make the top-level layout easier to navigate without losing research evidence,
changing native build contracts, or discarding the existing uncommitted work.

## Decisions and changes

- Group former top-level notes and Windows references under `research/notes/`
  and `research/windows/`. Preserve dated observations and raw retained evidence.
- Move `samples/` to `tests/fixtures/audio/` and update the live-test scripts'
  fixture paths without executing them.
- Consolidate four `docs/_META/` drafts into `docs/PROJECT_METADATA.md`; merge
  Windows collection README text into `research/windows/README.md`.
- Add documentation and research indexes; update source-of-truth routing,
  script paths, links, ignored proprietary-input paths, and release-note paths.
- Remove the redundant notes placeholder and accidentally tracked generated
  Ghidra project/database state. Preserve the complete local project outside
  the checkout in a temporary backup before removing it from the source tree.
- Keep `driver/`, `alsa/`, `packaging/`, CI, and installed local `tools/` in place.
  Native build/install contracts and hardware behavior are unchanged.

## Validation

- `python3 -m unittest discover -s tests -v`: 57 tests passed.
- `bash -n`: all 26 shell scripts under scripts and driver/scripts passed.
- PowerShell parser-only check: all 21 scripts passed; no Windows capture ran.
- All four optional DockPipe workflows passed schema validation; the source
  verification workflow passed against the pinned cached RFC.
- Native upstream and in-house `W=1` builds passed in an isolated temporary
  source copy, with native clean between builds. BTF generation was skipped
  because vmlinux was unavailable. Existing checkout build artifacts survived.
- All 69 local Markdown links in the main documentation, research, and driver
  guides resolve. Agent/task YAML indexes parse, paths exist, and IDs are unique.
- Raw retained evidence, audio fixtures, and preexisting packaging changes are
  byte-exact against the pre-cleanup snapshot. All removed Ghidra project files
  are byte-exact in the external backup. Ignored vendor inputs remain ignored.
- `git diff --check`: passed.

## Closure summary

Completed the folder and documentation consolidation without changing hardware
behavior or native build interfaces. The source tree no longer contains generated
Ghidra project state. The local backup was retained outside the repository at
`/tmp/quantum-organization-backup-oz_w2_80/pae_quantum.sys_ghidra`; this is a
temporary recovery copy, not a required build input or durable evidence store.

## Boundaries

No module loads, service changes, MMIO operations, hardware experiments, commits,
pushes, or publication. Historical evidence is not new hardware acceptance.
