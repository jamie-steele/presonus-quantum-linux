# Install Ghidra for driver analysis
# Downloads and sets up Ghidra

param(
    [string]$InstallDir = "$env:USERPROFILE\Ghidra",
    [switch]$SkipJavaCheck
)

$ErrorActionPreference = "Continue"

Write-Host "=== Ghidra Installation ===" -ForegroundColor Cyan
Write-Host ""

# Check Java
if (-not $SkipJavaCheck) {
    Write-Host "Checking for Java..." -ForegroundColor Yellow
    $java = Get-Command java -ErrorAction SilentlyContinue
    if (-not $java) {
        Write-Host "WARNING: Java not found in PATH" -ForegroundColor Yellow
        Write-Host "Ghidra requires Java 17 or later" -ForegroundColor Yellow
        Write-Host "Install Java from: https://adoptium.net/" -ForegroundColor Cyan
        Write-Host ""
        $continue = Read-Host "Continue anyway? (y/N)"
        if ($continue -ne "y") {
            exit 1
        }
    } else {
        $javaVersion = java -version 2>&1 | Select-String "version"
        Write-Host "Java found: $javaVersion" -ForegroundColor Green
    }
}

# Create install directory
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

# Try to find latest release from GitHub API
Write-Host "Finding latest Ghidra release..." -ForegroundColor Yellow
try {
    $releaseInfo = Invoke-RestMethod -Uri "https://api.github.com/repos/NationalSecurityAgency/ghidra/releases/latest" -UseBasicParsing
    $ghidraUrl = ($releaseInfo.assets | Where-Object { $_.name -match "ghidra.*\.zip" -and $_.name -notmatch "source" } | Select-Object -First 1).browser_download_url
    
    if (-not $ghidraUrl) {
        # Fallback to known version
        Write-Host "Could not find release, using fallback URL" -ForegroundColor Yellow
        $ghidraUrl = "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.1_build/ghidra_11.1_PUBLIC_20241218.zip"
    }
} catch {
    Write-Host "Could not fetch release info, using fallback URL" -ForegroundColor Yellow
    $ghidraUrl = "https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_11.1_build/ghidra_11.1_PUBLIC_20241218.zip"
}

$zipFile = Join-Path $InstallDir "ghidra.zip"

Write-Host "Downloading Ghidra..." -ForegroundColor Yellow
Write-Host "URL: $ghidraUrl" -ForegroundColor Gray
Write-Host "This may take a few minutes (~200MB download)..." -ForegroundColor Yellow
Write-Host ""

try {
    # Download with progress
    Invoke-WebRequest -Uri $ghidraUrl -OutFile $zipFile -UseBasicParsing
    
    if (Test-Path $zipFile) {
        $size = (Get-Item $zipFile).Length / 1MB
        Write-Host "Downloaded: $([math]::Round($size, 2)) MB" -ForegroundColor Green
        Write-Host ""
        
        Write-Host "Extracting..." -ForegroundColor Yellow
        Expand-Archive -Path $zipFile -DestinationPath $InstallDir -Force
        
        # Find the extracted folder
        $ghidraFolder = Get-ChildItem $InstallDir -Directory | Where-Object { $_.Name -match "^ghidra" } | Select-Object -First 1
        
        if ($ghidraFolder) {
            Write-Host "Ghidra extracted to: $($ghidraFolder.FullName)" -ForegroundColor Green
            Write-Host ""
            Write-Host "To run Ghidra:" -ForegroundColor Cyan
            Write-Host "  cd `"$($ghidraFolder.FullName)`"" -ForegroundColor White
            Write-Host "  .\ghidraRun.bat" -ForegroundColor White
            Write-Host ""
            Write-Host "Or create a shortcut to: $($ghidraFolder.FullName)\ghidraRun.bat" -ForegroundColor Yellow
            
            # Clean up zip
            Remove-Item $zipFile -Force
        } else {
            Write-Host "ERROR: Could not find extracted Ghidra folder" -ForegroundColor Red
        }
    }
} catch {
    Write-Host "ERROR: Download failed" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    Write-Host ""
    Write-Host "You can download manually from:" -ForegroundColor Yellow
    Write-Host "https://github.com/NationalSecurityAgency/ghidra/releases" -ForegroundColor Cyan
    exit 1
}
