# Alternative trace capture with different profile
# Try IORegistry or custom profile for better MMIO visibility

param(
    [string]$OutputFile = "quantum_io_trace.etl",
    [int]$DurationSeconds = 10
)

$ErrorActionPreference = "Continue"

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Requires Administrator!" -ForegroundColor Red
    exit 1
}

Write-Host "=== Alternative Trace Capture ===" -ForegroundColor Cyan
Write-Host ""

# Try IORegistry profile (better for I/O operations)
$wprPath = "C:\Windows\System32\wpr.exe"

Write-Host "Trying IORegistry profile (better for I/O/MMIO)..." -ForegroundColor Yellow
& $wprPath -cancel 2>&1 | Out-Null

# Start IORegistry trace
Write-Host "Starting IORegistry trace..." -ForegroundColor Cyan
$start = & $wprPath -start IORegistry -filemode 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "IORegistry profile not available, trying custom providers..." -ForegroundColor Yellow
    
    # Try with specific providers
    $providers = @(
        "{9B79EE91-B5FD-41C0-A243-4248E266E9D0}",  # Microsoft-Windows-Kernel-File
        "{3D6FA8D4-FE05-11D0-9DDA-00C04FD7BA7C}",  # Microsoft-Windows-Kernel-Disk
        "{90CBDC39-4A3E-11D1-84F4-0000F80464E3}"   # Microsoft-Windows-Kernel-Memory
    )
    
    $providerArgs = $providers | ForEach-Object { "-p", $_ }
    $start = & $wprPath -start $providerArgs -filemode 2>&1
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Could not start trace" -ForegroundColor Red
    Write-Host $start -ForegroundColor Red
    exit 1
}

Write-Host "Trace started. Play audio on Quantum 2626 for $DurationSeconds seconds..." -ForegroundColor Green
Start-Sleep -Seconds $DurationSeconds

Write-Host "Stopping trace..." -ForegroundColor Cyan
$stop = & $wprPath -stop $OutputFile 2>&1

if ($LASTEXITCODE -eq 0 -and (Test-Path $OutputFile)) {
    $size = (Get-Item $OutputFile).Length / 1MB
    Write-Host ""
    Write-Host "Trace saved: $OutputFile" -ForegroundColor Green
    Write-Host "Size: $([math]::Round($size, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "ERROR: Trace save failed" -ForegroundColor Red
    Write-Host $stop -ForegroundColor Red
}
