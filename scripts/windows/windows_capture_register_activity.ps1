# Windows - Capture register activity using ETW/WPR
# Monitors the working pae_quantum.sys driver to see what registers it accesses
# Run this while playing audio to capture MMIO patterns

param(
    [string]$OutputFile = "quantum_mmio_trace.etl",
    [int]$DurationSeconds = 10,
    [switch]$StartPlayback
)

$ErrorActionPreference = "Continue"

Write-Host "=== Quantum 2626 Register Activity Capture ===" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check if device exists
$device = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "PreSonus Quantum 2626" -and
    $_.Class -match "MEDIA|Audio"
} | Select-Object -First 1

if (-not $device) {
    Write-Host "ERROR: PreSonus Quantum 2626 not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Device: $($device.FriendlyName)" -ForegroundColor Green
Write-Host "Output: $OutputFile" -ForegroundColor Green
Write-Host "Duration: $DurationSeconds seconds" -ForegroundColor Green
Write-Host ""

# Check for WPR
$wprPath = "C:\Windows\System32\wpr.exe"
if (-not (Test-Path $wprPath)) {
    Write-Host "ERROR: Windows Performance Recorder (WPR) not found!" -ForegroundColor Red
    Write-Host "WPR should be at: $wprPath" -ForegroundColor Yellow
    exit 1
}

Write-Host "Starting ETW trace..." -ForegroundColor Yellow

# Stop any existing trace
& $wprPath -cancel 2>&1 | Out-Null

# Start trace with kernel profiling (includes driver I/O)
# GeneralProfile includes I/O operations
Write-Host "Starting WPR trace (this may take a moment)..." -ForegroundColor Cyan
$traceStart = & $wprPath -start GeneralProfile -filemode 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to start trace" -ForegroundColor Red
    Write-Host $traceStart -ForegroundColor Red
    exit 1
}

Write-Host "Trace started. Now:" -ForegroundColor Green
Write-Host "  1. Play audio on Quantum 2626 (or it will start automatically)" -ForegroundColor White
Write-Host "  2. Wait $DurationSeconds seconds" -ForegroundColor White
Write-Host ""

# Optionally start playback
if ($StartPlayback) {
    Write-Host "Starting test playback..." -ForegroundColor Cyan
    # Try to find a test audio file or use system sounds
    $testFile = "$env:SystemRoot\Media\Windows Notify.wav"
    if (Test-Path $testFile) {
        Start-Process -FilePath "powershell" -ArgumentList "-Command", "for(`$i=0; `$i -lt 5; `$i++) { (New-Object Media.SoundPlayer '$testFile').PlaySync(); Start-Sleep 1 }" -WindowStyle Hidden
    } else {
        Write-Host "  No test file found - please play audio manually" -ForegroundColor Yellow
    }
}

# Wait for duration
Write-Host "Capturing for $DurationSeconds seconds..." -ForegroundColor Cyan
Start-Sleep -Seconds $DurationSeconds

# Stop trace
Write-Host "Stopping trace..." -ForegroundColor Cyan
$traceStop = & $wprPath -stop $OutputFile 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to stop trace" -ForegroundColor Red
    Write-Host $traceStop -ForegroundColor Red
    exit 1
}

if (Test-Path $OutputFile) {
    $fileSize = (Get-Item $OutputFile).Length / 1MB
    Write-Host ""
    Write-Host "Trace saved: $OutputFile" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Open Windows Performance Analyzer (WPA)" -ForegroundColor White
    Write-Host "  2. File -> Open -> Select $OutputFile" -ForegroundColor White
    Write-Host "  3. Look for:" -ForegroundColor White
    Write-Host "     - I/O operations" -ForegroundColor Gray
    Write-Host "     - Driver activity (pae_quantum)" -ForegroundColor Gray
    Write-Host "     - Memory access patterns" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Or use: wpa.exe $OutputFile" -ForegroundColor Cyan
} else {
    Write-Host "ERROR: Trace file not created!" -ForegroundColor Red
    exit 1
}
