# Windows 11 Profiling — Quantum 2626 for Linux Integration

Use this **only when you need to reverse-engineer** the device (e.g. to write or adapt a Linux driver). Not for basic diagnosis: Linux already gives us the PCI identity (1c67:0104) via `lspci`. Use Windows profiling when you need driver behavior, resource usage, or protocol details for actual driver work.

---

## Prerequisites

- Windows 11 PC with Thunderbolt (Quantum 2626 working with PreSonus drivers).
- Quantum 2626 connected and recognized (e.g. in PreSonus Universal Control / Studio One).

---

## 1. Device identity (Vendor & Device ID)

### Method A: Device Manager (GUI)

1. **Win + X** → **Device Manager**.
2. Expand **Sound, video and game controllers** (and if needed **Other devices** or **Audio inputs and outputs**).
3. Find the PreSonus Quantum 2626 (or “Quantum” / “Thunderbolt audio”).
4. **Right‑click** → **Properties** → **Details** tab.
5. **Property:** choose **Hardware Ids**.
6. You should see lines like:
   - `PCI\VEN_xxxx&DEV_xxxx&SUBSYS_...`  
   or  
   - `USB\VID_xxxx&PID_xxxx...` (if it appears as USB over Thunderbolt).
7. **Record:**
   - **VEN_xxxx** = Vendor ID (4 hex digits).
   - **DEV_xxxx** = Device ID (4 hex digits).
   - **SUBSYS_...** = Subsystem vendor/device if present.

Example: `PCI\VEN_1234&DEV_5678` → Vendor `0x1234`, Device `0x5678` → on Linux this is `1234:5678` in `lspci -nn`.

### Method B: PowerShell

Run PowerShell **as Administrator**:

```powershell
# List PnP devices; look for PreSonus / Quantum / Audio
Get-PnpDevice -Class AudioEndpoint, Media, SoundVideo | Format-Table -Property Status, Class, FriendlyName, InstanceId -AutoSize

# Detailed info for a device (replace with your device's InstanceId from above)
Get-PnpDeviceProperty -InstanceId "<DeviceInstanceId>" -KeyName DEVPKEY_Device_HardwareIds
```

From **HardwareIds** you get the same `VEN_xxxx` and `DEV_xxxx` as above.

---

## 2. Driver and service names

In **Device Manager** → Quantum 2626 → **Properties** → **Driver** tab:

- **Driver Provider:** e.g. PreSonus.
- **Driver Date** / **Driver Version:** for reference.
- **Driver Details** → list of **.sys** and other files (e.g. `presonus_quantum.sys` or similar). Record the main driver filename.

Optional: in **Services** (Win + R → `services.msc`) look for any PreSonus/Quantum-related service names.

---

## 3. PCIe / Thunderbolt view (optional)

If the device appears as PCIe over Thunderbolt:

1. **Device Manager** → **View** → **Resources by type** (or use **View** → **Devices by connection** to see the Thunderbolt tree).
2. Or in PowerShell:
   ```powershell
   Get-PnpDevice | Where-Object { $_.FriendlyName -match "Quantum|PreSonus|Thunderbolt" } | Format-List *
   ```

This helps confirm it’s a PCIe device (same as you’d see in Linux `lspci` when Thunderbolt is working).

---

## 4. What to write down for Linux

Fill this and store it in the repo (e.g. `notes/windows_profile.txt`):

```text
# Quantum 2626 — Windows 11 profile

Date:
Windows version:

## Identity
Vendor ID (VEN):     0x____
Device ID (DEV):     0x____
Subsystem Vendor:    0x____  (if any)
Subsystem Device:    0x____  (if any)

## Driver
Driver provider:
Driver file(s):
Service name (if any):

## Notes
- PCI or USB in Hardware Ids?:
- Any other related devices (e.g. separate MIDI or control device):
```

On Linux you can then:

- Run `lspci -nn` and search for that vendor:device (e.g. `xxxx:yyyy`).
- Search kernel/ALSA source for that ID to see if a driver already exists or where to add a quirk.
- Use the driver/service names as a hint for protocol or chip family (e.g. if it matches a known PCIe audio chip).

---

## 5. Optional: resource usage (advanced)

If you later need to write a minimal driver, useful info from Windows:

- **Device Manager** → Quantum 2626 → **Properties** → **Resources** tab:  
  Note **IRQ** and **Memory range** (BARs). On Linux these appear in `lspci -vv` and `/proc/iomem`.

- **Driver Verifier** or **Windows Performance Recorder** is only needed for deep reverse engineering; skip unless you’re implementing a full driver from scratch.

---

## 6. After profiling

- Copy the filled `notes/windows_profile.txt` (or equivalent) into the repo.
- On Linux, run the Phase 1 steps in [DIAGNOSIS.md](DIAGNOSIS.md) again and compare:
  - Same vendor:device in `lspci -nn` as on Windows.
  - If yes: next step is to find or write an ALSA/kernel driver for that ID.
  - If Linux still doesn’t show the device: focus on Thunderbolt authorization, firmware, and cable/port on the Linux machine.

This keeps Windows profiling minimal and targeted: enough to identify the device and driver so we can integrate it on Linux without painstaking reverse engineering unless we choose to.
