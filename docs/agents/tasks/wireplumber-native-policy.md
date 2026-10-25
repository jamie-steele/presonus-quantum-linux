# TASK-020 WirePlumber Native Policy Selection

## Status

Active

## Objective

Fix [issue #35](https://github.com/jamie-steele/presonus-quantum-linux/issues/35):
native packages must activate only the policy for the installed WirePlumber
generation, including after a WirePlumber package upgrade.

## Decisions

- Keep both templates outside WirePlumber's configuration search paths and
  select one through a managed symlink. The unused Lua template must not appear
  in `main.lua.d` on WirePlumber 0.5.
- Select during package configuration. DEB file triggers and RPM transaction
  file triggers handle WirePlumber package updates; RPM also selects at the end
  of a Quantum upgrade after old package files have been removed.
- Preserve unexpected links and custom rules. Only exact legacy template
  copies and links to the private packaged templates are replaced automatically.
- Extend the existing pre-unpack backup to preserve managed symlinks and their
  template contents. Preserve compatibility with the existing revision-3
  migration backups; do not alter the RFC driver.
- Never restart services, open a PCM, load modules, or infer that this warning
  explains the separate slowdown and missing-device report in issue #33.

## Changes

- `packaging/native/wireplumber_policy.py`: version detection, selection,
  legacy-template conversion, custom-file preservation, and removal.
- Native staging/lifecycle hooks, DEB triggers, RPM transaction triggers, and
  pre-unpack backups integrate the policy selection.
- Native lifecycle checks require one active policy and exercise a real
  WirePlumber package reinstall to verify DEB trigger dispatch.
- `alsa/README.md` and `docs/RELEASES.md` explain the pending package behavior.

## Validation

- 57 Python tests pass, including both generation transitions, exact legacy
  files, custom files/links, symlink parents, removal after missing assets,
  Jammy version fallback, native hook generation, and pre-unpack link backups.
- Focused ShellCheck and Git whitespace checks pass.
- Ubuntu 22.04 (WirePlumber 0.4, kernel 5.15.0-198) and Debian 13
  (WirePlumber 0.5, kernel 6.12.113) passed native installation, reinstall,
  synthetic packaging-revision upgrade, custom backend-policy preservation,
  removal, and purge in disposable containers. Both passed real WirePlumber
  package reinstalls that dispatched the DEB file trigger and restored the
  correct policy after deliberately selecting the other generation.
- Fedora/openSUSE RPM variants built in a Debian RPM-tooling container;
  metadata inspection confirms the transaction triggers and Python dependency.
  Native Fedora/openSUSE lifecycle and real version-crossing distro upgrades
  were not run; both generation transitions are covered by the Python tests.
- Evidence is under `/tmp/quantum-wp35-validation`. No host modules or audio
  services were changed, and no physical audio acceptance is claimed.

## Remaining Work

- Local implementation and focused validation are complete. The isolated PR
  targets current master and includes only issue-35 changes. All 57 Python tests
  pass again in that clean checkout. Published release assets still stop at
  revision 2, so the pending revision-3 version remains appropriate.
- Merge, publication, public issue updates, and live audio tests remain separate
  follow-up operations.
