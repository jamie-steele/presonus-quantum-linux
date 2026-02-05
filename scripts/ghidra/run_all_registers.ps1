# Run comprehensive register analysis
param(
    [string]$GhidraPath = "$env:USERPROFILE\ghidra\ghidra_12.0.2_PUBLIC",
    [string]$DriverFile = ""
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Find driver file
if ([string]::IsNullOrEmpty($DriverFile)) {
    $desktopPath = "$env:USERPROFILE\Desktop\Quantum2626_DriverFiles\pae_quantum.sys"
    if (Test-Path $desktopPath) {
        $DriverFile = $desktopPath
    } else {
        $driverStore = "C:\Windows\System32\DriverStore\FileRepository"
        $dirs = Get-ChildItem $driverStore -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "pae_quantum*" }
        foreach ($d in $dirs) {
            $candidate = Join-Path $d.FullName "pae_quantum.sys"
            if (Test-Path $candidate) {
                $DriverFile = $candidate
                break
            }
        }
    }
}

if ([string]::IsNullOrEmpty($DriverFile) -or -not (Test-Path $DriverFile)) {
    Write-Host "ERROR: Driver file not found!" -ForegroundColor Red
    exit 1
}

$scriptPath = Join-Path $ScriptDir "find_all_registers.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: Script not found: $scriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "=== Running Comprehensive Register Analysis ===" -ForegroundColor Cyan
Write-Host "Driver: $DriverFile" -ForegroundColor Yellow
Write-Host "Script: $scriptPath" -ForegroundColor Yellow
Write-Host ""

$env:GHIDRA_INSTALL_DIR = $GhidraPath

Push-Location $ScriptDir

try {
    python -m pyghidra $DriverFile $scriptPath 2>&1 | ForEach-Object {
        if ($_ -notmatch "DeprecationWarning") {
            $_
        }
    }
} finally {
    Pop-Location
}

# Check for output
$outputFile = Join-Path $ScriptDir "all_registers.txt"
if (Test-Path $outputFile) {
    Write-Host ""
    Write-Host "SUCCESS: Report created: $outputFile" -ForegroundColor Green
    $lineCount = (Get-Content $outputFile | Measure-Object -Line).Lines
    Write-Host "  Lines: $lineCount" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "WARNING: Output file not found" -ForegroundColor Yellow
}
