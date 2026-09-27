# Linux driver testing

The default backend is Nicholas Johnson's `snd-quantum` RFC, pinned in
`driver/upstream.lock`. Read [CURRENT_STATUS.md](../notes/CURRENT_STATUS.md)
before a live test: compilation is not audio acceptance, and historical in-house
results do not transfer to the RFC.

## Offline checks

```bash
make -C driver upstream-sync
make -C driver W=1
python3 -m unittest discover -s tests -v
python3 scripts/release/validate-audio.py alsa
```

Only `upstream-sync` downloads source. To test the retained research fallback,
build with `QUANTUM_DRIVER=inhouse`. Distro DKMS/staging checks are documented
in [RELEASES.md](RELEASES.md) and run in disposable containers.

## Read-only hardware inspection

```bash
lspci -nnk -d 1c67:0104
cat /proc/asound/cards
aplay -l
arecord -l
modinfo snd-quantum
```

Check the actual PCI driver owner and ALSA card ID. The original RFC defaults
to `Quantum2626`; the fallback defaults to `P2626`. `modinfo` describes the module
on disk, which may differ from the loaded module after an update. Record the
kernel, release manifest or source lock, selected backend, and desktop versions.

## Live test boundaries

Choose one bounded test and follow [hardware-testing.md](agents/hardware-testing.md).
Installation and reboot selection are in [RELEASES.md](RELEASES.md). Avoid a live
swap between competing backend modules during ordinary desktop playback.

Begin at the fixed 48 kHz, 26-channel S32_LE desktop baseline. Verify the active
PCM geometry and kernel logs, then test one analog path at a controlled level.
Do not send a two-channel/S16_LE file directly to the raw 26-channel PCM; use the
named UCM endpoint or a correctly prepared multichannel fixture. For continuity
experiments use [LOOPBACK_CONTINUITY_TESTING.md](LOOPBACK_CONTINUITY_TESTING.md)
after checking that its chosen backend and instrumentation match the test.

Stop on DMA/IOMMU faults, page-table or command timeouts, a lost desktop graph,
or an unrecoverable stop. Capture the result before any recovery action. Do not
combine a rate change, module swap, and new desktop policy into one experiment.

The [old in-house guide](historical/INHOUSE_LINUX_TESTING.md) is retained for
research provenance. Its debug parameters and register examples are not RFC options.
