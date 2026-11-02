# Simple check - see what we can observe without admin rights
# This helps identify the device and driver before doing full tracing

$ErrorActionPreference = "Continue"

Write-Host "=== Simple Quantum 2626 Device Check ===" -ForegroundColor Cyan
Write-Host ""

# Find all Quantum devices
$devices = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "Quantum|PreSonus"
}

Write-Host "Found $($devices.Count) Quantum/PreSonus devices:" -ForegroundColor Green
Write-Host ""

foreach ($dev in $devices) {
    Write-Host "--- $($dev.FriendlyName) ---" -ForegroundColor Yellow
    Write-Host "  Class: $($dev.Class)"
    Write-Host "  Status: $($dev.Status)"
    Write-Host "  InstanceId: $($dev.InstanceId)"
    
    # Get driver info
    $instanceId = $dev.InstanceId
    try {
        $driverDesc = (Get-PnpDeviceProperty -InstanceId $instanceId -KeyName DEVPKEY_Device_DriverDesc -ErrorAction SilentlyContinue).Data
        $driverVersion = (Get-PnpDeviceProperty -InstanceId $instanceId -KeyName DEVPKEY_Device_DriverVersion -ErrorAction SilentlyContinue).Data
        $driverProvider = (Get-PnpDeviceProperty -InstanceId $instanceId -KeyName DEVPKEY_Device_DriverProvider -ErrorAction SilentlyContinue).Data
        
        if ($driverDesc) {
            Write-Host "  Driver: $driverDesc"
            Write-Host "  Version: $driverVersion"
            Write-Host "  Provider: $driverProvider"
        }
        
        # Get hardware IDs
        $hwIds = (Get-PnpDeviceProperty -InstanceId $instanceId -KeyName DEVPKEY_Device_HardwareIds -ErrorAction SilentlyContinue).Data
        if ($hwIds) {
            Write-Host "  Hardware IDs:"
            $hwIds | ForEach-Object { Write-Host "    $_" }
        }
    } catch {
        Write-Host "  (Could not get all properties)" -ForegroundColor Gray
    }
    Write-Host ""
}

# Check for driver service
Write-Host "=== Driver Services ===" -ForegroundColor Cyan
$services = Get-Service | Where-Object { $_.DisplayName -match "Quantum|PreSonus|PAE" }
if ($services) {
    foreach ($svc in $services) {
        Write-Host "$($svc.Name): $($svc.DisplayName) - $($svc.Status)" -ForegroundColor Green
    }
} else {
    Write-Host "No PreSonus/Quantum services found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "To capture MMIO activity, you need:" -ForegroundColor Yellow
Write-Host "1. Run PowerShell as Administrator" -ForegroundColor White
Write-Host "2. Run: .\windows_capture_register_activity.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Or use Windows Performance Recorder manually:" -ForegroundColor Yellow
Write-Host "  wpr -start GeneralProfile" -ForegroundColor White
Write-Host "  (play audio)" -ForegroundColor White
Write-Host "  wpr -stop quantum_trace.etl" -ForegroundColor White
