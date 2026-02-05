# Capture with more detailed I/O profiling for MMIO access
# Uses IORegistry profile which may capture more low-level operations

param(
    [int]$DurationSeconds = 15
)

$ErrorActionPreference = "Continue"

Write-Host "=== Detailed MMIO Capture ===" -ForegroundColor Cyan
Write-Host "Using IORegistry profile for better MMIO visibility" -ForegroundColor Yellow
Write-Host ""

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script requires Administrator privileges!" -ForegroundColor Red
    exit 1
}

# Check for WPR
$wprPath = "C:\Windows\System32\wpr.exe"
if (-not (Test-Path $wprPath)) {
    Write-Host "ERROR: WPR not found!" -ForegroundColor Red
    exit 1
}

# Output file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outputFile = "quantum_mmio_$timestamp.etl"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$outputPath = Join-Path $scriptDir $outputFile

Write-Host "Duration: $DurationSeconds seconds" -ForegroundColor Yellow
Write-Host "Output: $outputPath" -ForegroundColor Yellow
Write-Host ""
Write-Host "Continue playing audio!" -ForegroundColor Cyan
Write-Host ""

# Stop any existing trace
& $wprPath -cancel 2>&1 | Out-Null
Start-Sleep -Milliseconds 500

# Try IORegistry profile (better for I/O operations)
Write-Host "Starting IORegistry trace..." -ForegroundColor Yellow
$result = & $wprPath -start IORegistry -filemode 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "IORegistry not available, trying GeneralProfile..." -ForegroundColor Yellow
    $result = & $wprPath -start GeneralProfile -filemode 2>&1
}

Start-Sleep -Milliseconds 1000

Write-Host "Trace started! Capturing..." -ForegroundColor Green
Write-Host ""

# Countdown
for ($i = $DurationSeconds; $i -gt 0; $i--) {
    Write-Host "  $i seconds remaining..." -ForegroundColor Yellow
    Start-Sleep -Seconds 1
}

Write-Host ""
Write-Host "Stopping trace..." -ForegroundColor Yellow

# Stop trace
$fullOutputPath = (Resolve-Path $scriptDir -ErrorAction SilentlyContinue).Path
if (-not $fullOutputPath) {
    $fullOutputPath = $scriptDir
}
$fullOutputPath = Join-Path $fullOutputPath $outputFile

$null = & $wprPath -stop $fullOutputPath 2>&1
Start-Sleep -Milliseconds 1000

Write-Host ""
if (Test-Path $fullOutputPath) {
    $fileSize = (Get-Item $fullOutputPath).Length / 1MB
    Write-Host "Capture complete! Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Green
    Write-Host "File: $fullOutputPath" -ForegroundColor Cyan
} else {
    Write-Host "WARNING: File not created" -ForegroundColor Red
}
