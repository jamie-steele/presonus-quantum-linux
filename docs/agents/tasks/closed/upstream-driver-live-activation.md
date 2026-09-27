# TASK-013 Upstream Driver Live Activation

## Status

Closed; the one-time migration/activation experiment was superseded on 2026-09-27
by adopting upstream as the main backend and completing build/install integration.
The failed discovery and later cold-boot observations below remain historical
evidence. This closure does not claim that runtime faults were fixed or authorize
another activation, rollback, or listening A/B.

## Objective

Activate the exact 2026-08-20 upstream RFC module on the verified Quantum 2626,
restore the intended UCM desktop graph, and obtain a bounded listening A/B
without losing the in-house rollback artifact.

## Scope

- Install and activate the hash-pinned upstream module and UCM selector.
- Verify PCI binding, ALSA registration, closed-state safety, and kernel faults.
- Diagnose the first desktop profile-selection result without initiating
  unauthorized playback or retries.
- Retain the exact installed in-house module as rollback.

## Out Of Scope

- Automatic restart, module-load, or playback retries after a stopped result.
- Claiming that upstream fixes the historical pops before matched-geometry
  listening evidence exists.
- Editing the pinned RFC source during the activation checkpoint.

## Relevant Context

- `docs/agents/tasks/closed/upstream-driver-backend-integration.md` owns the completed
  external-source integration and dual-backend build evidence.
- `notes/CURRENT_STATUS.md` owns the current live backend and desktop state.
- The installed in-house rollback SHA-256 is
  `d54f2bf411430c5ed350b5999d07795e9d7de6aa3801332c9e0d97152fa9b45e`.

## Constraints

- Preserve the existing dirty checkout and all unrelated loopback work.
- Stop after an unexpected graph, fault marker, failed binding, or failed
  service recovery; obtain fresh approval before retrying.
- Leave playback to the user unless explicitly requested otherwise.

## Plan

1. Install and activate the exact upstream artifact once.
2. Verify kernel and ALSA state without playback.
3. Restore the complete UCM graph through one separately approved desktop
   recovery action.
4. Run a bounded, matched-geometry listening and fault-counter A/B.
5. Retain upstream or roll back based on the recorded result.

## Evidence And Discoveries

- 2026-08-20: preflight proved PCI `1c67:0104`, matching current-kernel
  artifacts, closed hardware PCMs at the initial observation, and the exact
  installed fallback hash.
- 2026-08-20: the first controller revision stopped before mutation because a
  PipeWire capture PCM was active. The corrected controller authenticated and
  stopped the user audio stack before requiring closed Quantum handles.
- 2026-08-20 19:34 EDT: controller SHA-256
  `a05066951fa1f953f8163c0357fda322ec616cb6d47b9100d069d77c48571c46`
  installed upstream module SHA-256
  `fe1f725a33a2c12fddb0f09ea8e849902fad8d65c5a1900d82278d8f4aebe2da`,
  installed the upstream UCM selector, stopped all five audio units, replaced
  `snd_quantum2626` with `snd_quantum`, and restarted all five units.
- Read-back proves `snd-quantum` owns the device, ALSA card 0 is Quantum2626,
  MSI IRQ 213 registered, srcversion is `65A6D16B4AFEEDFEEA3CF43`, both PCMs are
  closed, and no new kernel fault class appeared.
- WirePlumber returned only one generic multichannel sink and one generic
  multichannel source. The complete 13/26 UCM definition parses independently,
  but the PipeWire device selected ACP and the restart logged one aborted audio
  adapter activation.
- 2026-08-20 19:40 EDT: the user approved a desktop-only recovery attempt. A
  user-level copy of `alsa/wireplumber/51-quantum2626.lua` forced UCM using an
  `alsa.driver_name` match, but a five-unit audio restart still returned the
  generic 1/1 graph. That match is evaluated before ACP adds
  `alsa.driver_name`, so it did not reach the device.
- 2026-08-20 19:44 EDT: the rule was corrected to match the PCI vendor/product
  properties already present at discovery and installed user-level with exact
  SHA-256 `4fae5455807381f6ecc310c4cd94f75aff4b57b00894da3f05f77a38e8eb5486`.
  One WirePlumber-only restart proved `api.alsa.use-ucm=true` on the live
  Quantum device, but adapter activation again aborted and WirePlumber retained
  only the generic multichannel duplex profile.
