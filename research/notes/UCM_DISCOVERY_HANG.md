# Issue 33: UCM Discovery CPU Exhaustion Candidate

## Finding (2026-10-25)

Static inspection and a bounded offline reproduction identify exponential subset
enumeration in PipeWire 1.6.2's ACP UCM profile builder as the leading candidate
for [issue #33](https://github.com/jamie-steele/presonus-quantum-linux/issues/33).
This is a demonstrated algorithmic failure mode for the packaged device layout,
not a stack trace or confirmed root cause from the reporter's computer.

The revision-2 DEB contains 13 stereo playback devices and 26 mono capture
devices under one HiFi verb. All 39 devices have distinct PCM strings in their
respective direction and no SupportedDevices/ConflictingDevices restrictions.
Under ACP's `devset_supports_device()` predicate they are mutually compatible.

PipeWire's `iterate_device_subsets()` visits compatible nonempty subsets.
`iterate_maximal_device_subsets()` filters out subsets that can be extended, but
does not prune their enumeration. For 39 mutually compatible devices it returns
the full set immediately, then visits the remaining proper subsets before
terminating. This requires `2^39 - 1 = 549755813887` subset visits for one profile.

Call path, inspected in the PipeWire 1.6.2 release sources:

```text
ALSA ACP device impl_init()
  acp_card_new()
    pa_alsa_ucm_add_profile_set()
      ucm_create_verb_profiles()
        iterate_maximal_device_subsets()
          iterate_device_subsets()
      ucm_probe_profile_set()  # reached only after profile construction finishes
```

This is synchronous device initialization. If this path is entered during
WirePlumber discovery, it can prevent initialization completing and delay other
device/session work. It offers an explanation for CPU use, missing HDMI as well
as Quantum nodes, and an unresponsive `wpctl` without a kernel DMA error. The
reporter's exact blocked or spinning thread is still unobserved.

Primary sources:

- [PipeWire 1.6.2 UCM profile generation](https://github.com/PipeWire/pipewire/blob/1.6.2/spa/plugins/alsa/acp/alsa-ucm.c)
- [ACP card initialization](https://github.com/PipeWire/pipewire/blob/1.6.2/spa/plugins/alsa/acp/acp.c)
- [ALSA ACP SPA device initialization](https://github.com/PipeWire/pipewire/blob/1.6.2/spa/plugins/alsa/alsa-acp-device.c)

## Offline Evidence

- `make -C driver upstream-verify` passed. Each extracted revision-2 driver C/H
  file is compared to the verified cache separately from the UCM investigation.
- Inspected DEB SHA-256:
  `34bdded811d7e5b0efe2ea366b7c60ca0f1a2b5dbadaedf976bcc6f62c6239af`.
- Parsed that DEB's UCM files in an isolated ALSA_CONFIG_UCM2 tree with
  `alsaucm -c P2626 dump json`. Confirmed 39 devices, 13 distinct playback PCMs,
  26 distinct capture PCMs and no nonempty compatibility restrictions. No PCM
  was opened. Parsing alone does not exercise ACP profile generation.
- Compiled the two iterator functions extracted unchanged from PipeWire 1.6.2,
  with an ordered-set shim and a compatibility predicate specialized to the
  verified mutually compatible Quantum layout. This is an algorithm harness,
  not the full PipeWire/WirePlumber runtime. The shim retains ordered backtracking
  and instruments subset copies; it does not model other device configurations.

| Devices | Subsets visited | Maximal profiles returned |
| --- | ---: | ---: |
| 4 | 15 | 1 |
| 8 | 255 | 1 |
| 12 | 4095 | 1 |
| 16 | 65535 | 1 |
| 20 | 1048575 | 1 |
| 39 | Stopped at 1000000 visits | Second search still running |

Every completed small case asserted `visits == 2^N - 1` and one maximal profile.
The 39-device run was explicitly budget-limited; the full search was not run.
Temporary source, harness builder, executable, UCM dump and sanitized analysis
inputs remain under `/tmp/quantum33-audit`; no raw journal is added to Git.

## Driver Paths Reviewed

- `quantum_pcm_hw_params()` holds dma_mutex across sample-rate negotiation and
  page-table activation. The TCI rate response requests a 1000-ms timeout;
  transmit-slot acquisition and page-table polling have finite retry counts.
  Repeated failures can delay probing, and mutex acquisition itself has no
  timeout. No specific permanent lock cycle was established by this inspection.
- `quantum_process_audio()` releases dma_mutex before calling
  `snd_pcm_period_elapsed()`, avoiding the obvious synchronous-trigger
  self-deadlock. PCM is marked nonatomic, so mutex/sleep use in its callbacks
  is not by itself evidence of an atomic-context bug.
- Command RX processing and the IRQ thread drain work without an explicit
  per-invocation budget. A continually replenished or stuck device ring remains
  a secondary CPU-consumption hypothesis requiring IRQ/worker measurements.
- UCM dshare/dsnoop plugin opening can configure hardware before later streaming
  starts. ACP opens nonblocking PCMs, but that does not impose a wall-clock
  deadline on plugin setup, kernel callbacks or IPC synchronization. Neither
  plugins nor the driver have been proven safe for this reporter by this audit.

## New Reporter Journal

The [second failed-boot journal](https://github.com/jamie-steele/presonus-quantum-linux/issues/33#issuecomment-6402907927)
shows the upstream module registering and no Quantum page-table, command-response
or DMA-allocation timeout messages. It contains the known revision-2 Lua warning.
The service-alias output now resolves both names to WirePlumber with no load
error. The user session ultimately times out during shutdown and multiple
processes, including WirePlumber and PipeWire, are killed. Aggregate session CPU
time does not identify which process consumed CPU, and forced session teardown
does not by itself prove an audio-specific deadlock.

## Next Discriminators And Fix Direction

Confirm the active spinning thread in a bounded reproduction: a userspace stack
inside the subset iterators would distinguish this path from a thread blocked
in an ALSA ioctl, semaphore, or kernel mutex. A disposable full-ACP synthetic
card fixture could validate profile-construction behavior without Quantum
hardware. The prior ARM64 startup test lacked a Quantum card and therefore did
not exercise these 39 UCM devices.

A candidate upstream correction should prune redundant subsets or special-case
an entirely compatible device set, with general compatibility-graph tests.
Do not invent conflicts or remove mono endpoints solely to reduce enumeration;
those changes would alter valid simultaneous-routing contracts. Merely fixing
the Lua warning in PR #36 does not change this algorithm.

No driver/UCM policy change, package installation, service restart, module load,
or hardware test was performed. Root cause and any fix remain unconfirmed on
the reporter's computer.

## Full ACP Confirmation And Candidate Fix (2026-10-25)

The investigation now includes the real `acp_card_new()` entry point, compiled
from all six PipeWire 1.6.2 ACP source units and linked against libasound 1.2.8.
Real libasound parses the repository's full 39-device UCM profile. Card lookup
is redirected to the virtual P2626 profile, PCM opens use a null transport,
and control opens return ENODEV. These substitutions avoid hardware and do not
replace ACP's profile builder, compatibility predicates or mapping logic.

- Original: hit the three-second deadline with one UCM open and zero PCM opens.
  Symbolized stack: `acp_card_new -> pa_alsa_ucm_add_profile_set ->
  ucm_create_verb_profiles -> iterate_maximal_device_subsets ->
  devset_supports_device`.
- Patched: returned in approximately 0.003 seconds with Off and HiFi profiles,
  39 devices, 39 ports, and all 39 null PCM opens. The patch stops enumeration
  after finding a compatible full-device profile and frees the iterator state.
- Five smaller original/fixed compatibility fixtures returned identical profile
  names and device membership, including conflicts and unequal maximal groups.

The discovery stall and its fix are reproduced in full ACP with synthetic
hardware boundaries. This is stronger than the earlier specialized iterator
harness, but still does not identify the reporter's runtime stack or validate
physical transport. General partially compatible large graphs are not optimized
by this focused fast path.

The [patch and reproduction instructions](../../packaging/pipewire/README.md)
are retained in the repository. Run `scripts/experiments/ucm_acp_discovery.py`
against unmodified PipeWire 1.6.2 source. Evidence from the repeatable run is at
`/tmp/quantum-full-acp-b1ll89fe`; earlier full-ACP build/stack evidence is at
`/tmp/quantum33-full-acp`.

No installed PipeWire library, Quantum module, UCM policy, or live service was
changed. The patch is for upstream/downstream review and is not automatically
consumed by quantum-dkms. Submission and deployment remain separate steps.

### Final Device-Free Isolation Check

The syscall audit found that the initial host prototype's public ALSA symbol
overrides did not intercept internal card-info/version queries. These were
read-only metadata requests, not control writes or PCM hardware operations.
The final runner therefore refuses `/dev/snd`, adds card-index/local-config
control overrides, and runs in a disposable Ubuntu 22.04 container with no
sound devices, a read-only root filesystem, no network, and all capabilities
dropped. No host services, modules or installed configuration were changed.

All twelve full-ACP cases passed in that container with libasound 1.2.6.1:
the original Quantum case hit the deadline at 3.003 seconds with zero PCM opens;
the patched case completed in 0.003 seconds with 39 devices/ports. The five
smaller original/fixed layouts retained identical profiles and memberships.
A separate container syscall trace shows no successful sound-device opens and
no ioctls. The authoritative final evidence is under
`/tmp/quantum33-full-acp/container-evidence/quantum-full-acp-vkab874k` and
`/tmp/quantum33-full-acp/container-evidence/container-syscalls.log`.
