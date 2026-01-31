# PreSonus Quantum 2626 — Linux driver (skeleton)

Out-of-tree ALSA PCI driver skeleton for PreSonus Quantum 2626 (and family: 0101, 0102, 0103, 0105 from `driver-reference/pae_quantum.inf`). The card is registered and a PCM device appears. **IRQ path is wired:** the driver requests the device IRQ and calls `snd_pcm_period_elapsed()` from the interrupt handler for active playback/capture; if IRQ request fails, a timer fallback drives the pointer. **No actual hardware I/O yet** — no DMA or register programming; real playback/capture needs reverse engineering of `pae_quantum.sys` or the device BAR.

## Base / references

- **Kernel:** [Writing an ALSA Driver](https://docs.kernel.org/sound/kernel-api/writing-an-alsa-driver.html) (Takashi Iwai).
- **Structure:** `sound/pci/ens1370.c` (Ensoniq AudioPCI) — PCI table, probe/remove, chip create, PCM registration.
- **IDs:** `driver-reference/pae_quantum.inf`; Linux PCI baseline in `notes/DIAGNOSIS_RESULT.md` (1c67:0104, BAR 0 = 1 MiB).

## What this driver does

- **PCI:** Claims 1c67:0101, 0102, 0103, 0104, 0105.
- **Probe:** Enables device, requests regions, maps BAR 0 with `pci_iomap`, logs the first 64 bytes of BAR 0 (MMIO+0x00..0x3c) to dmesg for reverse-engineering, tries MSI first (Thunderbolt often has legacy IRQ 0), then requests the device IRQ when valid (>0) with a shared handler that signals period elapsed for active substreams, creates ALSA card + one PCM (playback + capture), registers card.
- **Remove / free:** Frees IRQ (if requested), frees MSI vectors (if allocated), unmaps BAR, releases regions, disables PCI.
- **PCM:** Open/close/hw_params/hw_free/prepare/trigger/pointer; hardware descriptor allows common rates/channels so the device shows in `aplay -l` / `arecord -l`. Pointer is driven by IRQ (or timer fallback). No data is moved to/from hardware yet.

## Build and load

```bash
cd driver
make
sudo insmod snd-quantum2626.ko
```

Or install and load via modprobe:

```bash
make install
sudo modprobe snd-quantum2626
```

Check:

```bash
aplay -l
arecord -l
cat /proc/asound/cards
```

Unload:

```bash
sudo rmmod snd-quantum2626
```

### Optional: dump MMIO at prepare/trigger (for reverse-engineering)

Load with `dump_on_trigger=1` to log the first 64 bytes of BAR 0 at each `prepare` and `trigger START/STOP`:

```bash
sudo modprobe snd-quantum2626 dump_on_trigger=1
```

Then run `aplay` or `arecord`; `dmesg` will show "MMIO at prepare", "MMIO at trigger START", "MMIO at trigger STOP". Compare with baseline (see `docs/REVERSE_ENGINEERING_PLAN.md` and `scripts/probe_during_playback.sh`).

## Next steps (real audio)

1. **IRQ:** Done. Handler runs and signals period elapsed; use dmesg to confirm IRQ is firing (or that timer fallback is used). Later: read a status register in the handler and only signal when the device actually reports a period (reverse-engineer BAR layout).
2. **PCM:** Implement prepare/trigger/pointer to program the device’s DMA/buffers and report the real hardware pointer; use `chip->iobase` and the MMIO dump (dmesg after load) to infer register layout from `pae_quantum.sys` or experimentation.
3. **Format/channels:** Adjust `quantum_pcm_hw` and constraints from device capabilities (e.g. 26 I/O from specs; may require multiple PCMs or channel maps).

## Layout

- `snd-quantum2626.c` — Single-file driver (PCI table, probe/remove, chip, stub PCM).
- `Makefile` — Out-of-tree kernel build.
- `README.md` — This file.
