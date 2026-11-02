# Windows - Monitor MMIO register access from working pae_quantum.sys driver
# This script helps capture what registers the Windows driver accesses
# Run while audio is playing/capturing to see register activity

$ErrorActionPreference = "Continue"

Write-Host "=== Windows MMIO Monitoring for Quantum 2626 ===" -ForegroundColor Cyan
Write-Host "This will help capture register access patterns from the working driver" -ForegroundColor Yellow
Write-Host ""

# Check if device is present
$device = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "PreSonus Quantum 2626" -and
    $_.Class -match "MEDIA|Audio"
} | Select-Object -First 1

if (-not $device) {
    Write-Host "ERROR: PreSonus Quantum 2626 not found!" -ForegroundColor Red
    Write-Host "Make sure the device is connected and driver is loaded." -ForegroundColor Yellow
    exit 1
}

Write-Host "Device found: $($device.FriendlyName)" -ForegroundColor Green
$instanceId = $device.InstanceId
Write-Host "InstanceId: $instanceId" -ForegroundColor Green
Write-Host ""

# Get driver info
$driverDesc = (Get-PnpDeviceProperty -InstanceId $instanceId -KeyName DEVPKEY_Device_DriverDesc).Data
Write-Host "Driver: $driverDesc" -ForegroundColor Green
Write-Host ""

Write-Host "=== Monitoring Options ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "To monitor MMIO access, you need one of these tools:" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Windows Performance Recorder (WPR) - Built-in Windows tool" -ForegroundColor White
Write-Host "   - Can trace kernel driver activity" -ForegroundColor Gray
Write-Host "   - Requires admin rights" -ForegroundColor Gray
Write-Host ""
Write-Host "2. WinDbg (Windows Debugger) - Advanced kernel debugging" -ForegroundColor White
Write-Host "   - Can set breakpoints on MMIO access" -ForegroundColor Gray
Write-Host "   - Requires kernel debugging setup" -ForegroundColor Gray
Write-Host ""
Write-Host "3. Custom kernel driver - Monitor MMIO via filter driver" -ForegroundColor White
Write-Host "   - Most direct approach" -ForegroundColor Gray
Write-Host "   - Requires driver development" -ForegroundColor Gray
Write-Host ""
Write-Host "4. ETW (Event Tracing for Windows) - System-level tracing" -ForegroundColor White
Write-Host "   - Can trace driver I/O operations" -ForegroundColor Gray
Write-Host "   - Requires ETW provider support" -ForegroundColor Gray
Write-Host ""

# Check for WPR
$wprPath = "C:\Windows\System32\wpr.exe"
if (Test-Path $wprPath) {
    Write-Host "Windows Performance Recorder (WPR) is available" -ForegroundColor Green
    Write-Host "  Path: $wprPath" -ForegroundColor Gray
    Write-Host ""
    Write-Host "To use WPR to trace driver activity:" -ForegroundColor Cyan
    Write-Host "  1. Run as Administrator" -ForegroundColor White
    Write-Host "  2. Start trace: wpr -start GeneralProfile" -ForegroundColor White
    Write-Host "  3. Play audio on Quantum 2626" -ForegroundColor White
    Write-Host "  4. Stop trace: wpr -stop trace.etl" -ForegroundColor White
    Write-Host "  5. Analyze with Windows Performance Analyzer (WPA)" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host "WPR not found at standard location" -ForegroundColor Yellow
}

# Alternative: Use Process Monitor to see driver file activity
Write-Host "=== Alternative: Monitor Driver File Activity ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Process Monitor (ProcMon) can show:" -ForegroundColor Cyan
Write-Host "  - Driver file access patterns" -ForegroundColor Gray
Write-Host "  - Registry access (may contain register values)" -ForegroundColor Gray
Write-Host "  - I/O operations" -ForegroundColor Gray
Write-Host ""
Write-Host "Download: https://docs.microsoft.com/sysinternals/downloads/procmon" -ForegroundColor White
Write-Host ""

# Check driver service
$service = Get-Service | Where-Object { $_.Name -match "quantum|pae" }
if ($service) {
    Write-Host "Driver service found: $($service.Name)" -ForegroundColor Green
    Write-Host "  Status: $($service.Status)" -ForegroundColor Gray
    Write-Host "  DisplayName: $($service.DisplayName)" -ForegroundColor Gray
    Write-Host ""
}

# Get device resources (memory ranges)
Write-Host "=== Device Resources ===" -ForegroundColor Yellow
$resources = Get-PnpDeviceProperty -InstanceId $instanceId | Where-Object {
    $_.KeyName -match "Memory|Resource|Address"
}
if ($resources) {
    foreach ($res in $resources) {
        Write-Host "$($res.KeyName): $($res.Data)" -ForegroundColor Cyan
    }
} else {
    Write-Host "No resource properties found via PnP" -ForegroundColor Yellow
    Write-Host "Check Device Manager -> Properties -> Resources tab manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "1. Use WPR or WinDbg to trace MMIO access during playback" -ForegroundColor White
Write-Host "2. Capture register read/write patterns" -ForegroundColor White
Write-Host "3. Compare baseline (idle) vs active (playback/capture)" -ForegroundColor White
Write-Host "4. Document register offsets and their functions" -ForegroundColor White
Write-Host ""
Write-Host "See docs/CLI_FEEDBACK_LOOP.md for more details" -ForegroundColor Cyan
