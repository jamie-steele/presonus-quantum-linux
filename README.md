# Quantum 2626 — Linux driver

Getting the **PreSonus Quantum 2626** Thunderbolt 3 audio interface working on Linux with an out-of-tree ALSA PCI driver.

## Device summary

- **Product:** PreSonus Quantum 2626  
- **Connection:** Thunderbolt 3 (no USB or PCIe card version)  
- **Audio:** 26×26 I/O, 24-bit/192 kHz, &lt;1 ms round-trip latency  
- **Official support:** macOS and Windows only (proprietary drivers)  
- **Linux:** No vendor driver; this repo is a community driver (PCI ID 1c67:0104).

---

## Current status (where we are)

- **Driver loads:** ALSA card appears (e.g. card 4). MSI interrupt works; prepare/trigger run.
- **Register programming (from Ghidra):** We program DMA buffer address at 0x10300 (playback) / 0x10304 (capture), and control at 0x100 (0x8 = start, 0x0 = stop). dmesg shows prepare/trigger and the values we write.
- **No sound yet:** Either the register map is incomplete (e.g. buffer size, sample rate, or different control bits), or physical output routing. Next step is more reverse-engineering on Windows (Ghidra + Python) to find buffer size, sample rate, and confirm control/stream start.

**Good stopping point for tonight.** Continue on Windows with Ghidra (and Python if you use it for RE) to refine the register map; then plug findings back into the driver.

---

## Quick start (Linux)

```bash
# Build
cd driver && make

# Load (after reboot, or if not loaded)
sudo modprobe snd-quantum2626
# Or first-time install: sudo make install && sudo modprobe snd-quantum2626

# Check card (e.g. card 4 = Quantum)
cat /proc/asound/cards

# Test playback (free the device first: stop wireplumber/pipewire)
systemctl --user stop wireplumber pipewire-pulse
aplay -D plughw:4,0 -r 48000 -f S16_LE -c 2 /usr/share/sounds/alsa/Front_Center.wav
systemctl --user start pipewire pipewire-pulse wireplumber
```

**Reload driver (after code changes):** Use `./scripts/reload_quantum_driver.sh` (stops audio, kills processes using card 4, rmmod/insmod, starts audio). If that still says "module in use", log out, switch to TTY2 (Ctrl+Alt+F2), run `sudo rmmod snd_quantum2626 && sudo insmod driver/snd-quantum2626.ko`, then switch back and log in.

---

## Docs and scripts

| What | Where |
|------|--------|
| **Reverse-engineering plan** | [docs/REVERSE_ENGINEERING_PLAN.md](docs/REVERSE_ENGINEERING_PLAN.md) — Phases: gather artifacts (Windows strings, Linux MMIO), Ghidra analysis, driver changes. |
| **No sound debugging** | [docs/NO_SOUND_DEBUG.md](docs/NO_SOUND_DEBUG.md) — What we program, likely causes, dump-on-trigger, next RE steps. |
| **Driver build/load** | [driver/README.md](driver/README.md) — Makefile, insmod/modprobe, optional dump_on_trigger. |
| **Register guesses** | [notes/REGISTER_GUESSES.md](notes/REGISTER_GUESSES.md) — Offsets from Ghidra; update as you find more. |
| **MMIO baseline** | [notes/MMIO_BASELINE.md](notes/MMIO_BASELINE.md) — BAR 0 values at load. |

**Scripts:** `scripts/reload_quantum_driver.sh` (Linux: reload driver), `scripts/capture_mmio_baseline.sh` (Linux: save MMIO from dmesg), `scripts/windows_re_next_run.ps1` (Windows: strings + Ghidra checklist), `scripts/windows_re_strings.ps1` (Windows: strings only).

---

## Next steps (Windows + Ghidra / Python)

1. **Ghidra:** In `pae_quantum.sys` find where the Windows driver **writes** buffer size, period size, sample rate, and stream start/stop. Confirm offsets (0x100, 0x10300/0x10304) and add any missing registers to [notes/REGISTER_GUESSES.md](notes/REGISTER_GUESSES.md).
2. **Driver:** Update `QUANTUM_REG_*` and prepare/trigger in `driver/snd-quantum2626.c` to program any new registers (buffer size, rate, etc.).
3. **Test:** Reload driver, run aplay, check dmesg and physical output.

