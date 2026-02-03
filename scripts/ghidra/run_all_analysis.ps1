# Run all Ghidra analysis scripts in headless mode using PyGhidra (Windows)
# Usage: .\run_all_analysis.ps1

param(
    [string]$GhidraPath = "$env:USERPROFILE\Ghidra\ghidra_12.0.2_PUBLIC",
    [string]$DriverFile = "$env:USERPROFILE\Desktop\Quantum2626_DriverFiles\pae_quantum.sys"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Running Ghidra Analysis Scripts (PyGhidra) ===" -ForegroundColor Cyan
Write-Host "Ghidra: $GhidraPath" -ForegroundColor Yellow
Write-Host "Driver: $DriverFile" -ForegroundColor Yellow
Write-Host ""

# Set Ghidra path for PyGhidra
$env:GHIDRA_INSTALL_DIR = $GhidraPath

# Check if driver file exists
if (-not (Test-Path $DriverFile)) {
    Write-Host "ERROR: Driver file not found at: $DriverFile" -ForegroundColor Red
    Write-Host "Please set -DriverFile parameter or ensure file exists" -ForegroundColor Yellow
    exit 1
}

# Check if PyGhidra is available
try {
    $null = python -c "import pyghidra" 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "PyGhidra not found"
    }
} catch {
    Write-Host "ERROR: PyGhidra not installed. Install with: pip install pyghidra" -ForegroundColor Red
    exit 1
}

# Scripts to run
$scripts = @(
    "find_mmio_registers.py",
    "find_buffer_registers.py",
    "find_interrupt_registers.py"
)

foreach ($script in $scripts) {
    $scriptPath = Join-Path $ScriptDir $script
    if (-not (Test-Path $scriptPath)) {
        Write-Host "WARNING: Script not found: $scriptPath" -ForegroundColor Yellow
        continue
    }
    
    Write-Host "=== Running $script ===" -ForegroundColor Green
    Write-Host ""
    
    # Use pyghidra command to run script (without --skip-analysis to ensure analysis runs)
    python -m pyghidra $DriverFile $scriptPath
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Script failed: $script" -ForegroundColor Red
    } else {
        Write-Host "SUCCESS: $script completed" -ForegroundColor Green
    }
    Write-Host ""
}

Write-Host "=== Analysis Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Check the output above for register discoveries." -ForegroundColor Yellow
Write-Host "Results should be saved to JSON files in the script directory." -ForegroundColor Yellow
