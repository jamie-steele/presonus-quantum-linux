# Windows 11 - Capture PreSonus Quantum 2626 device info for Linux driver work.
# Run in PowerShell (no Administrator required for device listing).
# Usage: .\windows_capture_quantum.ps1
# Copy the output to notes/windows_capture.txt in the repo.

$ErrorActionPreference = "SilentlyContinue"

Write-Host "=== Quantum 2626 - Windows capture ===" -ForegroundColor Cyan
Write-Host "Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
Write-Host "OS: $([System.Environment]::OSVersion.VersionString)"
Write-Host ""

# Devices matching Quantum / PreSonus / Thunderbolt audio
$devices = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "Quantum|PreSonus|Thunderbolt" -and
    $_.Class -match "Audio|Media|Sound|System"
}

if (-not $devices) {
    Write-Host "No PnP device found matching Quantum|PreSonus|Thunderbolt. Try broader search:" -ForegroundColor Yellow
    Get-PnpDevice -Class AudioEndpoint, Media, SoundVideo | Format-Table Status, Class, FriendlyName -AutoSize
    exit 1
}

foreach ($d in $devices) {
    Write-Host "--- $($d.FriendlyName) ---" -ForegroundColor Green
    Write-Host "Status: $($d.Status)  Class: $($d.Class)"
    Write-Host "InstanceId: $($d.InstanceId)"
    $ids = (Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName DEVPKEY_Device_HardwareIds).Data
    if ($ids) { $ids | ForEach-Object { Write-Host "  HardwareId: $_" } }
    $driver = (Get-PnpDeviceProperty -InstanceId $d.InstanceId -KeyName DEVPKEY_Device_DriverDesc).Data
    if ($driver) { Write-Host "  Driver: $driver" }
    Write-Host ""
}

Write-Host "=== End of capture ===" -ForegroundColor Cyan