- Independent read-only evidence now localizes the boundary: `alsaucm` opened
  the new `conf.d/snd-quantum/snd-quantum.conf` and `P2626/HiFi.conf`, while
  `spa-acp-tool` enumerated profile `HiFi` with 39 devices: 13 playback and 26
  capture. The failure is therefore in the WirePlumber 0.4/UCM adapter
  activation path, not evidence of a kernel transport fault or missing UCM
  install.
- 2026-08-20: immediate interface restoration was explicitly requested. The
  first rollback attempt stopped safely because three diagnostic
  `spa-acp-tool` processes started during this task still held controlC0. Those
  exact holders were terminated; `snd_quantum` then reached reference count
  zero, and the same hash-pinned rollback controller completed.
- Final read-back proves `snd_quantum2626` owns PCI `1c67:0104`, ALSA card 0 is
  `P2626` on IRQ 213, the loaded artifact matches SHA-256
  `d54f2bf411430c5ed350b5999d07795e9d7de6aa3801332c9e0d97152fa9b45e`,
  all five user audio units are active, Main is the configured/default sink,
  and the complete 13-output/26-input UCM graph is restored. Both PCMs were
  closed and the bounded rollback log had no fresh fault-class marker.
- 2026-08-21: a later upstream-backed 44.1-to-48-kHz desktop transition produced
  DMA reads to unmapped addresses, DMAR faults, page-table and sample-rate
  command timeouts, and an unusable graph. The boot ended uncleanly, but the
  persistent records do not prove a kernel panic or whole-machine crash cause.
- 2026-08-21: a cold boot reset the device and upstream auto-bound again because
  both installed modules advertise PCI `1c67:0104`. The 48-kHz UCM files parsed
  13 playback plus 26 capture devices, the complete graph returned, both PCMs
  were closed at the recorded checkpoint, and the user reported good playback.
  The active PCM rate was not captured before playback closed, so this is not
  sustained upstream acceptance and does not resolve the earlier DMA failure.

## Decisions

- Stop before playback because the active graph is not the intended matched
  UCM topology and cannot provide the planned comparison.
- Stop live retries after the separately approved desktop recovery attempts;
  another restart, profile mutation, playback test, or kernel rollback requires
  fresh user direction.
- Do not disturb the current cold-boot runtime under this paused live task or
  infer that its good listening interval resolves the earlier upstream faults.
  Further activation work remains offline until separately resumed.
- Retain both module artifacts, but make one backend the persistent boot owner
  before another reboot or live comparison. TASK-014 owns that source cleanup;
  this paused task retains the unresolved live evidence.

## Changes

- Installed `/lib/modules/7.0.11-76070011-generic/updates/snd-quantum.ko`.
- Installed `/usr/share/alsa/ucm2/conf.d/snd-quantum/snd-quantum.conf`.
- Loaded `snd_quantum`; retained the installed `snd_quantum2626` fallback.
- Installed the corrected WirePlumber rule under the user's configuration; the
  tracked source remains `alsa/wireplumber/51-quantum2626.lua`.
- Unloaded `snd_quantum`, reloaded the retained exact `snd_quantum2626`, and
  restored the in-house UCM graph through the user-run rollback controller.

## Validation

- Exact installed module hash and loaded srcversion match the offline artifact.
- PCI, ALSA, service, PCM, CPU-latency, and bounded kernel/service logs read
  back after activation.
- All three user audio services are active after the final WirePlumber-only
  restart, both Quantum PCMs are closed, and HDMI remains the active default
  sink. The recurring WirePlumber marker is `Object activation aborted: proxy
  destroyed`; no kernel fault marker accompanied it.
- Post-rollback validation supersedes that temporary graph state: all five
  units are active and the graph is exactly 13 outputs plus 26 inputs.
- Playback and capture were not initiated.

## Remaining Work

- No remaining migration task. Known desktop-discovery and DMA/rate-transition
  limitations remain in `notes/CURRENT_STATUS.md`. Diagnose a freshly reproduced
  upstream/integration problem when needed; do not resume this old activation plan.

## Closure Summary

Closed as superseded on 2026-09-27. The 2026-08-20 checkpoint failed at desktop
profile discovery and restored the in-house runtime without a listening A/B;
later cold-boot evidence recorded upstream binding. Both observations are retained
without treating either as the current host state or sustained upstream acceptance.
