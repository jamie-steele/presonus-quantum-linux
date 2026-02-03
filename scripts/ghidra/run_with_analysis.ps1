# Run Ghidra analysis with proper analysis enabled
# This ensures the binary is fully analyzed before scripts run

param(
    [string]$GhidraPath = "$env:USERPROFILE\Ghidra\ghidra_12.0.2_PUBLIC",
    [string]$DriverFile = "$env:USERPROFILE\Desktop\Quantum2626_DriverFiles\pae_quantum.sys",
    [string]$ProjectPath = "$env:USERPROFILE\ghidra_projects",
    [string]$ProjectName = "Quantum2626_Analysis"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host "=== Running Ghidra with Full Analysis ===" -ForegroundColor Cyan
Write-Host "Ghidra: $GhidraPath" -ForegroundColor Yellow
Write-Host "Driver: $DriverFile" -ForegroundColor Yellow
Write-Host "Project: $ProjectPath\$ProjectName" -ForegroundColor Yellow
Write-Host ""

# Check paths
$analyzeHeadless = Join-Path $GhidraPath "support\analyzeHeadless.bat"
if (-not (Test-Path $analyzeHeadless)) {
    Write-Host "ERROR: Ghidra not found at: $GhidraPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $DriverFile)) {
    Write-Host "ERROR: Driver file not found: $DriverFile" -ForegroundColor Red
    exit 1
}

# Step 1: Import and analyze the binary (keep project for script execution)
Write-Host "=== Step 1: Importing and Analyzing Binary ===" -ForegroundColor Green
Write-Host "This may take several minutes..." -ForegroundColor Yellow

$programName = [System.IO.Path]::GetFileName($DriverFile)

# Check if project already exists
$projectFullPath = Join-Path $ProjectPath $ProjectName
if (Test-Path $projectFullPath) {
    Write-Host "Project already exists, skipping import..." -ForegroundColor Yellow
    Write-Host "If you need to re-analyze, delete the project first: $projectFullPath" -ForegroundColor Yellow
} else {
    & $analyzeHeadless `
        $ProjectPath `
        $ProjectName `
        -import $DriverFile `
        -processor x86:LE:64:default `
        -cspec gcc `
        -analysisTimeoutPerFile 600
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Analysis failed" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Analysis complete!" -ForegroundColor Green
}
Write-Host ""

# Step 2: Run scripts on the analyzed binary using analyzeHeadless (proper way)
Write-Host "=== Step 2: Running Analysis Scripts ===" -ForegroundColor Green

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
    
    Write-Host "=== Running $script ===" -ForegroundColor Cyan
    
    # Use pyghidra command-line tool
    # Note: This uses the deprecated run_script() internally, but it's the only
    # way to run Python 3 scripts with PyGhidra. The deprecation warning is
    # from PyGhidra's internal code, not ours.
    # To truly avoid warnings, we'd need to convert scripts to Jython and use
    # analyzeHeadless -postScript, but that's a bigger change.
    $env:GHIDRA_INSTALL_DIR = $GhidraPath
    
    # Run script on the analyzed binary
    python -m pyghidra $DriverFile $scriptPath 2>&1 | ForEach-Object {
        # Filter out the deprecation warning (it's from PyGhidra internals, not our code)
        if ($_ -notmatch "DeprecationWarning.*run_script\(\) is deprecated") {
            $_
        }
    }
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Script failed: $script" -ForegroundColor Red
    } else {
        Write-Host "SUCCESS: $script completed" -ForegroundColor Green
    }
    Write-Host ""
}

Write-Host "=== All Analysis Complete ===" -ForegroundColor Cyan
Write-Host "Check JSON files in: $ScriptDir" -ForegroundColor Yellow
