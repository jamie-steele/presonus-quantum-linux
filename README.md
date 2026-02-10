# PreSonus Quantum 2626 Linux Driver

Community-developed **Linux ALSA driver** for the **PreSonus Quantum 2626** Thunderbolt 3 audio interface. This open-source driver enables professional audio production on Linux with this high-performance 26×26 I/O interface.

## Overview

Getting the **PreSonus Quantum 2626** Thunderbolt 3 audio interface working on Linux with an out-of-tree ALSA PCI driver. This project provides Linux support for professional audio recording, music production, and low-latency audio processing.

## Hardware Specifications

- **Product:** PreSonus Quantum 2626 Thunderbolt Audio Interface  
- **Connection:** Thunderbolt 3 (no USB or PCIe card version)  
- **Audio Capabilities:** 26 inputs × 26 outputs, 24-bit/192 kHz resolution, <1 ms round-trip latency  
- **Official Support:** macOS and Windows only (proprietary drivers)  
- **Linux Support:** Community-developed ALSA driver (PCI ID 1c67:0104)
- **Use Cases:** Professional audio recording, music production, live sound, DAW integration, low-latency audio processing

---

## Development Status

- **Driver Status:** ALSA card detection working, MSI interrupts operational, prepare/trigger functions implemented
- **Register Programming:** DMA buffer address configuration (0x10300 playback / 0x10304 capture), control registers (0x100)
- **Current Limitation:** Audio output not yet functional - requires additional reverse engineering of Windows driver
- **Next Steps:** Complete register mapping for buffer size, sample rate configuration, and audio routing

**Development Progress:** The driver successfully loads and creates an ALSA sound card. We're actively reverse-engineering the Windows driver using Ghidra to complete the register map for full audio functionality.

---

## Installation and Quick Start

### Building the Driver

```bash
# Navigate to driver directory
cd driver && make

# Install the kernel module
sudo make install

# Load the driver
sudo modprobe snd-quantum2626
```

### Testing Audio Playback

```bash
# Check if the Quantum 2626 is detected
cat /proc/asound/cards

# Stop audio services (required for testing)
systemctl --user stop wireplumber pipewire-pulse

# Test audio playback (adjust card number as needed)
aplay -D plughw:4,0 -r 48000 -f S16_LE -c 2 /usr/share/sounds/alsa/Front_Center.wav

# Restart audio services
systemctl --user start pipewire pipewire-pulse wireplumber
```

### Reloading After Changes

**Reload driver (after code changes):** Use `./scripts/reload_quantum_driver.sh` (stops audio, kills processes using card 4, rmmod/insmod, starts audio). If that still says "module in use", log out, switch to TTY2 (Ctrl+Alt+F2), run `sudo rmmod snd_quantum2626 && sudo insmod driver/snd-quantum2626.ko`, then switch back and log in.

---

## Documentation and Development Resources

| Resource | Description |
|----------|-------------|
| **Reverse-engineering plan** | [docs/REVERSE_ENGINEERING_PLAN.md](docs/REVERSE_ENGINEERING_PLAN.md) — Phases: gather artifacts (Windows strings, Linux MMIO), Ghidra analysis, driver changes. |
| **No sound debugging** | [docs/NO_SOUND_DEBUG.md](docs/NO_SOUND_DEBUG.md) — What we program, likely causes, dump-on-trigger, next RE steps. |
| **Driver build/load** | [driver/README.md](driver/README.md) — Makefile, insmod/modprobe, optional dump_on_trigger. |
| **Register guesses** | [notes/REGISTER_GUESSES.md](notes/REGISTER_GUESSES.md) — Offsets from Ghidra; update as you find more. |
| **MMIO baseline** | [notes/MMIO_BASELINE.md](notes/MMIO_BASELINE.md) — BAR 0 values at load. |

### Development Scripts

- `scripts/reload_quantum_driver.sh` — Linux: reload driver for development
- `scripts/capture_mmio_baseline.sh` — Linux: save MMIO register dumps from dmesg
- `scripts/windows_re_next_run.ps1` — Windows: strings extraction + Ghidra analysis checklist
- `scripts/windows_re_strings.ps1` — Windows: extract strings from driver binaries

---

## Reverse Engineering Workflow

### Current Development Focus (Windows + Ghidra Analysis)

1. **Ghidra Analysis:** Analyze `pae_quantum.sys` Windows driver to identify register mappings for:
   - Buffer size and period size configuration
   - Sample rate programming
   - Stream start/stop control sequences
   - Confirm existing offsets (0x100, 0x10300/0x10304)
   - Document new register discoveries in [notes/REGISTER_GUESSES.md](notes/REGISTER_GUESSES.md)

2. **Driver Implementation:** Update `QUANTUM_REG_*` constants and prepare/trigger functions in `driver/snd-quantum2626.c` with discovered register mappings

3. **Testing and Validation:** Reload driver, test with aplay, verify dmesg output and physical audio output

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

---

## Keywords

Linux audio driver, PreSonus Quantum 2626, Thunderbolt 3 audio interface, ALSA driver, professional audio Linux, reverse engineering audio hardware, out-of-tree kernel module, music production Linux, DAW Linux, low-latency audio, 192 kHz audio interface, 24-bit audio, Ghidra reverse engineering, PCI audio driver, Linux audio development, open source audio driver, Thunderbolt audio Linux

## Contributing

Contributions are welcome! This is a community-driven project. If you have a PreSonus Quantum 2626 and want to help with:
- Testing the driver on your Linux system
- Reverse engineering the Windows driver
- Improving documentation and guides
- Bug fixes and feature development
- Hardware testing and validation

Please feel free to open issues or submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
