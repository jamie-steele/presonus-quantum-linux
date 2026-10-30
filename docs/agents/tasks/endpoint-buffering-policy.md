# TASK-026 Quantum endpoint buffering policy correction

## Status

Active

## Objective

Publish native revision 5 with Quantum buffering rules matching current and
legacy UCM endpoint names in WirePlumber 0.4 and 0.5.

## Evidence And Discoveries

- On 2026-10-29, the installed revision-4 rule matched PCM-derived names while
  the published nodes used UCM device names. Playback headroom was zero instead
  of the requested 256 frames. This confirms a policy matching defect.
- Issue #33 now reports device discovery with silence/periodic buzzing. Its
  latest metadata forces graph quantum 1024; the local session used 256 without
  a forced quantum. A common playback root cause remains unconfirmed.
- Initial local diagnostics were followed by a user-reported system crash and
  reboot. No service restart, module reload, or setting change had been issued;
  causality is undetermined. Further verification here is offline only.
- The corrected user-level Lua override was installed with a backup at the
  user's request, without restarting audio. Activation/audible acceptance has
  not been established.

## Changes

- Scope endpoint rules to exact Quantum driver identities and HiFi direction.
- Preserve 128-frame periods, four periods per buffer, playback-only headroom,
  UCM routing, and the unchanged upstream RFC.
- Increment native revision to 5 and document activation/override boundaries.

## Validation

- Offline Lua execution, SPA-JSON parsing, and 174 matching cases passed,
  covering all 39 UCM endpoints, legacy names, both backends, and exclusions.
- Nine policy-selection, sixteen native-package, and eight migration tests
  passed before release preparation. Hosted release gates remain required.

## Remaining Work

- Commit and review the focused change, pass hosted distro/APT checks, merge,
  publish native revision 5, and verify its signed APT delivery.
- Reporter audible confirmation remains separate; no issue comment is authorized.

## Publication migration follow-up

The first native publication run (40987566032) correctly blocked publication:
the immutable source installer leaves the previous regular Lua policy, while
revision 5 changes the template. The selector treated the old generated file
as customized. PR checks had built a fresh source installer with the new policy,
so their migration fixture did not expose the historical-file difference.

The selector now recognizes only the two exact published legacy policy hashes;
any edited content remains protected, as do unrelated symlinks and user overrides.
Immutable historical fixtures test migration in both policy generations and
ensure edited variants block changes without partially switching either file.
No revision-5 assets were published by the failed run. Rerun full release gates
before publication; native revision remains 5.
