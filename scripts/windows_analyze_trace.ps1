# Analyze WPR trace file - extract basic info without WPA
# This gives us a quick look at what's in the trace

param(
    [Parameter(Mandatory=$true)]
    [string]$TraceFile
)

$ErrorActionPreference = "Continue"

Write-Host "=== Analyzing WPR Trace File ===" -ForegroundColor Cyan
Write-Host "File: $TraceFile" -ForegroundColor Green
Write-Host ""

if (-not (Test-Path $TraceFile)) {
    Write-Host "ERROR: Trace file not found: $TraceFile" -ForegroundColor Red
    exit 1
}

$fileInfo = Get-Item $TraceFile
Write-Host "Size: $([math]::Round($fileInfo.Length / 1MB, 2)) MB" -ForegroundColor Cyan
Write-Host "Created: $($fileInfo.CreationTime)" -ForegroundColor Cyan
Write-Host ""

# Check if we can use tracerpt (built-in Windows tool)
$tracerptPath = "C:\Windows\System32\tracerpt.exe"
if (Test-Path $tracerptPath) {
    Write-Host "Using tracerpt to extract events..." -ForegroundColor Yellow
    
    $traceDir = Split-Path $TraceFile -Parent
    if ([string]::IsNullOrEmpty($traceDir)) {
        $traceDir = Get-Location
    }
    $outputDir = Join-Path $traceDir "trace_analysis"
    if (Test-Path $outputDir) {
        Remove-Item $outputDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $outputDir | Out-Null
    
    # Extract events to CSV
    Write-Host "Extracting events (this may take a moment)..." -ForegroundColor Cyan
    & $tracerptPath $TraceFile -o "$outputDir\events.csv" -of CSV 2>&1 | Out-Null
    
    if (Test-Path "$outputDir\events.csv") {
        Write-Host "Events extracted!" -ForegroundColor Green
        Write-Host ""
        
        # Try to find relevant events
        Write-Host "=== Searching for relevant events ===" -ForegroundColor Yellow
        
        # Look for I/O operations, driver activity
        $events = Import-Csv "$outputDir\events.csv" -ErrorAction SilentlyContinue
        
        if ($events) {
            Write-Host "Total events: $($events.Count)" -ForegroundColor Cyan
            
            # Filter for interesting events
            $ioEvents = $events | Where-Object { 
                $_.EventName -match "IO|Read|Write|Memory|MMIO|Driver" -or
                $_.TaskName -match "IO|Driver" -or
                $_.ProviderName -match "quantum|pae|audio"
            } | Select-Object -First 50
            
            if ($ioEvents) {
                Write-Host ""
                Write-Host "Found $($ioEvents.Count) potentially relevant events:" -ForegroundColor Green
                $ioEvents | Format-Table EventName, TaskName, ProviderName, TimeStamp -AutoSize | Out-String -Width 200
            } else {
                Write-Host "No obvious I/O events found in first scan" -ForegroundColor Yellow
            }
            
            # Look for pae_quantum driver
            $quantumEvents = $events | Where-Object {
                $_.ProviderName -match "quantum|pae" -or
                $_.TaskName -match "quantum|pae"
            }
            
            if ($quantumEvents) {
                Write-Host ""
                Write-Host "Found $($quantumEvents.Count) Quantum driver events!" -ForegroundColor Green
                $quantumEvents | Select-Object -First 20 | Format-Table EventName, TaskName, TimeStamp -AutoSize
            }
        }
        
        Write-Host ""
        Write-Host "Full events CSV: $outputDir\events.csv" -ForegroundColor Cyan
        Write-Host "You can open it in Excel or text editor to search for MMIO/I/O operations" -ForegroundColor Yellow
    } else {
        Write-Host "Could not extract events to CSV" -ForegroundColor Yellow
    }
    
    # Also try to get summary
    Write-Host ""
    Write-Host "=== Trace Summary ===" -ForegroundColor Yellow
    & $tracerptPath $TraceFile -summary "$outputDir\summary.txt" 2>&1 | Out-Null
    if (Test-Path "$outputDir\summary.txt") {
        Get-Content "$outputDir\summary.txt" | Select-Object -First 50
    }
} else {
    Write-Host "tracerpt.exe not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=== For Detailed Analysis ===" -ForegroundColor Yellow
Write-Host "Open the trace file in Windows Performance Analyzer (WPA):" -ForegroundColor White
Write-Host "  1. Search for 'wpa.exe' in Start menu" -ForegroundColor Gray
Write-Host "  2. File -> Open -> Select: $TraceFile" -ForegroundColor Gray
Write-Host "  3. Look for:" -ForegroundColor Gray
Write-Host "     - I/O operations" -ForegroundColor Gray
Write-Host "     - Driver activity (filter by 'pae_quantum')" -ForegroundColor Gray
Write-Host "     - Memory access patterns" -ForegroundColor Gray
Write-Host ""
