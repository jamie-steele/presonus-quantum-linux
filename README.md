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

### Getting Started
| Resource | Description |
|----------|-------------|
| **Linux Testing** | [docs/LINUX_TESTING.md](docs/LINUX_TESTING.md) — Complete guide with quick start, testing procedures, and troubleshooting |
| **Driver Build/Load** | [driver/README.md](driver/README.md) — Makefile, insmod/modprobe, optional dump_on_trigger |

### Reverse Engineering
| Resource | Description |
|----------|-------------|
| **Reverse Engineering Plan** | [docs/REVERSE_ENGINEERING_PLAN.md](docs/REVERSE_ENGINEERING_PLAN.md) — Phases: gather artifacts (Windows strings, Linux MMIO), Ghidra analysis, driver changes |
| **Ghidra Analysis Guide** | [docs/GHIDRA_GUIDE.md](docs/GHIDRA_GUIDE.md) — Complete guide for analyzing the Windows driver with Ghidra |
| **Windows Profiling** | [docs/STAGE2_RUNBOOK.md](docs/STAGE2_RUNBOOK.md) — Capture device IDs and driver info from Windows 11 |
| **Windows Register Monitoring** | [docs/WINDOWS_REGISTER_MONITORING.md](docs/WINDOWS_REGISTER_MONITORING.md) — Monitor register access on Windows |

### Debugging and Reference
| Resource | Description |
|----------|-------------|
| **No Sound Debugging** | [docs/NO_SOUND_DEBUG.md](docs/NO_SOUND_DEBUG.md) — What we program, likely causes, dump-on-trigger, next RE steps |
| **Register Map** | [notes/REGISTER_GUESSES.md](notes/REGISTER_GUESSES.md) — Confirmed and suspected register offsets from Ghidra analysis |
| **Ghidra Findings** | [notes/GHIDRA_FINDINGS_SUMMARY.md](notes/GHIDRA_FINDINGS_SUMMARY.md) — Summary of reverse engineering findings |
| **MMIO Baseline** | [notes/MMIO_BASELINE.md](notes/MMIO_BASELINE.md) — BAR 0 register values at load |

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
   Use Windows only when you need to reverse-engineer the device (e.g. to write or adapt a Linux driver). On a Windows 11 machine with the Quantum 2626 working you can capture vendor/device IDs, driver names, and resource usage — see `docs/STAGE2_RUNBOOK.md`. We don’t need Windows for basic diagnosis; Linux already gives us the PCI identity (e.g. 1c67:0104).

3. **Use the profiling output for Linux**  
   - Match the same vendor/device ID on Linux (`lspci -nn`).
   - If the device is a standard PCIe audio design, existing ALSA drivers might be extended; if it’s custom, we need a minimal driver or reverse‑engineering.

- **Stage 1 (Linux):** [docs/DIAGNOSIS.md](docs/DIAGNOSIS.md) — diagnosis plan (done: device 1c67:0104 visible, no driver).
- **Stage 2 (Windows):** [docs/STAGE2_RUNBOOK.md](docs/STAGE2_RUNBOOK.md) — Profile on Windows 11, fill `notes/windows_profile.txt` for driver work.
- **Windows driver reference:** [driver-reference/](driver-reference/) — PreSonus Windows driver files (INF + notes) for IDs and reverse engineering; `.sys`/`.cat`/`.PNF` kept locally only.
- **Linux driver:** [driver/](driver/) — Out-of-tree ALSA PCI driver; card + PCM, Ghidra-derived register programming (buffer 0x10300/0x10304, control 0x100). Build: `make` in `driver/`; load: `sudo modprobe snd-quantum2626` (after `sudo make install`) or `sudo insmod snd-quantum2626.ko`. Real audio: more RE (buffer size, sample rate, control bits).

## Repository Layout

```
Quantum2626/
├── README.md                     # Main documentation
├── driver/                       # Linux ALSA PCI driver
│   ├── README.md
│   ├── Makefile
│   └── snd-quantum2626.c
├── driver-reference/             # Windows driver reference files
│   ├── README.md                 # INF summary and driver info
│   ├── pae_quantum.inf           # Windows setup info (PCI IDs, service, KMDF)
│   └── strings_*.txt             # Extracted strings from Windows driver
├── docs/                         # Documentation and guides
│   ├── LINUX_TESTING.md          # Linux testing and troubleshooting guide
│   ├── GHIDRA_GUIDE.md           # Ghidra reverse engineering guide
│   ├── REVERSE_ENGINEERING_PLAN.md # Overall RE strategy
│   ├── STAGE2_RUNBOOK.md         # Windows profiling guide
│   ├── WINDOWS_REGISTER_MONITORING.md # Windows register monitoring
│   ├── NO_SOUND_DEBUG.md         # Debugging guide
│   ├── DIAGNOSIS.md              # Initial diagnosis plan
│   └── _META/                    # Project metadata files
├── notes/                        # Development notes and findings
│   ├── REGISTER_GUESSES.md       # Register offset map (active)
│   ├── GHIDRA_FINDINGS_SUMMARY.md # Ghidra analysis summary
│   ├── DRIVER_IMPLEMENTATION.md  # Driver implementation notes
│   ├── analysis/                 # Analysis data and outputs
│   │   ├── register_data/        # Register capture data
│   │   ├── dmesg_logs/           # Linux kernel logs
│   │   └── ghidra_outputs/       # Ghidra script outputs
│   └── archive/                  # Historical session logs
├── scripts/                      # Development and testing scripts
│   ├── ghidra/                   # Ghidra analysis scripts
│   └── trace_analysis/           # Trace analysis scripts
└── samples/                      # Sample files and test data
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
