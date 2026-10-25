# TASK-022 Script organization and local DockPipe scaffold

## Status

Closed — completed 2026-10-25.

## Changes

- Moved 32 loose scripts into `scripts/linux/`, `scripts/windows/`,
  `scripts/experiments/`, and the existing `scripts/ghidra/` directory.
- Left release and maintenance scripts in their existing groups. Added
  `scripts/README.md` with entry points and links to the relevant procedures.
- Updated callers, usage examples, documentation links, Bash root discovery,
  and Windows repository-root discovery for the extra directory level.
- Ran `dockpipe init`, removed its generated example, and moved the four local
  workflows from `.dockpipe/` to `workflows/<name>/config.yml`.
- Removed generated package metadata and the empty secrets section from
  `dockpipe.config.json`; it declares only schema and local workflow roots.
  This is an optional workflow consumer, with no authored package manifest.

## Validation

- All 57 Python tests passed directly and through the named DockPipe test workflow.
- The relocated loopback tool's offline `self-test` passed for both transports.
- Syntax checks passed for all 26 shell scripts and 21 PowerShell scripts.
- Root discovery passed for all 12 moved shell scripts that calculate a repository
  root, evaluating only their directory assignments from outside the checkout.
- All 81 local Markdown links in the audited documentation resolve. Agent/task
  indexes parse and their paths exist.
- DockPipe compiled all four workflows. Named build, clean, test and check runs
  passed; build and clean used a temporary source copy to preserve local artifacts.
- Original files and executable modes are preserved. Driver sources, CI,
  packaging, tests, and release/maintenance scripts are byte-exact against the
  snapshot taken before this task. `git diff --check` passed.

No hardware-facing script bodies, Windows captures, service changes, module
loads, or register experiments ran. No commit or publication was performed.
