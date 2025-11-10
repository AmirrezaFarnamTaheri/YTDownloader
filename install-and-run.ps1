param(
    [switch]$SkipVenv = $false,
    [switch]$Force = $false,
    [string]$Proxy = ""
)

# YTDownloader - Complete Setup and Installation Script for Windows
# This script handles everything: checking dependencies, installing, and launching the app

$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $scriptDir) {
    $scriptDir = (Get-Location).Path
}

$LogFile = Join-Path $scriptDir "ytdownloader_installer.log"
$script:InstallerTranscriptActive = $false
try {
    # Ensure log file directory exists and is writable
    $logDir = Split-Path -Parent $LogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    if (Test-Path $LogFile) {
        # Check if file is writable
        try {
            [System.IO.File]::OpenWrite($LogFile).Close()
        } catch {
            Write-Warning "Log file is not writable: $LogFile"
        }
    }
    Start-Transcript -Path $LogFile -Append -ErrorAction Stop | Out-Null
    $script:InstallerTranscriptActive = $true
} catch {
    Write-Warning "Could not start installer transcript: $_"
}

function Stop-InstallerTranscript {
    if ($script:InstallerTranscriptActive) {
        try {
            Stop-Transcript | Out-Null
        } catch {
            # ignore transcript shutdown failures
        }
        $script:InstallerTranscriptActive = $false
    }
}

function Stop-And-Exit {
    param([int]$Code = 0)
    Stop-InstallerTranscript
    exit $Code
}

# Color definitions
$GREEN = "Green"
$RED = "Red"
$YELLOW = "Yellow"
$CYAN = "Cyan"

function Write-Status {
    param([string]$Message, [string]$Color = 'White')
    Write-Host "[$([DateTime]::Now.ToString('HH:mm:ss'))] $Message" -ForegroundColor $Color
}

function Write-Success {
    param([string]$Message)
    Write-Status "[OK] $Message" -Color $GREEN
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Status "[ERROR] $Message" -Color $RED
}

function Write-Warning-Custom {
    param([string]$Message)
    Write-Status "[WARN] $Message" -Color $YELLOW
}

function Write-Info {
    param([string]$Message)
    Write-Status "[INFO] $Message" -Color $CYAN
}
# Header
try {
    Clear-Host
} catch {
    # Ignore hosts that do not expose a console buffer
}
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
    Stop-And-Exit 1
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
        Stop-And-Exit 1
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
    Stop-And-Exit 1
}

# Check for proxy.txt file (for consistency with batch script)
$proxyFromFile = ""
$proxyFile = Join-Path $appDir "proxy.txt"
if (Test-Path $proxyFile) {
    $proxyFromFile = (Get-Content $proxyFile -First 1).Trim()
    Write-Info "Found proxy.txt, using proxy from file"
}

# Use command-line proxy parameter if provided, otherwise use file
$finalProxy = if (-not [string]::IsNullOrEmpty($Proxy)) { $Proxy } elseif (-not [string]::IsNullOrEmpty($proxyFromFile)) { $proxyFromFile } else { "" }

$pipArgs = @()
if (-not [string]::IsNullOrEmpty($finalProxy)) {
    $pipArgs = @("--proxy", $finalProxy)
    Write-Info "Using proxy: $finalProxy"
}

Write-Status "This may take a few minutes..."
Write-Status "Upgrading pip..."
if ($pipArgs.Count -gt 0) {
    & $pythonExe -m pip install --upgrade pip @pipArgs
} else {
    & $pythonExe -m pip install --upgrade pip
}
if ($LASTEXITCODE -ne 0) {
    Write-Warning-Custom "Failed to upgrade pip. Continuing anyway..."
}

Write-Status "Installing dependencies from requirements.txt..."
if ($pipArgs.Count -gt 0) {
    & $pythonExe -m pip install -r $requirementsFile @pipArgs
} else {
    & $pythonExe -m pip install -r $requirementsFile
}
if ($LASTEXITCODE -ne 0) {
    Write-Error-Custom "Failed to install dependencies. Please check the output above for errors."
    Pause
    Stop-And-Exit 1
}
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
        try {
            $shortcut.IconLocation = $iconPath
        } catch {
            Write-Warning-Custom "Could not set icon for shortcut: $_"
        }
    }
    $shortcut.Save()
    Write-Success "Desktop shortcut created: $shortcutPath"
} catch {
    Write-Warning-Custom "Could not create desktop shortcut (may require admin rights): $_"
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
        try {
            $shortcut.IconLocation = $iconPath
        } catch {
            Write-Warning-Custom "Could not set icon for Start Menu shortcut: $_"
        }
    }
    $shortcut.Save()
    Write-Success "Start Menu shortcut created"
} catch {
    Write-Warning-Custom "Could not create Start Menu shortcut: $_"
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
    Stop-And-Exit 1
}

# Launch in background so the script can finish
try {
    if ($SkipVenv) {
        Start-Process python -ArgumentList $mainPyPath -WorkingDirectory $appDir
    } else {
        Start-Process $pythonExe -ArgumentList $mainPyPath -WorkingDirectory $appDir
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
Write-Host "  Installer log: $LogFile" -ForegroundColor Cyan
Write-Host ""

Write-Success "Setup completed successfully!"
Write-Host ""
Stop-And-Exit 0

