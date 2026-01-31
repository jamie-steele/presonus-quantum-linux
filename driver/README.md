# PreSonus Quantum 2626 — Linux driver (skeleton)

Out-of-tree ALSA PCI driver skeleton for PreSonus Quantum 2626 (and family: 0101, 0102, 0103, 0105 from `driver-reference/pae_quantum.inf`). The card is registered and a PCM device appears; **no actual hardware I/O yet** — PCM ops are stubs. Real playback/capture and IRQ handling need reverse engineering of `pae_quantum.sys` or the device BAR.

## Base / references

- **Kernel:** [Writing an ALSA Driver](https://docs.kernel.org/sound/kernel-api/writing-an-alsa-driver.html) (Takashi Iwai).
- **Structure:** `sound/pci/ens1370.c` (Ensoniq AudioPCI) — PCI table, probe/remove, chip create, PCM registration.
- **IDs:** `driver-reference/pae_quantum.inf`; Linux PCI baseline in `notes/DIAGNOSIS_RESULT.md` (1c67:0104, BAR 0 = 1 MiB).

## What this driver does

- **PCI:** Claims 1c67:0101, 0102, 0103, 0104, 0105.
- **Probe:** Enables device, requests regions, maps BAR 0 with `pci_iomap`, creates ALSA card + one PCM (playback + capture), registers card. No IRQ requested yet.
- **Remove / free:** Unmaps BAR, releases regions, disables PCI.
- **PCM:** Stub open/close/hw_params/hw_free/prepare/trigger/pointer; hardware descriptor allows common rates/channels so the device shows in `aplay -l` / `arecord -l`. No data is moved.

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

## Next steps (real audio)

1. **IRQ:** Add an interrupt handler and `request_irq` in `snd_quantum_create`; call `snd_pcm_period_elapsed()` from the handler when the device notifies a period (reverse-engineer Windows driver or BAR layout).
2. **PCM:** Implement prepare/trigger/pointer (and optionally hw_params) to program the device’s buffers and report the hardware pointer; use `chip->iobase` to read/write registers (layout from `pae_quantum.sys` or experimentation).
3. **Format/channels:** Adjust `quantum_pcm_hw` and constraints from device capabilities (e.g. 26 I/O from specs; may require multiple PCMs or channel maps).

## Layout

- `snd-quantum2626.c` — Single-file driver (PCI table, probe/remove, chip, stub PCM).
- `Makefile` — Out-of-tree kernel build.
- `README.md` — This file.
