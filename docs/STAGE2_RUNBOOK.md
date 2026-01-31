# Stage 2 — Windows 11 Profiling Runbook

Run this on a **Windows 11** machine where the Quantum 2626 is connected and working (PreSonus drivers installed). Goal: capture device identity, driver names, and resource usage for reverse-engineering / Linux driver work.

**Linux already gave us:** PCI ID **1c67:0104** (PreSonus). On Windows we confirm the same ID and capture driver details.

---

## Checklist

- [ ] Quantum 2626 connected via Thunderbolt and recognized in Windows (e.g. PreSonus Universal Control shows it).
- [ ] Device Manager and/or PowerShell run (steps below).
- [ ] `notes/windows_profile.txt` filled and saved (template in repo).

---

## Step 1: Device identity (Hardware IDs)

### Option A — Device Manager

1. **Win + X** → **Device Manager**.
2. Expand **Sound, video and game controllers** (and **Audio inputs and outputs** if present).
3. Find **PreSonus Quantum 2626** (or “Quantum” / “Thunderbolt audio”).
4. Right‑click → **Properties** → **Details** tab.
5. **Property:** **Hardware Ids**.
6. Note the first line, e.g. `PCI\VEN_1C67&DEV_0104&SUBSYS_...`  
   - **VEN_** = Vendor ID (expect **1C67** = PreSonus).  
   - **DEV_** = Device ID (expect **0104**).  
   - **SUBSYS_** = Subsystem vendor & device (optional).

### Option B — PowerShell (dump all relevant devices)

Open **PowerShell** (no need for Administrator for this):

```powershell
Get-PnpDevice | Where-Object { $_.FriendlyName -match "Quantum|PreSonus|Thunderbolt" } | ForEach-Object {
  $id = $_.InstanceId
  Write-Host "--- $($_.FriendlyName) ---"
  Write-Host "InstanceId: $id"
  Get-PnpDeviceProperty -InstanceId $id -KeyName DEVPKEY_Device_HardwareIds 2>$null | Select-Object -ExpandProperty Data
  Write-Host ""
}
```

Copy the output into `notes/windows_profile.txt` or the “PowerShell output” section of the template.

---

## Step 2: Driver info

In **Device Manager** → Quantum 2626 → **Properties** → **Driver** tab:

- **Driver Provider:** _______________
- **Driver Date / Version:** _______________
- **Driver Details** → note the **.sys** filename(s): _______________

Optional: **Win + R** → `services.msc` → look for PreSonus/Quantum service names.

---

## Step 3: Resources (for driver work)

In **Device Manager** → Quantum 2626 → **Properties** → **Resources** tab:

- **Resource type:** Interrupt Request (IRQ), Memory Range.
- Note the values (or “Conflict” if shown): _______________

On Linux we already have: **Region 0** = Memory at 0x64000000, size 1 MiB. Compare with Windows memory range.

---

## Step 4: Fill and save the profile

1. Open `notes/windows_profile.txt` in this repo (or copy the template from the end of this runbook).
2. Fill every field you can from Steps 1–3.
3. Save the file in the repo so we can use it for driver work.

---

## Step 5: (Optional) Run the capture script

In the repo there is **scripts/windows_capture_quantum.ps1**. On Windows:

1. Copy it to your Windows machine (or clone the repo).
2. In PowerShell: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` (if scripts are blocked).
3. Run: `.\windows_capture_quantum.ps1`
4. Copy the generated output into `notes/` (e.g. `notes/windows_capture.txt`).

---

## Template: `notes/windows_profile.txt`

Copy this into `notes/windows_profile.txt` and fill it in:

```text
# Quantum 2626 — Windows 11 profile (Stage 2)

Date:
Windows version: (e.g. Win 11 23H2)

## Identity (from Hardware Ids)
Vendor ID (VEN):     0x____   (expect 0x1c67)
Device ID (DEV):     0x____   (expect 0x0104)
Subsystem Vendor:    0x____   (if any)
Subsystem Device:    0x____   (if any)
PCI or USB in Hardware Ids?:   PCI / USB

## Driver
Driver provider:
Driver version/date:
Driver file(s) (.sys):

## Resources (from Properties → Resources)
IRQ:
Memory range(s):

## PowerShell output (optional paste)
(paste Get-PnpDevice / HardwareIds output here)

## Notes
(any other devices under Thunderbolt, MIDI device name, etc.)
```

---

After Stage 2, we use this profile to compare with Linux (1c67:0104), search kernel/ALSA for the same ID, and plan driver work or reverse-engineering steps.
