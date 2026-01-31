# Quantum 2626 — Linux Integration

Getting the **PreSonus Quantum 2626** Thunderbolt 3 audio interface working on Linux.

## Device summary

- **Product:** PreSonus Quantum 2626  
- **Connection:** Thunderbolt 3 (no USB or PCIe card version)  
- **Audio:** 26×26 I/O, 24-bit/192 kHz, &lt;1 ms round-trip latency  
- **Official support:** macOS and Windows only (proprietary drivers)  
- **Linux status:** No vendor driver. Thunderbolt is supported by the kernel; the device would appear as PCIe over the Thunderbolt tunnel, but a device-specific audio driver does not exist (as of community reports).

## Path of least resistance

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

## Repository layout

```
Quantum2626/
├── README.md
├── docs/
│   ├── DIAGNOSIS.md           # Stage 1 diagnosis plan (Linux)
│   ├── STAGE2_RUNBOOK.md      # Stage 2 — Windows 11 runbook
│   └── WINDOWS_PROFILING.md   # Windows profiling reference
├── notes/
│   ├── baseline_lspci_nn.txt  # PCI baseline (1c67:0104)
│   ├── DIAGNOSIS_RESULT.md    # Stage 1 result
│   └── windows_profile.txt    # Fill in on Windows (Stage 2)
└── scripts/
    └── windows_capture_quantum.ps1   # Optional: run on Windows to capture device info
```

## References

- [PreSonus Quantum 2626](https://www.presonus.com/products/quantum-2626)  
- [LinuxMusicians: Presonus Quantum Thunderbolt](https://linuxmusicians.com/viewtopic.php?t=19316) — “Linux supports Thunderbolt, but no one has written a Linux driver for a Thunderbolt audio interface (yet).”  
- [Kernel Thunderbolt docs](https://docs.kernel.org/admin-guide/thunderbolt.html)
