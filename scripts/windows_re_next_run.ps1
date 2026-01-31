# Windows "next run" for reverse-engineering: find driver, extract strings, copy hints.
# Run in PowerShell on a Windows machine with the Quantum 2626 driver installed.

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir

Write-Host "=== Quantum 2626 RE - Windows next run ===" -ForegroundColor Cyan
Write-Host ""

# 1. Run string extraction
& (Join-Path $scriptDir "windows_re_strings.ps1")
if ($LASTEXITCODE -ne 0 -and $null -ne $LASTEXITCODE) { exit $LASTEXITCODE }
Write-Host ""

# 2. Find driver path again for copy hint
$driverStore = "C:\Windows\System32\DriverStore\FileRepository"
$driverPath = $null
foreach ($d in (Get-ChildItem $driverStore -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "pae_quantum*" })) {
    $c = Join-Path $d.FullName "pae_quantum.sys"
    if (Test-Path $c) { $driverPath = $c; break }
}
if (-not $driverPath) {
    $driverPath = "C:\Windows\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\pae_quantum.sys"
    if (-not (Test-Path $driverPath)) { $driverPath = "pae_quantum.sys (search DriverStore)" }
}

Write-Host "=== Next steps ===" -ForegroundColor Cyan
Write-Host "1. Copy to repo (from this machine or later):" -ForegroundColor Yellow
Write-Host "   - driver-reference/strings_pae_quantum.txt (already created by script)"
Write-Host "   - driver-reference/strings_interesting.txt"
Write-Host "   - Optional: $driverPath  ->  driver-reference/pae_quantum.sys"
Write-Host ""
Write-Host "2. On Linux: run scripts/capture_mmio_baseline.sh after loading the driver." -ForegroundColor Yellow
Write-Host ""
Write-Host "3. Ghidra (or IDA):" -ForegroundColor Yellow
Write-Host "   - Load pae_quantum.sys (PE, x64 kernel driver)"
Write-Host "   - Search strings for: buffer, register, offset, 0x, BAR, control, status"
Write-Host "   - Find MMIO base (MmMapIoSpace / mapping) and all (base+offset) read/write"
Write-Host "   - Note offsets that match our baseline: 0x04=0x01030060, 0x08=0x10"
Write-Host "   - Document in notes/REGISTER_GUESSES.md"
Write-Host ""
Write-Host "4. See docs/REVERSE_ENGINEERING_PLAN.md for full phases." -ForegroundColor Yellow
