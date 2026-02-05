# Run format and sample rate register analysis
# This script runs the find_format_registers.py analysis

param(
    [string]$GhidraPath = "$env:USERPROFILE\ghidra\ghidra_12.0.2_PUBLIC",
    [string]$DriverFile = "",
    [string]$ProjectPath = "$env:USERPROFILE\ghidra_projects",
    [string]$ProjectName = "Quantum2626_Analysis"
)

$ErrorActionPreference = "Continue"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Find driver file if not specified
if ([string]::IsNullOrEmpty($DriverFile)) {
    # Try Desktop first
    $desktopPath = "$env:USERPROFILE\Desktop\Quantum2626_DriverFiles\pae_quantum.sys"
    if (Test-Path $desktopPath) {
        $DriverFile = $desktopPath
        Write-Host "Using Desktop copy: $DriverFile" -ForegroundColor Green
    } else {
        # Try DriverStore
        $driverStore = "C:\Windows\System32\DriverStore\FileRepository"
        $dirs = Get-ChildItem $driverStore -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "pae_quantum*" }
        foreach ($d in $dirs) {
            $candidate = Join-Path $d.FullName "pae_quantum.sys"
            if (Test-Path $candidate) {
                $DriverFile = $candidate
                Write-Host "Using DriverStore copy: $DriverFile" -ForegroundColor Green
                break
            }
        }
    }
}

if ([string]::IsNullOrEmpty($DriverFile) -or -not (Test-Path $DriverFile)) {
    Write-Host "ERROR: Driver file not found!" -ForegroundColor Red
    Write-Host "Please specify -DriverFile or ensure driver is in Desktop\Quantum2626_DriverFiles\" -ForegroundColor Yellow
    exit 1
}

Write-Host "=== Running Format Register Analysis ===" -ForegroundColor Cyan
Write-Host "Ghidra: $GhidraPath" -ForegroundColor Yellow
Write-Host "Driver: $DriverFile" -ForegroundColor Yellow
Write-Host "Project: $ProjectPath\$ProjectName" -ForegroundColor Yellow
Write-Host ""

# Check Ghidra
$analyzeHeadless = Join-Path $GhidraPath "support\analyzeHeadless.bat"
if (-not (Test-Path $analyzeHeadless)) {
    Write-Host "ERROR: Ghidra not found at: $GhidraPath" -ForegroundColor Red
    exit 1
}

# Check if project exists
$projectFullPath = Join-Path $ProjectPath $ProjectName
if (-not (Test-Path $projectFullPath)) {
    Write-Host "=== Project not found, importing and analyzing binary ===" -ForegroundColor Yellow
    Write-Host "This may take several minutes..." -ForegroundColor Yellow
    
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
    Write-Host ""
}

# Run format register analysis script using PyGhidra
Write-Host "=== Running Format Register Analysis Script ===" -ForegroundColor Green

$scriptPath = Join-Path $ScriptDir "find_format_registers.py"
if (-not (Test-Path $scriptPath)) {
    Write-Host "ERROR: Script not found: $scriptPath" -ForegroundColor Red
    exit 1
}

# Set GHIDRA_INSTALL_DIR for PyGhidra
$env:GHIDRA_INSTALL_DIR = $GhidraPath

# Use PyGhidra CLI - simplest and most reliable approach
Write-Host "Running script using PyGhidra CLI..." -ForegroundColor Yellow
Write-Host "Binary: $DriverFile" -ForegroundColor Gray
Write-Host "Script: $scriptPath" -ForegroundColor Gray
Write-Host ""

# Change to script directory so output files are created there
Push-Location $ScriptDir

try {
    # PyGhidra CLI format: pyghidra <binary> <script>
    # It will automatically analyze the binary and run the script
    $output = python -m pyghidra $DriverFile $scriptPath 2>&1
    
    # Filter and display output
    $output | ForEach-Object {
        $line = if ($_ -is [string]) { $_.Trim() } else { $_.ToString().Trim() }
        # Filter out noise but keep important messages
        if ($line -and
            $line -notmatch "DeprecationWarning" -and 
            $line -notmatch "WARNING.*PDB" -and
            $line -notmatch "INFO.*Using log" -and
            $line -notmatch "INFO.*Loading user" -and
            $line -notmatch "INFO.*Searching for classes" -and
            $line -notmatch "INFO.*Class searcher" -and
            $line -notmatch "INFO.*Initializing" -and
            $line -notmatch "INFO.*HEADLESS" -and
            $line -notmatch "INFO.*Opening" -and
            $line -notmatch "INFO.*REPORT" -and
            $line -notmatch "INFO.*IMPORTING" -and
            $line -notmatch "INFO.*Using Loader" -and
            $line -notmatch "INFO.*Additional info" -and
            $line -notmatch "INFO.*Searching.*paths" -and
            $line -notmatch "INFO.*Loading file" -and
            $line -notmatch "INFO.*Using existing" -and
            $line -notmatch "INFO.*Applying" -and
            $line -notmatch "INFO.*Linking" -and
            $line -notmatch "------------------------------------------------" -and
            $line -ne "") {
            Write-Host $line
        }
    }
    
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        Write-Host ""
        Write-Host "WARNING: Script may have completed with warnings (exit code: $LASTEXITCODE)" -ForegroundColor Yellow
    }
} finally {
    Pop-Location
}

# Check for output file
$outputFile = Join-Path $ScriptDir "format_registers.txt"
if (Test-Path $outputFile) {
    Write-Host ""
    Write-Host "SUCCESS: Output file created: $outputFile" -ForegroundColor Green
    $lineCount = (Get-Content $outputFile | Measure-Object -Line).Lines
    Write-Host "  Lines in output: $lineCount" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "WARNING: Output file not found: $outputFile" -ForegroundColor Yellow
    Write-Host "  Script may have run but didn't create output file" -ForegroundColor Gray
}

Write-Host ""
Write-Host "=== Analysis Complete ===" -ForegroundColor Cyan
Write-Host "Check format_registers.json in: $ScriptDir" -ForegroundColor Yellow
