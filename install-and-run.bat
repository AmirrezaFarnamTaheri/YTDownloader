@echo off
REM Lumina - Setup and Installation Batch Script for Windows
REM This script handles everything: checking, installing, and launching

set "LOG_FILE=%~dp0lumina_installer.log"
set "WRAPPER_PS=%TEMP%\lumina_installer_wrapper.ps1"

if /i "%~1"=="__run_main__" (
    shift
    goto :main
)

> "%WRAPPER_PS%" echo param(
>> "%WRAPPER_PS%" echo ^    [string]$ScriptPath,
>> "%WRAPPER_PS%" echo ^    [string]$LogPath
>> "%WRAPPER_PS%" echo ^)
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo $psi = New-Object System.Diagnostics.ProcessStartInfo
>> "%WRAPPER_PS%" echo $psi.FileName = $ScriptPath
>> "%WRAPPER_PS%" echo $psi.Arguments = "__run_main__"
>> "%WRAPPER_PS%" echo $psi.RedirectStandardOutput = $true
>> "%WRAPPER_PS%" echo $psi.RedirectStandardError = $true
>> "%WRAPPER_PS%" echo $psi.StandardOutputEncoding = [System.Text.Encoding]::UTF8
>> "%WRAPPER_PS%" echo $psi.StandardErrorEncoding = [System.Text.Encoding]::UTF8
>> "%WRAPPER_PS%" echo $psi.UseShellExecute = $false
>> "%WRAPPER_PS%" echo $psi.CreateNoWindow = $false
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo $process = New-Object System.Diagnostics.Process
>> "%WRAPPER_PS%" echo $process.StartInfo = $psi
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo try {
>> "%WRAPPER_PS%" echo ^    $null = $process.Start()
>> "%WRAPPER_PS%" echo } catch {
>> "%WRAPPER_PS%" echo ^    Write-Error "Failed to start installer: $_"
>> "%WRAPPER_PS%" echo ^    exit 1
>> "%WRAPPER_PS%" echo }
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo $logWriter = New-Object System.IO.StreamWriter($LogPath, $true, [System.Text.Encoding]::UTF8)
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo try {
>> "%WRAPPER_PS%" echo ^    while (-not $process.HasExited -or -not $process.StandardOutput.EndOfStream -or -not $process.StandardError.EndOfStream) {
>> "%WRAPPER_PS%" echo ^        while (-not $process.StandardOutput.EndOfStream) {
>> "%WRAPPER_PS%" echo ^            $line = $process.StandardOutput.ReadLine()
>> "%WRAPPER_PS%" echo ^            if ($line -ne $null) {
>> "%WRAPPER_PS%" echo ^                $logWriter.WriteLine($line)
>> "%WRAPPER_PS%" echo ^                $logWriter.Flush()
>> "%WRAPPER_PS%" echo ^                Write-Host $line
>> "%WRAPPER_PS%" echo ^                [Console]::Out.Flush()
>> "%WRAPPER_PS%" echo ^            }
>> "%WRAPPER_PS%" echo ^        }
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo ^        while (-not $process.StandardError.EndOfStream) {
>> "%WRAPPER_PS%" echo ^            $errLine = $process.StandardError.ReadLine()
>> "%WRAPPER_PS%" echo ^            if ($errLine -ne $null) {
>> "%WRAPPER_PS%" echo ^                $logWriter.WriteLine($errLine)
>> "%WRAPPER_PS%" echo ^                $logWriter.Flush()
>> "%WRAPPER_PS%" echo ^                Write-Host $errLine
>> "%WRAPPER_PS%" echo ^                [Console]::Error.Flush()
>> "%WRAPPER_PS%" echo ^            }
>> "%WRAPPER_PS%" echo ^        }
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo ^        [Console]::Out.Flush()
>> "%WRAPPER_PS%" echo ^        Start-Sleep -Milliseconds 10
>> "%WRAPPER_PS%" echo ^    }
>> "%WRAPPER_PS%" echo
>> "%WRAPPER_PS%" echo ^    $process.WaitForExit() ^| Out-Null
>> "%WRAPPER_PS%" echo ^    exit $process.ExitCode
>> "%WRAPPER_PS%" echo } finally {
>> "%WRAPPER_PS%" echo ^    $logWriter.Dispose()
>> "%WRAPPER_PS%" echo }

powershell -NoProfile -ExecutionPolicy Bypass -File "%WRAPPER_PS%" -ScriptPath "%~f0" -LogPath "%LOG_FILE%"
set "EXIT_CODE=%ERRORLEVEL%"
del "%WRAPPER_PS%" 2>nul
exit /b %EXIT_CODE%

:main
setlocal enabledelayedexpansion

color 0B
cls

echo.
echo ============================================================
echo                    Lumina Setup
echo             Modern Media Downloader
echo                  Windows Installation
echo ============================================================
echo.

REM Step 1: Check if Python is installed
echo [Step 1] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo.
    echo ERROR: Python is not installed or not in PATH
    echo.
    echo Please install Python 3.8 or higher from:
    echo   https://www.python.org/downloads/
    echo.
    echo IMPORTANT: During installation, check "Add Python to PATH"
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo [OK] %PYTHON_VERSION%
echo.

