# YTDownloader - Complete Setup and Installation Script for Windows
# This script handles everything: checking dependencies, installing, and launching the app

# Setup logging
$LogFile = "ytdownloader_installer.log"
Start-Transcript -Path $LogFile -Append

$ErrorActionPreference = "Stop"

param(
    [switch]$SkipVenv = $false,
    [switch]$Force = $false,
    [string]$Proxy = ""
)

# Color definitions
$GREEN = "Green"
$RED = "Red"
$YELLOW = "Yellow"
$CYAN = "Cyan"

function Write-Status {
    param([string]$Message, [string]$Color = "White")
    Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Status "✓ $Message" -Color $GREEN
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Status "✗ $Message" -Color $RED
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Status "⚠ $Message" -Color $YELLOW
}

function Write-Info {
    param([string]$Message)
    Write-Status "ℹ $Message" -Color $CYAN
}

# Header
Clear-Host
Write-Host @"
╔═══════════════════════════════════════════════════════════╗
║                    YTDownloader Setup                     ║
║            Advanced YouTube Video Downloader              ║
║                   Windows Installation                    ║
╚═══════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

Write-Info "Starting YTDownloader setup and installation..."
Write-Host ""

# Step 1: Check if Python is installed
Write-Status "Step 1: Checking Python installation..." -Color $CYAN
$pythonPath = $null
$pythonVersion = $null

try {
    $pythonPath = (Get-Command python -ErrorAction Stop).Source
    $pythonVersion = python --version 2>&1
    Write-Success "Python found: $pythonVersion"
} catch {
    Write-Error-Custom "Python is not installed or not in PATH"
    Write-Host ""
    Write-Host "Please install Python 3.8 or higher from:" -ForegroundColor White
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Cyan
    Write-Host ""
    Write-Warning-Custom "During installation, make sure to check 'Add Python to PATH'"
    Write-Host ""
    Pause
    Exit 1
}

# Step 2: Verify Python version
Write-Status "Step 2: Verifying Python version..." -Color $CYAN
$versionMatch = $pythonVersion -match "(\d+)\.(\d+)"
if ($versionMatch) {
    $major = [int]$matches[1]
    $minor = [int]$matches[2]

    if ($major -ge 3 -and $minor -ge 8) {
        Write-Success "Python version is compatible (Python $major.$minor)"
    } else {
        Write-Error-Custom "Python 3.8 or higher is required. You have Python $major.$minor"
        Pause
        Exit 1
    }
} else {
    Write-Warning-Custom "Could not verify Python version, proceeding anyway..."
}

Write-Host ""

# Step 3: Get the application directory
Write-Status "Step 3: Setting up application directory..." -Color $CYAN
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appDir = if ($scriptDir) { $scriptDir } else { Get-Location }
$venvPath = Join-Path $appDir "venv"

Write-Status "Application directory: $appDir"

if ($SkipVenv) {
    Write-Warning-Custom "Virtual environment creation skipped (--SkipVenv flag used)"
    $pythonExe = "python"
} else {
    Write-Host ""

    # Step 4: Create or use virtual environment
    Write-Status "Step 4: Setting up virtual environment..." -Color $CYAN

    if ((Test-Path $venvPath) -and -not $Force) {
        Write-Warning-Custom "Virtual environment already exists at $venvPath"
        $useExisting = Read-Host "Use existing virtual environment? (Y/n)"
        if ($useExisting -ne "n" -and $useExisting -ne "N") {
            Write-Status "Using existing virtual environment..."
            $pythonExe = Join-Path $venvPath "Scripts\python.exe"
        } else {
            Write-Status "Removing existing virtual environment..."
            Remove-Item -Recurse -Force $venvPath -ErrorAction SilentlyContinue
            Write-Status "Creating new virtual environment..."
            & python -m venv $venvPath
            Write-Success "Virtual environment created successfully"
            $pythonExe = Join-Path $venvPath "Scripts\python.exe"
        }
    } else {
        Write-Status "Creating virtual environment..."
        & python -m venv $venvPath
        Write-Success "Virtual environment created successfully"
        $pythonExe = Join-Path $venvPath "Scripts\python.exe"
    }
}

Write-Host ""

# Step 5: Install dependencies
Write-Status "Step 5: Installing Python dependencies..." -Color $CYAN
$requirementsFile = Join-Path $appDir "requirements.txt"

if (-not (Test-Path $requirementsFile)) {
    Write-Error-Custom "requirements.txt not found at $appDir"
    Pause
    Exit 1
}

