# PipeWire UCM Discovery Fix Candidate

`0001-stop-after-complete-ucm-profile.patch` targets PipeWire **1.6.2**, not the
Quantum kernel driver. It is an upstream patch candidate; `quantum-dkms` does
not apply it, replace distro PipeWire libraries, or install a patched service.

## Problem And Change

Quantum's HiFi verb has 39 mutually compatible devices: 13 stereo playback
devices and 26 mono capture devices. ACP finds the full-device profile first,
then exhaustively enumerates its proper subsets to check for other maximal
profiles. The resulting search has `2^39 - 1` nonempty subsets.

The patch ends profile enumeration after producing a compatible full-device
profile. Every proper subset can be extended and therefore cannot be another
maximal profile. Profiles with conflicting devices retain the original search.
The iterator state is released before exiting; all endpoint mappings remain.

This fixes the demonstrated full-ACP search stall. It does not establish the
exact runtime root cause on the issue-33 reporter's machine, and does not fix
the general exponential behavior of other, partially compatible layouts.

## Reproduce And Verify Without Hardware

Use a disposable container without sound-device passthrough. No running
PipeWire/WirePlumber service is required. Obtain the unmodified PipeWire 1.6.2
source and, from this repository, run:

```bash
docker build -t quantum-acp-test:issue33 tests/fixtures/acp
pipewire_source=/absolute/path/to/pipewire-1.6.2
evidence=$(mktemp -d /tmp/quantum-acp-evidence.XXXXXXXX)
docker run --rm --network none --read-only \
  --user "$(id -u):$(id -g)" --cpus=2 --memory=2g \
  --cap-drop=ALL --security-opt=no-new-privileges \
  -v "$PWD:/workspace:ro" -v "$pipewire_source:/pipewire:ro" \
  -v "$evidence:/tmp" quantum-acp-test:issue33 \
  python3 /workspace/scripts/experiments/ucm_acp_discovery.py /pipewire
```

The image supplies a C compiler, ALSA development files and UCM data, Python,
Git and optional syscall tracing. Building the image downloads these ordinary
dependencies; the test container itself has networking disabled and all
capabilities dropped. The runner refuses to run if `/dev/snd` exists.

The source archive is available from
[the upstream release tag](https://github.com/PipeWire/pipewire/releases/tag/1.6.2).
The GitHub tag archive used locally had SHA-256
`2014c187fccdd6d245585be4eda7dabd781dcddd921604c40ab015bba6cb042d`;
the runner independently pins the `alsa-ucm.c` bytes before applying the patch.
The supplied source is never edited. Builds, copied configuration, logs and
JSON results are written into a new `/tmp/quantum-full-acp-*` directory.

The executable calls real `acp_card_new()` and all six unmodified ACP source
units, with only `alsa-ucm.c` changed in the fixed build. Real libasound parses
the repository UCM. The test substitutes two hardware boundaries:

- Card lookup `hw:0` is redirected to the virtual `P2626` UCM profile.
- ALSA PCM opens are redirected to libasound's null PCM; public control opens
  return ENODEV. A private asound configuration prevents reading user PCM overrides.
  Internal libasound lookups can bypass symbol interposition, so the absence of
  sound devices in the container is a necessary isolation boundary.

Thus profile construction, compatibility checks, mapping/probe loops, exported
card profiles/devices/ports, and teardown run through real ACP. It does not
validate actual card discovery, dshare/dsnoop transport, kernel callbacks,
physical audio, a live WirePlumber process, or a distro-patched ACP build.
Only optional Valgrind instrumentation is disabled by the standalone build.

The original 39-device run must hit its three-second deadline before any PCM
open. The fixed run must return both Off and HiFi with 39 devices, 39 ports and
39 null PCM opens. Original/fixed profile names and exact device memberships
must also match for single-device, four compatible devices, one conflict pair,
a three-device conflict chain, and two independent conflict pairs.

Final container result (2026-10-25, libasound 1.2.6.1): original deadline at 3.003 seconds,
zero PCM opens; fixed completion at 0.003 seconds. These are synthetic execution
times, not physical discovery or audio-latency measurements. All five smaller
original/fixed compatibility comparisons passed.

A syscall trace of the final fixed container run shows failed lookups for absent
control devices, no successful sound-device opens, and no ioctls. An earlier
host prototype unexpectedly performed read-only card-info/version queries:
the syscall audit caught that, and the authoritative regression was rerun in
the device-free container. No PCM hardware, settings, modules or live services
were changed by those prototype queries.

## Deployment Boundary

The patch needs review and submission to PipeWire, or an explicitly reviewed
downstream PipeWire build/backport. Neither has been published or installed.
The Lua-warning correction in PR #36 is separate and cannot apply this ACP fix.
Do not ask the reporter to repeat a failing installation merely to test that PR.
