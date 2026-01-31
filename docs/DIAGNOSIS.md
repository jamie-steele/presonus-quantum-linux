# Diagnosis Plan — Quantum 2626 on Linux

Diagnose first on Linux (path of least resistance), then profile on Windows 11 only if needed.

---

## Phase 1: Linux (do this first)

### 1.1 Thunderbolt and kernel

- **Thunderbolt authorized?**  
  On many distros you must authorize Thunderbolt devices (BIOS/UEFI or OS prompt). Ensure the Quantum 2626 is authorized so the kernel can see it.

- **Kernel and modules:**
  ```bash
  uname -r
  lsmod | grep -E 'thunderbolt|thunderbolt_net'
  ```
  If no Thunderbolt modules, enable in kernel config: `CONFIG_THUNDERBOLT`, and optionally `CONFIG_THUNDERBOLT_NET`.

### 1.2 Plug in the Quantum 2626 and capture

Run with the device **unplugged**, then **plug in** (after authorizing if prompted), then run:

```bash
# PCI devices (Thunderbolt devices often show as PCIe)
lspci -nnvv > notes/lspci_after_plug.txt

# Kernel messages (look for Thunderbolt, PCI, ALSA, snd)
dmesg | tail -100 > notes/dmesg_after_plug.txt

# ALSA playback / capture devices
aplay -l   > notes/aplay_l.txt
arecord -l > notes/arecord_l.txt

# Optional: list all sound cards
cat /proc/asound/cards >> notes/alsa_cards.txt
```

Save everything under `notes/` (create the folder if needed).

### 1.3 Interpret Phase 1

| What you see | Meaning | Next step |
|--------------|--------|-----------|
| New PCI device in `lspci` (with vendor/device ID) | Thunderbolt tunnel works; device is visible as PCIe | Record the **vendor:device** ID; go to Phase 2 only if you need driver hints from Windows. |
| No new PCI device | Thunderbolt not authorized, bad cable/port, or firmware | Fix Thunderbolt auth/cable/port; retry. If still nothing, profile on Windows to confirm device identity. |
| PCI device present but no ALSA card | Expected: no Linux driver for this interface | Use Windows profiling to get exact IDs and device class; plan minimal driver or ALSA extension. |
| ALSA card appears | Device may be class-compliant or already supported | Document which driver (e.g. `snd_xxx`) and card name; minimal work. |

**Path of least resistance:** If `lspci` shows the device with a clear vendor:device ID, you already have what you need to search for existing drivers or plan a new one. Windows profiling is only needed if Linux shows nothing or you want to confirm driver behavior/resource usage.

---

## Phase 2: Windows 11 (only for reverse-engineering)

Use **only when you need to reverse-engineer** the device for driver work (e.g. capture driver behavior, resource usage, or protocol details). Not needed for basic diagnosis — Linux already gives us the PCI ID (1c67:0104). If Linux never shows the device, fix Thunderbolt/auth first; use Windows to confirm identity only if that’s still unclear.

See **[WINDOWS_PROFILING.md](WINDOWS_PROFILING.md)** for the exact steps (Device Manager, PowerShell, optional tools).

---

## Phase 3: Use the results on Linux

- **Vendor:Device ID** from either Linux `lspci -nn` or Windows (e.g. Device Manager → Properties → Details → Hardware Ids) lets you:
  - Search the kernel/ALSA tree for that ID.
  - Add a quirk or new entry in an existing driver.
  - Plan a minimal kernel or userspace driver.

- **Notes:** Keep `notes/` updated with:
  - `lspci -nnvv` (and `dmesg`) from Linux.
  - Vendor/Device ID and driver name from Windows.
  - Any links to datasheets or reverse-engineering notes.

Once you have the IDs and (if needed) Windows profiling output, we can decide whether to extend an existing ALSA driver or outline a minimal driver approach.
