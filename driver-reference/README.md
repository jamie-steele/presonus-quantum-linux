# Windows driver reference — Quantum 2626

Reference files from the PreSonus Windows driver for the Quantum 2626. Used for IDs, service names, and behavior when building or reverse-engineering a Linux driver. **Not for redistribution of the driver itself.**

## What’s here

| File | Description |
|------|-------------|
| **pae_quantum.inf** | Windows setup information: PCI IDs, service name, driver filename, KMDF version. |
| **README.txt** | Collection notes: device ID, driver version, next steps (strings, Ghidra, compare resources). |
| **resources.txt** | Device/resources dump from Windows. |
| **services.txt** | PreSonus Hardware Access Service (user-mode); kernel driver is `pae_quantum`. |

**Not in repo (keep locally only):** `pae_quantum.sys`, `pae_quantum.cat`, `pae_quantum.PNF` — binary/signed; use locally for reverse engineering if needed.

## From the INF (summary)

- **Quantum 2626:** `PCI\VEN_1C67&DEV_0104&SUBSYS_01041C67` — matches Linux `1c67:0104`.
- **Driver:** `pae_quantum.sys` (kernel), service name `pae_quantum`.
- **Class:** MEDIA; uses KS + WDMAUDIO. KMDF 1.19. DriverVer 01/31/2023, 1.37.0.0.
- **Other devices in same driver:** 0101 (Quantum), 0102 (Quantum 2), 0103 (4848), 0105 (Mobile).

Use this plus `notes/DIAGNOSIS_RESULT.md` and `docs/NEXT_DRIVER.md` for Linux driver work.
