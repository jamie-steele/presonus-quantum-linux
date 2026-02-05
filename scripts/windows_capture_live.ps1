# Quick live capture while device is actively being used
param(
    [int]$DurationSeconds = 15
)

$ErrorActionPreference = "Continue"

Write-Host "=== LIVE CAPTURE - Quantum 2626 Active Use ===" -ForegroundColor Cyan
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Check for WPR
$wprPath = "C:\Windows\System32\wpr.exe"
if (-not (Test-Path $wprPath)) {
    Write-Host "ERROR: Windows Performance Recorder (WPR) not found!" -ForegroundColor Red
    exit 1
}

# Output file with timestamp
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = "quantum_live_$timestamp.etl"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputPath = Join-Path $scriptDir $outputFile

Write-Host "Starting capture NOW..." -ForegroundColor Green
Write-Host "Duration: $DurationSeconds seconds" -ForegroundColor Yellow
Write-Host "Output: $outputPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Continue playing audio during capture!" -ForegroundColor Cyan
Write-Host ""

# Stop any existing trace
& $wprPath -cancel 2>&1 | Out-Null
Start-Sleep -Milliseconds 500

# Start trace
Write-Host "Starting WPR trace..." -ForegroundColor Yellow
$null = & $wprPath -start GeneralProfile -filemode 2>&1
Start-Sleep -Milliseconds 1000

Write-Host "Trace started! Capturing for $DurationSeconds seconds..." -ForegroundColor Green
Write-Host ""

# Countdown
for ($i = $DurationSeconds; $i -gt 0; $i--) {
    Write-Host "  $i seconds remaining..." -ForegroundColor Yellow
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "Stopping trace..." -ForegroundColor Yellow

# Stop trace with full path
$fullOutputPath = (Resolve-Path $scriptDir -ErrorAction SilentlyContinue).Path
if (-not $fullOutputPath) {
    $fullOutputPath = $scriptDir
}
$fullOutputPath = Join-Path $fullOutputPath $outputFile

$null = & $wprPath -stop $fullOutputPath 2>&1
Start-Sleep -Milliseconds 1000

Write-Host ""
Write-Host "Capture complete!" -ForegroundColor Green
Write-Host "File: $outputPath" -ForegroundColor Cyan

# Check file
if (Test-Path $outputPath) {
    $fileSize = (Get-Item $outputPath).Length / 1MB
    Write-Host "Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Next: Analyze with WPA or run windows_analyze_trace.ps1" -ForegroundColor Yellow
} else {
    Write-Host "WARNING: Output file not found!" -ForegroundColor Red
    Write-Host "Check if WPR trace is still running: wpr -status" -ForegroundColor Yellow
}
