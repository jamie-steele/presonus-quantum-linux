# Windows - Collect all Quantum 2626 driver files and information
# Run this before rebooting to Linux
# Copies files to Desktop for easy access

$ErrorActionPreference = "Continue"
$desktop = [Environment]::GetFolderPath("Desktop")
$outputDir = Join-Path $desktop "Quantum2626_DriverFiles"

Write-Host "=== Collecting Quantum 2626 Driver Files ===" -ForegroundColor Cyan
Write-Host "Output directory: $outputDir" -ForegroundColor Green
Write-Host ""

# Create output directory
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
}

# 1. Copy driver binary
Write-Host "1. Copying driver binary..." -ForegroundColor Yellow
$driverPath = "C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\pae_quantum.sys"
if (Test-Path $driverPath) {
    Copy-Item $driverPath $outputDir -Force
    Write-Host "   Copied: pae_quantum.sys" -ForegroundColor Green
} else {
    Write-Host "   ERROR: Driver file not found!" -ForegroundColor Red
}

# 2. Copy INF file
Write-Host "2. Copying INF file..." -ForegroundColor Yellow
$infPath = "C:\WINDOWS\INF\oem73.inf"
if (Test-Path $infPath) {
    Copy-Item $infPath (Join-Path $outputDir "pae_quantum.inf") -Force
    Write-Host "   Copied: pae_quantum.inf" -ForegroundColor Green
} else {
    Write-Host "   ERROR: INF file not found!" -ForegroundColor Red
}

# 3. Copy all files from driver directory
Write-Host "3. Copying all driver directory files..." -ForegroundColor Yellow
$driverDir = "C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4"
if (Test-Path $driverDir) {
    $driverFiles = Get-ChildItem $driverDir
    foreach ($file in $driverFiles) {
        Copy-Item $file.FullName $outputDir -Force
        Write-Host "   Copied: $($file.Name)" -ForegroundColor Green
    }
} else {
    Write-Host "   ERROR: Driver directory not found!" -ForegroundColor Red
}

# 4. Get Resources information
Write-Host "4. Collecting device resources..." -ForegroundColor Yellow
$device = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "PreSonus Quantum 2626" -and
    $_.Class -match "MEDIA|Audio"
} | Select-Object -First 1

if ($device) {
    $instanceId = $device.InstanceId
    $resources = @()
    
    # Get all resource-related properties
    $props = Get-PnpDeviceProperty -InstanceId $instanceId | Where-Object {
        $_.KeyName -match "IRQ|Memory|Resource|Address|BAR"
    }
    
    $resources += "=== Device Resources ==="
    $resources += "InstanceId: $instanceId"
    $resources += ""
    
    foreach ($prop in $props) {
        $resources += "$($prop.KeyName): $($prop.Data)"
    }
    
    # Also try to get from registry
    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Enum\$($instanceId.Replace('\', '\'))"
    if (Test-Path $regPath) {
        $resources += ""
        $resources += "=== Registry Resources ==="
        try {
            $regProps = Get-ItemProperty -Path $regPath -ErrorAction SilentlyContinue
            if ($regProps) {
                $resources += "Device Parameters found in registry"
            }
        } catch {
            $resources += "Could not read registry: $($_.Exception.Message)"
        }
    }
    
    $resources | Out-File (Join-Path $outputDir "resources.txt") -Encoding UTF8
    Write-Host "   Saved: resources.txt" -ForegroundColor Green
} else {
    Write-Host "   ERROR: Device not found!" -ForegroundColor Red
}

# 5. Get service information
Write-Host "5. Collecting service information..." -ForegroundColor Yellow
$services = Get-Service | Where-Object { $_.DisplayName -match "Quantum|PreSonus" }
if ($services) {
    $services | Format-List * | Out-File (Join-Path $outputDir "services.txt") -Encoding UTF8
    Write-Host "   Saved: services.txt" -ForegroundColor Green
} else {
    Write-Host "   No PreSonus/Quantum services found" -ForegroundColor Yellow
}

# 6. Create a summary document
Write-Host "6. Creating summary document..." -ForegroundColor Yellow
$summary = @"
# Quantum 2626 Driver Files Collection
Date: $(Get-Date -Format 'yyyy-MM-dd HH:mm')
Windows Version: $([System.Environment]::OSVersion.VersionString)

## Files Collected
- pae_quantum.sys - Main driver binary (~200KB)
- pae_quantum.inf - Driver installation file
- All files from driver directory

## Device Information
Device ID: PCI\VEN_1C67&DEV_0104&SUBSYS_01041C67
Driver Version: 1.37.0.0

## Next Steps
1. Copy this entire folder to your Linux machine
2. Use the driver files for reverse engineering:
   - strings pae_quantum.sys > quantum_strings.txt
   - Use Ghidra/IDA Pro for disassembly
3. Compare resources.txt with Linux lspci -vv output

## File Locations (Windows)
Driver: C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\
INF: C:\WINDOWS\INF\oem73.inf
"@

$summary | Out-File (Join-Path $outputDir "README.txt") -Encoding UTF8
Write-Host "   Saved: README.txt" -ForegroundColor Green

Write-Host ""
Write-Host "=== Collection Complete ===" -ForegroundColor Green
Write-Host "Files saved to: $outputDir" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Copy the '$outputDir' folder to your Linux machine" -ForegroundColor Yellow
Write-Host "2. Or copy files to a USB drive/network share" -ForegroundColor Yellow
Write-Host "3. On Linux, analyze pae_quantum.sys with reverse engineering tools" -ForegroundColor Yellow
