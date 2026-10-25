# Launch Ghidra to analyze pae_quantum.sys driver
# Usage: .\ghidra_analyze_driver.ps1

$ErrorActionPreference = "Continue"

Write-Host "=== Ghidra Driver Analysis Setup ===" -ForegroundColor Cyan
Write-Host ""

# Find Ghidra
$ghidraRun = $null
$ghidraPaths = @(
    "$env:USERPROFILE\Ghidra",
    "C:\Program Files\Ghidra",
    "C:\Program Files (x86)\Ghidra"
)

foreach ($path in $ghidraPaths) {
    if (Test-Path $path) {
        $bat = Get-ChildItem $path -Recurse -Filter "ghidraRun.bat" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($bat) {
            $ghidraRun = $bat.FullName
            Write-Host "Found Ghidra: $ghidraRun" -ForegroundColor Green
            break
        }
    }
}

if (-not $ghidraRun) {
    Write-Host "ERROR: Ghidra not found!" -ForegroundColor Red
    Write-Host "Please install Ghidra or update the path in this script." -ForegroundColor Yellow
    exit 1
}

# Find driver file
$driverFile = $null
$driverPaths = @(
    "$env:USERPROFILE\Desktop\Quantum2626_DriverFiles\pae_quantum.sys",
    "C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_16dcb910a004b0c4\pae_quantum.sys",
    "C:\WINDOWS\System32\DriverStore\FileRepository\pae_quantum.inf_amd64_60e367fe3befdd09\pae_quantum.sys"
)

foreach ($path in $driverPaths) {
    if (Test-Path $path) {
        $driverFile = $path
        Write-Host "Found driver: $driverFile" -ForegroundColor Green
        break
    }
}

if (-not $driverFile) {
    Write-Host "ERROR: pae_quantum.sys not found!" -ForegroundColor Red
    Write-Host "Searched in:" -ForegroundColor Yellow
    foreach ($path in $driverPaths) {
        Write-Host "  - $path" -ForegroundColor Gray
    }
    exit 1
}

# Create project directory
$projectDir = Join-Path $env:USERPROFILE "ghidra_projects"
if (-not (Test-Path $projectDir)) {
    New-Item -ItemType Directory -Path $projectDir | Out-Null
}

$projectName = "Quantum2626_Driver"
$projectPath = Join-Path $projectDir $projectName

Write-Host ""
Write-Host "Project will be created at: $projectPath" -ForegroundColor Cyan
Write-Host ""
Write-Host "Launching Ghidra..." -ForegroundColor Yellow
Write-Host ""
Write-Host "=== Ghidra Analysis Guide ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Once Ghidra opens:" -ForegroundColor Yellow
Write-Host "1. Create a new project (File > New Project)" -ForegroundColor White
Write-Host "2. Import the driver file: $driverFile" -ForegroundColor White
Write-Host "3. When prompted, select 'Yes' to analyze" -ForegroundColor White
Write-Host "4. Use default analysis options (or customize)" -ForegroundColor White
Write-Host ""
Write-Host "=== What to Look For ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. MMIO Register Access:" -ForegroundColor Yellow
Write-Host "   - Search for: MmMapIoSpace, MmUnmapIoSpace" -ForegroundColor White
Write-Host "   - Look for: readl/writel patterns (32-bit MMIO)" -ForegroundColor White
Write-Host "   - Find: Register offsets (0x0000, 0x0004, 0x0008, etc.)" -ForegroundColor White
Write-Host ""
Write-Host "2. Buffer Management:" -ForegroundColor Yellow
Write-Host "   - Search for: AllocateCommonBuffer, DMA functions" -ForegroundColor White
Write-Host "   - Look for: Buffer address registers" -ForegroundColor White
Write-Host ""
Write-Host "3. Interrupt Handling:" -ForegroundColor Yellow
Write-Host "   - Search for: IoConnectInterrupt, InterruptService" -ForegroundColor White
Write-Host "   - Look for: Interrupt status/ack registers" -ForegroundColor White
Write-Host ""
Write-Host "4. Audio Stream Control:" -ForegroundColor Yellow
Write-Host "   - Search for: Start/Stop functions" -ForegroundColor White
Write-Host "   - Look for: Format/sample rate registers" -ForegroundColor White
Write-Host "   - Find: Position registers" -ForegroundColor White
Write-Host ""
Write-Host "5. PCI Configuration:" -ForegroundColor Yellow
Write-Host "   - Search for: IoRead/WriteConfig functions" -ForegroundColor White
Write-Host "   - Look for: BAR mapping (BAR0, BAR1, etc.)" -ForegroundColor White
Write-Host ""
Write-Host "Launching Ghidra..." -ForegroundColor Green

# Set JAVA_HOME if not set
$javaHome = [System.Environment]::GetEnvironmentVariable("JAVA_HOME", "Machine")
if (-not $javaHome) {
    $javaHome = [System.Environment]::GetEnvironmentVariable("JAVA_HOME", "User")
}
if (-not $javaHome) {
    # Try to find Java 21+ (required for Ghidra 12+)
    $java21Dirs = Get-ChildItem "C:\Program Files\Eclipse Adoptium" -Directory | Where-Object { $_.Name -match "jdk-2[1-9]|jdk-[3-9]" }
    if ($java21Dirs) {
        $java21Dir = $java21Dirs | Sort-Object Name -Descending | Select-Object -First 1
        $javaPath = Join-Path $java21Dir.FullName "bin\java.exe"
        if (Test-Path $javaPath) {
            $javaHome = $java21Dir.FullName
            Write-Host "Found Java 21+ at: $javaHome" -ForegroundColor Yellow
        }
    }
    # Fallback to any Java
    if (-not $javaHome) {
        $javaPath = Get-ChildItem "C:\Program Files\Eclipse Adoptium" -Recurse -Filter "java.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($javaPath) {
            $javaHome = Split-Path (Split-Path $javaPath.FullName -Parent) -Parent
            Write-Host "Found Java at: $javaHome" -ForegroundColor Yellow
        }
    }
}

if ($javaHome) {
    $env:JAVA_HOME = $javaHome
    Write-Host "Using JAVA_HOME: $javaHome" -ForegroundColor Green
}

# Launch Ghidra
$ghidraDir = Split-Path $ghidraRun -Parent
Set-Location $ghidraDir

# Create a batch file that sets JAVA_HOME and launches Ghidra
$launchBat = Join-Path $env:TEMP "launch_ghidra.bat"
@"
@echo off
if defined JAVA_HOME (
    set JAVA_HOME=$javaHome
)
cd /d "$ghidraDir"
call "$ghidraRun"
"@ | Out-File -FilePath $launchBat -Encoding ASCII

Start-Process -FilePath $launchBat

Write-Host ""
Write-Host "Ghidra launched! Follow the guide above to analyze the driver." -ForegroundColor Green
Write-Host ""
Write-Host "Tip: Use Ghidra's 'Search > For Strings' to find register offsets" -ForegroundColor Yellow
Write-Host "     Use 'Search > For Scalars' to find magic numbers/offsets" -ForegroundColor Yellow
