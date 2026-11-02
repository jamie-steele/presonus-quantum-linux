# TASK-025 Issue 33 UCM Discovery Hang Investigation

## Status

Active

## Objective

Identify code paths that could stall the whole audio graph during Quantum
discovery, without another blind reinstall or live hardware mutation.

## Evidence And Decisions

- The revision-2 driver source matches the pinned, verified RFC cache.
- Parsed the exact shipped UCM profile and reproduced exponential enumeration
  in extracted PipeWire 1.6.2 subset iterators with a specialized offline harness.
- The leading candidate is redundant enumeration of 39 mutually compatible
  devices, before PCM probing. This is not yet confirmed by reporter stacks.
- Latest reporter logs confirm the alias correction and still lack Quantum
  timeout diagnostics. They do not identify per-process CPU consumption.
- Canonical analysis, primary source links, reproduction results and remaining
  driver/IPC alternatives: [UCM discovery hang](../../../research/notes/UCM_DISCOVERY_HANG.md).

## Validation

- Verified upstream cache; compared extracted driver source files; parsed exact
  packaged UCM without a hardware PCM; built the extracted-iterator C harness
  with `-std=c11 -Wall -Wextra -Werror -O2`.
- Completed and asserted cases through 20 devices. Explicitly stopped the
  39-device case at one million subset visits; no exhaustive large run.
- No runtime implementation changes or live hardware tests.

## Full ACP Reproduction And Fix Follow-Up

- User authorized full ACP reproduction and a fix if the failure mode was
  confirmed. The standalone test now builds all six real ACP source units and
  calls `acp_card_new()`; only hardware lookup and transport are substituted.
- Original PipeWire 1.6.2 stalls before PCM probing and reaches the explicit
  three-second deadline. The candidate patch returns Off/HiFi, 39 devices and
  39 ports, and completes all 39 null PCM opens in approximately 0.003 seconds.
- Five smaller original/fixed fixtures preserve exact profile names/device
  memberships, including pair, chain and independent conflict layouts.
- `packaging/pipewire/`: upstream source patch and review/reproduction README.
- `scripts/experiments/ucm_acp_discovery.py` and `tests/fixtures/acp/discovery.c`:
  reusable hardware-free full-ACP regression runner and hardware-boundary shim.
- No driver/UCM contract or installed service was changed. This is a PipeWire
  fix candidate, not an automatically installed quantum-dkms correction.
- The initial host prototype made incidental read-only card metadata queries;
  syscall auditing caught the incomplete interposition. The final runner
  requires no `/dev/snd` and passed all twelve cases in a device-free container
  with networking disabled, read-only root and all capabilities dropped. A
  container syscall trace confirms no successful sound-device opens or ioctls.

## Remaining Work

- Local reproduction and focused source fix are complete. Upstream review,
  submission, distro backport/deployment and reporter runtime confirmation are
  pending. Repository PR #38 is merged; upstream submission is separate.

## Native Delivery Follow-Up

- User requested that package upgrades deliver the runtime correction after
  PR #38 only retained the patch and reproduction harness.
- Native revision 4 requires a compiled, checksum-verified private ACP plugin.
  The build applies the pinned PipeWire 1.6.2 patch; a WirePlumber service drop-in
  activates it after login/reboot. Quantum PCI IDs select the patched factory;
  unrelated cards and ALSA factories delegate to the installed distro plugin.
- Corresponding sources, licenses and private mixer data are included. Distro
  libraries are not replaced. No live host installation or audio restart is
  authorized or performed. Native publication remains a separate step.
- Canonical package behavior and validation: `packaging/pipewire/README.md`.

### Delivery Validation

- Built revision-4 DEB plus Fedora/openSUSE RPMs and revision-5 upgrade fixtures
  in a disposable Ubuntu 22.04 container. The plugin requires at most glibc 2.34,
  within the enforced glibc 2.35/x86_64 baseline.
- Real Ubuntu 22.04 package lifecycle passed: pre-fix revision 3 -> 4 upgrade,
  installed-factory discovery, same-version reinstall, WirePlumber policy
  trigger, revision 4 -> 5 upgrade, config preservation, and removal/purge.
- The exact DEB payload also passed actual distro PipeWire-loader discovery on
  Debian 13 and Ubuntu 26.04 with their ALSA UCM dependencies present. The
  Ubuntu 26.04 runtime check matches the reporter's release; it does not add
  full native distro/kernel lifecycle acceptance. All 39 Quantum mappings were
  probed twice (direct SPA factory and PipeWire loader). Unrelated factories
  retain distro pointers; PCI selector tests preserve unrelated/missing IDs.
- All 60 Python tests and the original/fixed 12-case ACP regression matrix
  passed; ShellCheck, YAML parsing and whitespace checks passed.
- No host library/configuration, module, live service or sound device was changed.
  No release publication or reporter hardware acceptance is claimed. Full native
  distro lifecycle/repository coverage remains enforced by the CI matrix.