$proxyArg = ""
if (-not [string]::IsNullOrEmpty($Proxy)) {
    $proxyArg = "--proxy $Proxy"
    Write-Info "Using proxy: $Proxy"
}

Write-Status "This may take a few minutes..."
Write-Status "Upgrading pip..."
& $pythonExe -m pip install --upgrade pip $proxyArg
Write-Status "Installing dependencies from requirements.txt..."
& $pythonExe -m pip install -r $requirementsFile $proxyArg
Write-Success "All dependencies installed successfully"

Write-Host ""

# Step 6: Create shortcuts
Write-Status "Step 6: Creating shortcuts and configuration..." -Color $CYAN

# Create Desktop shortcut
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "YTDownloader.lnk"
$iconPath = Join-Path $appDir "icon.ico"

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $pythonExe
    $shortcut.Arguments = "`"$(Join-Path $appDir 'main.py')`""
    $shortcut.WorkingDirectory = $appDir
    $shortcut.Description = "YTDownloader - Advanced YouTube Video Downloader"
    if (Test-Path $iconPath) {
        $shortcut.IconLocation = $iconPath
    }
    $shortcut.Save()
    Write-Success "Desktop shortcut created: $shortcutPath"
} catch {
    Write-Warning-Custom "Could not create desktop shortcut (may require admin rights)"
}

# Create Start Menu shortcut
$startMenuPath = [Environment]::GetFolderPath("StartMenu")
$startMenuDir = Join-Path $startMenuPath "Programs\YTDownloader"
if (-not (Test-Path $startMenuDir)) {
    New-Item -ItemType Directory -Path $startMenuDir -Force | Out-Null
}
$startMenuShortcut = Join-Path $startMenuDir "YTDownloader.lnk"

try {
    $WshShell = New-Object -ComObject WScript.Shell
    $shortcut = $WshShell.CreateShortcut($startMenuShortcut)
    $shortcut.TargetPath = $pythonExe
    $shortcut.Arguments = "`"$(Join-Path $appDir 'main.py')`""
    $shortcut.WorkingDirectory = $appDir
    $shortcut.Description = "YTDownloader - Advanced YouTube Video Downloader"
    if (Test-Path $iconPath) {
        $shortcut.IconLocation = $iconPath
    }
    $shortcut.Save()
    Write-Success "Start Menu shortcut created"
} catch {
    Write-Warning-Custom "Could not create Start Menu shortcut"
}

Write-Host ""

# Step 7: Launch the application
Write-Status "Step 7: Launching YTDownloader..." -Color $CYAN
Write-Info "Starting the application GUI..."
Write-Host ""

$mainPyPath = Join-Path $appDir "main.py"
if (-not (Test-Path $mainPyPath)) {
    Write-Error-Custom "main.py not found at $appDir"
    Pause
    Exit 1
}

# Launch in background so the script can finish
try {
    if ($SkipVenv) {
        Start-Process python -ArgumentList $mainPyPath -WorkingDirectory $appDir -NoNewWindow
    } else {
        Start-Process $pythonExe -ArgumentList $mainPyPath -WorkingDirectory $appDir -NoNewWindow
    }
    Write-Success "YTDownloader is launching..."
    Start-Sleep -Seconds 2
} catch {
    Write-Error-Custom "Failed to start YTDownloader: $_"
    Write-Info "You can manually run it with: $pythonExe $mainPyPath"
}

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          Setup Complete! YTDownloader is Ready            ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

Write-Host "Next time you can launch YTDownloader by:" -ForegroundColor White
Write-Host "  1. Double-clicking the shortcut on your Desktop" -ForegroundColor Cyan
Write-Host "  2. Searching for 'YTDownloader' in the Start Menu" -ForegroundColor Cyan
Write-Host "  3. Running: $pythonExe $mainPyPath" -ForegroundColor Cyan
Write-Host ""

Write-Info "For help and documentation, visit:"
Write-Host "  https://github.com/AmirrezaFarnamTaheri/YTDownloader" -ForegroundColor Cyan
Write-Host ""

Write-Info "Configuration and logs are saved to:"
Write-Host "  Settings: $([Environment]::GetFolderPath('UserProfile'))\.ytdownloader\config.json" -ForegroundColor Cyan
Write-Host "  Logs: $appDir\ytdownloader.log" -ForegroundColor Cyan
Write-Host ""

Write-Success "Setup completed successfully!"
Write-Host ""
