# Quantum 2626 — Diagnosis Result (Phase 1)

**Date:** 2025-01-30  
**Kernel:** 6.17.9-76061709-generic  
**Thunderbolt modules:** `thunderbolt`, `intel_wmi_thunderbolt` loaded

---

## Summary

| Check | Result |
|-------|--------|
| Thunderbolt support | ✅ Kernel and modules present |
| Device visible on PCI | ✅ Yes — **09:00.0** |
| Vendor:Device ID | **1c67:0104** (PreSonus) |
| PCI class | 0401 — Multimedia audio controller |
| Kernel driver bound | ❌ **None** |
| ALSA sound card | ❌ No card for Quantum 2626 |

---

## Device details

- **Bus:** 09:00.0 (behind Thunderbolt chain: Titan Ridge → Alpine Ridge → device)
- **Vendor ID:** 0x1c67 (PreSonus Audio Electronics Inc.)
- **Device ID:** 0x0104
- **Subsystem:** 1c67:0104
- **Region 0:** Memory at 0x64000000, size 1 MiB (32-bit, non-prefetchable)
- **Kernel driver in use:** *(none)*
- **Kernel modules:** *(none)*

---

## Conclusion

- **Path of least resistance is confirmed:** Thunderbolt and PCI enumeration work. The Quantum 2626 is seen by the kernel as a PCIe device.
- **Gap:** No Linux driver claims this device. PreSonus provides no Linux driver; the kernel/ALSA tree has no driver for `1c67:0104`.

**Tried:** `new_id` with snd_hda_intel (two- and four-value form) — rejected with “Invalid argument” (driver likely does not accept dynamic IDs for vendor 1c67).

**Next steps:**

1. **Stage 2 (Windows)** — Profile on Windows 11 per `docs/STAGE2_RUNBOOK.md`; fill `notes/windows_profile.txt` (driver name, resources, IDs). Use that for reverse-engineering / driver work.
2. **Build our own driver** — Add support for 1c67:0104: either extend an existing PCI audio driver with this ID (if the chip is known) or write a minimal ALSA PCI driver that maps the device BAR and exposes an ALSA card. See `docs/NEXT_DRIVER.md`.
