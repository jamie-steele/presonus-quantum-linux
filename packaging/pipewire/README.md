# Packaged Quantum ACP Discovery Fix

`0001-stop-after-complete-ucm-profile.patch` targets PipeWire **1.6.2**, not the
Quantum kernel driver. Native `quantum-dkms` revision 4 builds this patch into
a private runtime plugin and installs the WirePlumber startup configuration
that selects it. It does not overwrite distro PipeWire libraries.

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

## Native Package Integration

The native workflow builds the private plugin in Ubuntu 22.04, rejects a
changed upstream source archive, applies the patch, and compiles the six ACP
units plus the upstream ACP SPA device wrapper. The builder rejects non-x86_64
output and symbols requiring newer than glibc 2.35. Native DEB and RPM builds
require this compiled artifact and verify its patch, router and binary hashes;
a patch-only package is no longer a supported build result.

The plugin is installed at
`/usr/lib/quantum-dkms/spa-0.2/alsa/libspa-alsa.so`. A package-owned WirePlumber
user-service drop-in prepends the private plugin directory to `SPA_PLUGIN_DIR`.
On the next login/reboot, ordinary ALSA factory loading reaches this plugin.
Only `api.alsa.acp.device` instances carrying Quantum PCI IDs `1c67:0104` use
the patched code. Other cards and all other ALSA factories are forwarded to
the installed distro plugin. Audio PCM transport remains distro code. Internal
ACP symbols are hidden to prevent symbol collisions between the two builds.
Distro plugin updates are used on the next process start without rebuilding
Quantum's private plugin.

The package includes private mixer data, upstream notices, LGPL 2.1 text,
the exact upstream source archive, router, patch and build script. These
corresponding sources are under `/usr/share/doc/quantum-dkms/acp/source`.
To rebuild, use that directory as the repository root in an Ubuntu 22.04
container with `build-essential libasound2-dev git python3` installed:

```bash
python3 scripts/release/build_acp.py /tmp/rebuilt-acp \
  --archive pipewire-1.6.2.tar.gz
```

No install-time download, compilation of PipeWire, library diversion, module
load or audio-service restart is performed. The driver still builds through
DKMS. Removal deletes the private plugin and startup drop-in. Reboot after
install, upgrade or removal so the user service reloads its environment and
no process retains old mapped code. Existing custom WirePlumber units or
`SPA_PLUGIN_DIR` overrides require inspection; the integration targets the
distro's standard `wireplumber.service` and standard x86_64 SPA directories.

Native lifecycle tests instantiate the installed SPA factory and use the
installed startup environment with the actual distro PipeWire loader. They
assert all 39 Quantum PCM probes, original pointers for other factories, and
PCI-ID selection for unrelated cards. Locally, these runtime checks passed
on Ubuntu 22.04, Debian 13, and Ubuntu 26.04; the full install/upgrade/removal
check passed on Ubuntu 22.04. This supplements the original/fixed full-ACP
compatibility matrix. It still substitutes null PCM transport and
is not hardware or a running desktop-session acceptance test.

Revision 4 must be built, tested and published before APT users receive it.
Merging source alone does not publish new native assets or refresh the feed.
The standalone source/DKMS installer does not install this private plugin;
its audio-stack integration remains separate. The upstream PipeWire patch
submission and reporter hardware confirmation are also still pending.