REM Step 2: Get application directory
echo [Step 2] Setting up application directory...
set APP_DIR=%~dp0
set VENV_PATH=%APP_DIR%venv
set PYTHON_EXE=python

echo Application directory: %APP_DIR%
echo.

REM Step 3: Create virtual environment
echo [Step 3] Setting up virtual environment...
if exist "%VENV_PATH%" (
    echo Virtual environment already exists at: %VENV_PATH%
    echo.
    echo You can either:
    echo   - Use the existing virtual environment (recommended, faster)
    echo   - Remove and recreate it (if you're experiencing issues)
    echo.
    REM Echo the prompt text first - this will flush immediately with newline
    echo Use existing virtual environment? (Y/n):
    REM Now read input - it will appear on next line but prompt is visible
    set /p USE_EXISTING="> "
    REM Trim whitespace and convert to lowercase for comparison
    set "USE_EXISTING=!USE_EXISTING: =!"
    if /i "!USE_EXISTING!"=="n" (
        echo Removing existing virtual environment...
        rmdir /s /q "%VENV_PATH%"
        if not exist "%VENV_PATH%" (
            echo Creating new virtual environment...
            call python -m venv "%VENV_PATH%"
            if errorlevel 1 (
                color 0C
                echo ERROR: Failed to create virtual environment
                pause
                exit /b 1
            )
            echo [OK] Virtual environment created
        ) else (
            color 0C
            echo ERROR: Failed to remove existing virtual environment
            pause
            exit /b 1
        )
    ) else (
        echo [OK] Using existing virtual environment
    )
) else (
    echo Creating new virtual environment...
    call python -m venv "%VENV_PATH%"
    if errorlevel 1 (
        color 0C
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
)
set PYTHON_EXE=%VENV_PATH%\Scripts\python.exe
echo.

REM Step 4: Install dependencies
echo [Step 4] Installing Python dependencies...
echo This may take a few minutes...

set "PROXY_ARG="
if exist "%APP_DIR%proxy.txt" (
    echo Found proxy.txt, setting proxy...
    set /p PROXY_URL=<%APP_DIR%proxy.txt
    set "PROXY_ARG=--proxy !PROXY_URL!"
    echo Using proxy: !PROXY_URL!
)

echo Upgrading pip...
if defined PROXY_ARG (
    call %PYTHON_EXE% -m pip install --upgrade pip !PROXY_ARG!
) else (
    call %PYTHON_EXE% -m pip install --upgrade pip
)
if errorlevel 1 (
    color 0E
    echo WARNING: Failed to upgrade pip. Continuing anyway...
)

echo Installing dependencies from requirements.txt...
if not exist "%APP_DIR%requirements.txt" (
    color 0C
    echo ERROR: requirements.txt not found
    pause
    exit /b 1
)

if defined PROXY_ARG (
    call %PYTHON_EXE% -m pip install -r "%APP_DIR%requirements.txt" !PROXY_ARG!
) else (
    call %PYTHON_EXE% -m pip install -r "%APP_DIR%requirements.txt"
)
if errorlevel 1 (
    color 0C
    echo ERROR: Failed to install dependencies. Please check the output above for errors.
    pause
    exit /b 1
) else (
    echo [OK] All dependencies installed
)
echo.

REM Step 5: Create shortcuts
echo [Step 5] Creating shortcuts...
set ICON_PATH=%APP_DIR%assets\logo.ico

powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $shell = New-Object -ComObject WScript.Shell; $desktop = [Environment]::GetFolderPath('Desktop'); $shortcut = $shell.CreateShortcut((Join-Path $desktop 'Lumina.lnk')); $shortcut.TargetPath = '%PYTHON_EXE%'; $shortcut.Arguments = '%APP_DIR%main.py'; $shortcut.WorkingDirectory = '%APP_DIR%'; $shortcut.Description = 'Lumina - Modern Media Downloader'; if (Test-Path '%ICON_PATH%') { $shortcut.IconLocation = '%ICON_PATH%' }; $shortcut.Save()"
if errorlevel 1 (
    color 0E
    echo WARNING: Could not create desktop shortcut.
    echo Please try running this script as an administrator.
) else (
    echo [OK] Desktop shortcut created
)
echo.

REM Step 6: Launch the application
echo [Step 6] Launching Lumina...
echo Starting the application GUI...
echo.

if not exist "%APP_DIR%main.py" (
    color 0C
    echo ERROR: main.py not found
    pause
    exit /b 1
)

start "" "%PYTHON_EXE%" "%APP_DIR%main.py"
timeout /t 2 /nobreak

color 0A
echo.
echo ============================================================
echo           Setup Complete! Lumina is Ready
echo ============================================================
echo.
echo Next time you can launch Lumina by:
echo   1. Double-clicking the shortcut on your Desktop
echo   2. Running the batch file again
echo   3. Command: "%PYTHON_EXE%" "%APP_DIR%main.py"
echo.
echo Configuration and logs are saved to:
echo   Settings: %USERPROFILE%\.lumina\config.json
echo   App logs: %APP_DIR%lumina.log
echo   Installer log: %LOG_FILE%
echo.
echo For help and documentation, visit:
echo   https://github.com/AmirrezaFarnamTaheri/Lumina
echo.
pause
exit /b 0
