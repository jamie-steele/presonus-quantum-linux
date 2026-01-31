# Extract all strings from pae_quantum.sys for reverse-engineering.
# Run on Windows with the PreSonus Quantum driver installed.
# Output: driver-reference/strings_pae_quantum.txt, strings_interesting.txt

$ErrorActionPreference = "Continue"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptDir
$driverRef = Join-Path $repoRoot "driver-reference"
$driverRef = $driverRef -replace '\\', '/'

# Find pae_quantum.sys in DriverStore
$driverStore = "C:\Windows\System32\DriverStore\FileRepository"
$driverPath = $null
if (Test-Path $driverStore) {
    $dirs = Get-ChildItem $driverStore -Directory -ErrorAction SilentlyContinue | Where-Object { $_.Name -like "pae_quantum*" }
    foreach ($d in $dirs) {
        $candidate = Join-Path $d.FullName "pae_quantum.sys"
        if (Test-Path $candidate) {
            $driverPath = $candidate
            break
        }
    }
}

# Fallback: known paths from earlier collection
if (-not $driverPath) {
    $known = @(
        "C:\Windows\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\pae_quantum.sys",
        "C:\Windows\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_60e367fe3befdd09\pae_quantum.sys"
    )
    foreach ($p in $known) {
        if (Test-Path $p) { $driverPath = $p; break }
    }
}

if (-not $driverPath) {
    Write-Host "ERROR: pae_quantum.sys not found. Install PreSonus Quantum driver and run again." -ForegroundColor Red
    exit 1
}

Write-Host "Using driver: $driverPath" -ForegroundColor Green
$bytes = [System.IO.File]::ReadAllBytes($driverPath)

# Extract strings (ASCII, length >= 4)
$allStrings = [System.Collections.ArrayList]@()
$current = [System.Text.StringBuilder]::new()
foreach ($b in $bytes) {
    if ($b -ge 32 -and $b -le 126) {
        [void]$current.Append([char]$b)
    } else {
        if ($current.Length -ge 4) {
            [void]$allStrings.Add($current.ToString())
        }
        $current = [System.Text.StringBuilder]::new()
    }
}
if ($current.Length -ge 4) { [void]$allStrings.Add($current.ToString()) }

# Ensure output dir exists (driver-reference may be in repo root)
if (-not (Test-Path $driverRef)) {
    New-Item -ItemType Directory -Path $driverRef -Force | Out-Null
}

# Save all strings
$allPath = Join-Path $driverRef "strings_pae_quantum.txt"
$allStrings | Set-Content -Path $allPath -Encoding UTF8
Write-Host "Wrote $($allStrings.Count) strings to driver-reference/strings_pae_quantum.txt" -ForegroundColor Green

# Interesting subset: offsets, PCI, buffer, register-like, hex
$interesting = $allStrings | Where-Object {
    $_ -match "^(PCI|USB|REG|IO|MEM|IRQ|DMA|BAR|QUANTUM|PRESONUS|1C67|0104|AUDIO|PCM|STREAM|BUFFER|CONTROL|REGISTER|OFFSET|BASE|ADDR)" -or
    $_ -match "0x[0-9A-Fa-f]+" -or
    $_ -match "^[A-Z_]{4,}$" -or
    $_ -match "buffer|register|offset|control|status|enable|start|stop"
} | Select-Object -Unique
$intPath = Join-Path $driverRef "strings_interesting.txt"
$interesting | Set-Content -Path $intPath -Encoding UTF8
Write-Host "Wrote $($interesting.Count) filtered strings to driver-reference/strings_interesting.txt" -ForegroundColor Green
Write-Host "Copy driver-reference/ to your Linux repo and use strings_*.txt in Ghidra search." -ForegroundColor Yellow
