@echo off
REM YTDownloader - Setup and Installation Batch Script for Windows
REM This script handles everything: checking, installing, and launching

set "LOG_FILE=ytdownloader_installer.log"
call :main >"%LOG_FILE%" 2>&1
exit /b

:main
setlocal enabledelayedexpansion

color 0B
cls

echo.
echo ============================================================
echo                    YTDownloader Setup
echo             Advanced YouTube Video Downloader
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
    echo Virtual environment already exists
    set /p USE_EXISTING="Use existing virtual environment? (Y/n): "
    if /i "!USE_EXISTING!"=="n" (
        echo Removing existing virtual environment...
        rmdir /s /q "%VENV_PATH%"
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
        echo Using existing virtual environment
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
echo Upgrading pip...
call %PYTHON_EXE% -m pip install --upgrade pip
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

call %PYTHON_EXE% -m pip install -r "%APP_DIR%requirements.txt"
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
set ICON_PATH=%APP_DIR%icon.ico
set PWSH_CMD=$WshShell = New-Object -ComObject WScript.Shell;
set PWSH_CMD=%PWSH_CMD% $DesktopPath = [Environment]::GetFolderPath('Desktop');
set PWSH_CMD=%PWSH_CMD% $ShortcutPath = Join-Path $DesktopPath 'YTDownloader.lnk';
set PWSH_CMD=%PWSH_CMD% $Shortcut = $WshShell.CreateShortcut($ShortcutPath);
set PWSH_CMD=%PWSH_CMD% $Shortcut.TargetPath = '%PYTHON_EXE%';
set PWSH_CMD=%PWSH_CMD% $Shortcut.Arguments = '""%APP_DIR%main.py""';
set PWSH_CMD=%PWSH_CMD% $Shortcut.WorkingDirectory = '""%APP_DIR%""';
set PWSH_CMD=%PWSH_CMD% $Shortcut.Description = 'YTDownloader - Advanced YouTube Video Downloader';
if exist "%ICON_PATH%" (
    set PWSH_CMD=%PWSH_CMD% $Shortcut.IconLocation = '""%ICON_PATH%""';
)
set PWSH_CMD=%PWSH_CMD% $Shortcut.Save();

powershell -NoProfile -Command "%PWSH_CMD%"
if errorlevel 1 (
    color 0E
    echo WARNING: Could not create desktop shortcut.
    echo Please try running this script as an administrator.
) else (
    echo [OK] Desktop shortcut created
)
echo.

REM Step 6: Launch the application
echo [Step 6] Launching YTDownloader...
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
echo           Setup Complete! YTDownloader is Ready
echo ============================================================
echo.
echo Next time you can launch YTDownloader by:
echo   1. Double-clicking the shortcut on your Desktop
echo   2. Running the batch file again
echo   3. Command: "%PYTHON_EXE%" "%APP_DIR%main.py"
echo.
echo Configuration and logs are saved to:
echo   Settings: %USERPROFILE%\.ytdownloader\config.json
echo   Logs: %APP_DIR%ytdownloader.log
echo.
echo For help and documentation, visit:
echo   https://github.com/AmirrezaFarnamTaheri/YTDownloader
echo.
pause
exit /b 0
