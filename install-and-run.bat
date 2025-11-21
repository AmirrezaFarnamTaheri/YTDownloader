@echo off
SETLOCAL EnableDelayedExpansion

:: StreamCatch Installer & Launcher for Windows
:: Zero-config setup script

TITLE StreamCatch Setup

echo ============================================================
echo                   StreamCatch Setup
echo            Modern Media Downloader (Windows)
echo ============================================================
echo.

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8+ from Microsoft Store or python.org.
    echo.
    pause
    exit /b 1
)

:: Create Virtual Environment
if not exist "venv" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
)

:: Upgrade PIP
echo [2/4] Checking dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul 2>&1

:: Install Requirements
if exist "requirements.txt" (
    echo [3/4] Installing/Updating libraries...
    pip install -r requirements.txt >nul 2>&1
    if %errorlevel% neq 0 (
        echo [WARNING] Some dependencies failed to install.
        echo Check internet connection or proxy settings.
    )
)

:: Build EXE (Optional)
if not exist "dist\StreamCatch.exe" (
    echo.
    echo [OPTIONAL] Building standalone EXE for easier future access?
    echo This takes a minute but allows you to run the app without this script later.
    set /p BUILD_EXE="Build EXE now? (y/n): "
    if /i "!BUILD_EXE!"=="y" (
        echo Building StreamCatch.exe...
        pyinstaller StreamCatch.spec
        echo.
        echo [SUCCESS] StreamCatch.exe created in 'dist' folder!
        echo You can create a shortcut to dist\StreamCatch.exe on your desktop.
        echo.
    )
)

:: Launch
echo [4/4] Launching StreamCatch...
echo.
if exist "dist\StreamCatch.exe" (
    start "" "dist\StreamCatch.exe"
) else (
    python main.py
)

exit
