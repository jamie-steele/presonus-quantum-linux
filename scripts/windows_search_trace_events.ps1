# Search trace events CSV for driver-specific activity
# Helps find MMIO register access patterns

param(
    [string]$EventsFile = "trace_analysis\events.csv",
    [string]$SearchPattern = "",
    [int]$MaxResults = 50
)

$ErrorActionPreference = "Continue"

Write-Host "=== Searching Trace Events ===" -ForegroundColor Cyan
Write-Host ""

# Find events file
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$eventsPath = Join-Path $scriptDir $EventsFile

if (-not (Test-Path $eventsPath)) {
    Write-Host "ERROR: Events file not found: $eventsPath" -ForegroundColor Red
    Write-Host "Run windows_analyze_trace.ps1 first to extract events" -ForegroundColor Yellow
    exit 1
}

Write-Host "Events file: $eventsPath" -ForegroundColor Green
$fileSize = (Get-Item $eventsPath).Length / 1MB
Write-Host "Size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Gray
Write-Host ""

# Default search patterns if none provided
if ([string]::IsNullOrEmpty($SearchPattern)) {
    Write-Host "Searching for driver-related events..." -ForegroundColor Yellow
    Write-Host ""
    
    # Search patterns
    $patterns = @{
        "Driver Name" = "pae_quantum"
        "MMIO Mapping" = "MmMapIoSpace"
        "Register Read" = "READ_REGISTER"
        "Register Write" = "WRITE_REGISTER"
        "I/O Operations" = "IoRead|IoWrite|MmRead|MmWrite"
        "Memory Operations" = "MmMapIoSpace|MmUnmapIoSpace"
        "Interrupt" = "IoConnectInterrupt|Interrupt"
        "DMA" = "AllocateCommonBuffer|MapTransfer"
    }
    
    $allResults = @{}
    
    foreach ($name in $patterns.Keys) {
        $pattern = $patterns[$name]
        Write-Host "Searching for: $name ($pattern)" -ForegroundColor Cyan
        
        $results = Select-String -Path $eventsPath -Pattern $pattern -CaseSensitive:$false | Select-Object -First $MaxResults
        
        if ($results) {
            $count = (Select-String -Path $eventsPath -Pattern $pattern -CaseSensitive:$false).Count
            Write-Host "  Found: $count matches (showing first $([Math]::Min($MaxResults, $count)))" -ForegroundColor Green
            
            $allResults[$name] = $results
            
            # Show first few examples
            foreach ($result in $results | Select-Object -First 5) {
                $line = $result.Line
                # Truncate long lines
                if ($line.Length -gt 150) {
                    $line = $line.Substring(0, 147) + "..."
                }
                Write-Host "    $line" -ForegroundColor Gray
            }
            if ($results.Count -gt 5) {
                Write-Host "    ... and $($results.Count - 5) more" -ForegroundColor DarkGray
            }
        } else {
            Write-Host "  No matches" -ForegroundColor Yellow
        }
        Write-Host ""
    }
    
    # Summary
    Write-Host "=== Summary ===" -ForegroundColor Yellow
    foreach ($name in $allResults.Keys) {
        $count = (Select-String -Path $eventsPath -Pattern $patterns[$name] -CaseSensitive:$false).Count
        Write-Host "  $name : $count matches" -ForegroundColor White
    }
    
    # Save detailed results
    $outputFile = Join-Path $scriptDir "trace_analysis\driver_events.txt"
    Write-Host ""
    Write-Host "Saving detailed results to: $outputFile" -ForegroundColor Cyan
    
    $output = @()
    $output += "=== Driver Event Search Results ==="
    $output += "File: $eventsPath"
    $output += "Date: $(Get-Date)"
    $output += ""
    
    foreach ($name in $allResults.Keys) {
        $pattern = $patterns[$name]
        $count = (Select-String -Path $eventsPath -Pattern $pattern -CaseSensitive:$false).Count
        $output += "=== $name ($pattern) ==="
        $output += "Total matches: $count"
        $output += ""
        
        foreach ($result in $allResults[$name]) {
            $output += $result.Line
        }
        $output += ""
    }
    
    $output | Out-File -FilePath $outputFile -Encoding UTF8
    Write-Host "Results saved!" -ForegroundColor Green
    
} else {
    # Custom search
    Write-Host "Searching for: $SearchPattern" -ForegroundColor Yellow
    Write-Host ""
    
    $results = Select-String -Path $eventsPath -Pattern $SearchPattern -CaseSensitive:$false | Select-Object -First $MaxResults
    
    if ($results) {
        $count = (Select-String -Path $eventsPath -Pattern $SearchPattern -CaseSensitive:$false).Count
        Write-Host "Found: $count matches (showing first $([Math]::Min($MaxResults, $count)))" -ForegroundColor Green
        Write-Host ""
        
        foreach ($result in $results) {
            Write-Host $result.Line -ForegroundColor White
        }
    } else {
        Write-Host "No matches found" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
