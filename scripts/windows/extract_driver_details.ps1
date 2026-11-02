# Extract details from pae_quantum.sys driver files

$drivers = @(
    "C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\pae_quantum.sys",
    "C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_60e367fe3befdd09\pae_quantum.sys"
)

foreach ($driverPath in $drivers) {
    if (Test-Path $driverPath) {
        Write-Host "=== $driverPath ===" -ForegroundColor Green
        $file = Get-Item $driverPath
        Write-Host "Size: $($file.Length) bytes ($([math]::Round($file.Length/1KB, 2)) KB)"
        Write-Host "Modified: $($file.LastWriteTime)"
        
        $versionInfo = $file.VersionInfo
        Write-Host "File Version: $($versionInfo.FileVersion)"
        Write-Host "Product: $($versionInfo.ProductName)"
        Write-Host "Company: $($versionInfo.CompanyName)"
        Write-Host "Description: $($versionInfo.FileDescription)"
        Write-Host ""
        
        # Extract strings
        Write-Host "Extracting interesting strings..." -ForegroundColor Cyan
        $bytes = [System.IO.File]::ReadAllBytes($driverPath)
        $strings = @()
        $currentString = ""
        
        foreach ($byte in $bytes) {
            if ($byte -ge 32 -and $byte -le 126) {
                $currentString += [char]$byte
            } else {
                if ($currentString.Length -ge 4) {
                    $strings += $currentString
                }
                $currentString = ""
            }
        }
        
        # Filter interesting strings
        $interesting = $strings | Where-Object {
            $_ -match "^(PCI|USB|REG|IO|MEM|IRQ|DMA|BAR|QUANTUM|PRESONUS|1C67|0104|AUDIO|PCM|STREAM|BUFFER|CONTROL|REGISTER)" -or
            $_ -match "^[A-Z_]{4,}$" -or
            $_ -match "^[a-z][A-Z][a-zA-Z]+$" -or
            $_ -match "0x[0-9A-Fa-f]+"
        } | Select-Object -First 150 -Unique
        
        Write-Host "Found $($interesting.Count) interesting strings:" -ForegroundColor Cyan
        $interesting | ForEach-Object { Write-Host "  $_" }
        Write-Host ""
        Write-Host "---" -ForegroundColor Yellow
        Write-Host ""
    }
}

Write-Host "Driver files ready for analysis!" -ForegroundColor Green
Write-Host "Copy these files to Linux for deeper analysis with:" -ForegroundColor Yellow
Write-Host "  - strings pae_quantum.sys > quantum_strings.txt" -ForegroundColor Yellow
Write-Host "  - objdump -d pae_quantum.sys > quantum_disassembly.txt" -ForegroundColor Yellow
Write-Host "  - hexdump -C pae_quantum.sys | head -100" -ForegroundColor Yellow
