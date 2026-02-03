# Extract driver-specific activity from trace
# Focus on pae_quantum.sys and related processes

param(
    [Parameter(Mandatory=$true)]
    [string]$TraceFile
)

$ErrorActionPreference = "Continue"

Write-Host "=== Extracting Quantum Driver Activity ===" -ForegroundColor Cyan
Write-Host "Trace: $TraceFile" -ForegroundColor Green
Write-Host ""

$traceDir = Split-Path $TraceFile -Parent
if ([string]::IsNullOrEmpty($traceDir)) {
    $traceDir = Get-Location
}
$outputDir = Join-Path $traceDir "driver_activity"
if (Test-Path $outputDir) {
    Remove-Item $outputDir -Recurse -Force
}
New-Item -ItemType Directory -Path $outputDir | Out-Null

# Extract events CSV if not already done
$eventsCsv = Join-Path (Split-Path $TraceFile -Parent) "trace_analysis\events.csv"
if (-not (Test-Path $eventsCsv)) {
    Write-Host "Extracting events from trace..." -ForegroundColor Yellow
    $tracerptPath = "C:\Windows\System32\tracerpt.exe"
    & $tracerptPath $TraceFile -o "$outputDir\events.csv" -of CSV 2>&1 | Out-Null
    $eventsCsv = "$outputDir\events.csv"
}

if (-not (Test-Path $eventsCsv)) {
    Write-Host "ERROR: Could not extract events" -ForegroundColor Red
    exit 1
}

Write-Host "Searching for Quantum driver activity..." -ForegroundColor Cyan

# Search for driver file references
$driverRefs = Select-String -Path $eventsCsv -Pattern "pae_quantum" -CaseSensitive:$false
if ($driverRefs) {
    Write-Host "Found $($driverRefs.Count) references to pae_quantum.sys" -ForegroundColor Green
    $driverRefs | Select-Object -First 20 | ForEach-Object {
        Write-Host "  $($_.Line.Substring(0, [Math]::Min(150, $_.Line.Length)))" -ForegroundColor Gray
    }
    $driverRefs | Out-File "$outputDir\driver_references.txt"
} else {
    Write-Host "No direct pae_quantum.sys references found" -ForegroundColor Yellow
}

# Search for PreSonus Hardware Access Service
$serviceRefs = Select-String -Path $eventsCsv -Pattern "PreSonusHardwareAccessService|quantumdevice" -CaseSensitive:$false
if ($serviceRefs) {
    Write-Host ""
    Write-Host "Found $($serviceRefs.Count) references to PreSonus services" -ForegroundColor Green
    $serviceRefs | Select-Object -First 20 | ForEach-Object {
        Write-Host "  $($_.Line.Substring(0, [Math]::Min(150, $_.Line.Length)))" -ForegroundColor Gray
    }
    $serviceRefs | Out-File "$outputDir\service_references.txt"
}

# Look for I/O operations that might be MMIO
Write-Host ""
Write-Host "Searching for I/O operations..." -ForegroundColor Cyan
$ioOps = Select-String -Path $eventsCsv -Pattern "DiskIo|FileIo.*Read|FileIo.*Write" -CaseSensitive:$false
if ($ioOps) {
    Write-Host "Found $($ioOps.Count) I/O operations" -ForegroundColor Green
    $ioOps | Select-Object -First 30 | Out-File "$outputDir\io_operations.txt"
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Yellow
Write-Host "Results saved to: $outputDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Note: GeneralProfile may not capture MMIO directly." -ForegroundColor Yellow
Write-Host "For MMIO access, you may need:" -ForegroundColor Yellow
Write-Host "  1. Windows Performance Analyzer (WPA) - Open the .etl file" -ForegroundColor White
Write-Host "  2. More specific trace profile (I/O, Memory)" -ForegroundColor White
Write-Host "  3. WinDbg with MMIO breakpoints" -ForegroundColor White
Write-Host ""