---

## Path of least resistance (historical)

1. **Diagnose on Linux first**  
   Plug in the interface (with Thunderbolt authorized) and capture:
   - Does it show up in `lspci`?
   - Any `dmesg` / kernel messages?
   - Any ALSA devices (`aplay -l`, `arecord -l`)?  

   If it appears as PCIe but has no ALSA device, we know the bus is fine and the gap is a missing audio driver.

2. **Profile on Windows 11 only when reverse-engineering**  
   Use Windows only when you need to reverse-engineer the device (e.g. to write or adapt a Linux driver). On a Windows 11 machine with the Quantum 2626 working you can capture vendor/device IDs, driver names, and resource usage — see `docs/WINDOWS_PROFILING.md`. We don’t need Windows for basic diagnosis; Linux already gives us the PCI identity (e.g. 1c67:0104).

3. **Use the profiling output for Linux**  
   - Match the same vendor/device ID on Linux (`lspci -nn`).
   - If the device is a standard PCIe audio design, existing ALSA drivers might be extended; if it’s custom, we need a minimal driver or reverse‑engineering.

- **Stage 1 (Linux):** [docs/DIAGNOSIS.md](docs/DIAGNOSIS.md) — diagnosis plan (done: device 1c67:0104 visible, no driver).
- **Try without reverse engineering:** [docs/TRY_WITHOUT_RE.md](docs/TRY_WITHOUT_RE.md) — `new_id` with snd_hda_intel was tried; rejected (Invalid argument). Path closed without reverse engineering.
- **Stage 2 (Windows):** [docs/STAGE2_RUNBOOK.md](docs/STAGE2_RUNBOOK.md) — Profile on Windows 11, fill `notes/windows_profile.txt` for driver work.
- **Next — build our own driver:** [docs/NEXT_DRIVER.md](docs/NEXT_DRIVER.md) — Options after Stage 2 (extend existing driver vs new ALSA PCI driver); points at kernel docs and repo notes.
- **Windows driver reference:** [driver-reference/](driver-reference/) — PreSonus Windows driver files (INF + notes) for IDs and reverse engineering; `.sys`/`.cat`/`.PNF` kept locally only.
- **Linux driver:** [driver/](driver/) — Out-of-tree ALSA PCI driver; card + PCM, Ghidra-derived register programming (buffer 0x10300/0x10304, control 0x100). Build: `make` in `driver/`; load: `sudo modprobe snd-quantum2626` (after `sudo make install`) or `sudo insmod snd-quantum2626.ko`. Real audio: more RE (buffer size, sample rate, control bits).

## Repository layout

```
Quantum2626/
├── README.md
├── driver/                   # Linux ALSA PCI driver
│   ├── README.md
│   ├── Makefile
│   └── snd-quantum2626.c
├── driver-reference/         # Windows driver (INF, strings; .sys local)
│   ├── README.md             # What’s here and INF summary
│   ├── pae_quantum.inf       # Windows setup info (PCI IDs, service, KMDF)
│   └── strings_*.txt         # From windows_re_strings.ps1
├── docs/
│   ├── REVERSE_ENGINEERING_PLAN.md
│   ├── NO_SOUND_DEBUG.md
│   ├── DIAGNOSIS.md
│   ├── STAGE2_RUNBOOK.md
│   └── WINDOWS_PROFILING.md
├── notes/
│   ├── MMIO_BASELINE.md
│   ├── REGISTER_GUESSES.md
│   └── ...
└── scripts/
    ├── reload_quantum_driver.sh
    ├── capture_mmio_baseline.sh
    ├── windows_re_next_run.ps1
    └── windows_re_strings.ps1
```

## References

- [PreSonus Quantum 2626](https://www.presonus.com/products/quantum-2626)  
- [LinuxMusicians: Presonus Quantum Thunderbolt](https://linuxmusicians.com/viewtopic.php?t=19316) — “Linux supports Thunderbolt, but no one has written a Linux driver for a Thunderbolt audio interface (yet).”  
- [Kernel Thunderbolt docs](https://docs.kernel.org/admin-guide/thunderbolt.html)
