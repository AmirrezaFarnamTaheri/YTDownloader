# StreamCatch - Windows Setup Guide

Complete setup and installation guide for Windows users.

## Quick Start (Easiest Method)

### Option 1: Using the Batch Script (Recommended for most users)

1. **Download the repository** or clone it to your computer
2. **Right-click** on `install-and-run.bat` in the StreamCatch folder
3. **Click** "Run as administrator" (optional but recommended)
4. **Wait** for the installation to complete
5. **StreamCatch will launch automatically!**

### Option 2: Using PowerShell Script (Advanced users)

1. **Open PowerShell** as Administrator
2. **Navigate** to the StreamCatch folder:
   ```powershell
   cd "C:\path\to\StreamCatch"
   ```
3. **Run the setup script**:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\install-and-run.ps1
   ```
4. **Wait** for installation to complete
5. **StreamCatch will launch automatically!**

## What These Scripts Do

### install-and-run.bat
- ✓ Checks if Python 3.8+ is installed
- ✓ Creates a Python virtual environment
- ✓ Installs all required dependencies
- ✓ Creates desktop and Start Menu shortcuts
- ✓ Launches the StreamCatch GUI
- ✓ Works on all Windows versions

### install-and-run.ps1
- ✓ Same as batch script but with enhanced features
- ✓ Better error handling and reporting
- ✓ Colored output for better readability
- ✓ Advanced options (--SkipVenv, --Force flags)
- ✓ Requires PowerShell execution policy adjustment

## System Requirements

- **Windows**: Windows 7 or newer (Windows 10/11 recommended)
- **Python**: 3.8 or higher
- **RAM**: 256 MB minimum
- **Disk Space**: 200 MB minimum
- **Internet**: Required for setup and downloading videos

## Prerequisites

### Step 1: Install Python

If you don't have Python installed:

1. **Download** from: https://www.python.org/downloads/
2. **Run** the installer
3. **IMPORTANT**: Check the box "Add Python to PATH"
4. **Click** "Install Now" or customize as needed
5. **Verify** installation by opening Command Prompt and typing:
   ```cmd
   python --version
   ```

### Step 2: Download StreamCatch

**Option A: Clone from GitHub**
```cmd
git clone https://github.com/AmirrezaFarnamTaheri/StreamCatch.git
cd StreamCatch
```

**Option B: Download ZIP**
1. Visit: https://github.com/AmirrezaFarnamTaheri/StreamCatch
2. Click "Code" → "Download ZIP"
3. Extract the ZIP file to your desired location

## Detailed Installation Steps

### Using Batch Script (Recommended)

1. **Open File Explorer**
2. **Navigate** to the StreamCatch folder
3. **Right-click** on `install-and-run.bat`
4. **Select** "Run as administrator"
5. **Command Prompt window** will open and show:
   ```
   [14:30:42] Step 1: Checking Python installation...
   [14:30:42] ✓ Python 3.11.5
   ...
   ```
6. **Wait** for all steps to complete (typically 2-5 minutes)
7. **StreamCatch GUI** will open automatically
8. **Done!** The app is now installed

### Troubleshooting the Batch Script

**Issue**: "Python is not installed or not in PATH"
- **Solution**: Install Python from https://www.python.org/downloads/
- **Important**: Check "Add Python to PATH" during installation
- **Verify**: Open Command Prompt and type `python --version`

**Issue**: Virtual environment creation fails
- **Solution**: Run the script as Administrator
- **Alternative**: Delete the `venv` folder and try again

**Issue**: Dependencies installation fails
- **Solution**: Check your internet connection
- **Alternative**: Run the script again, it will use existing venv

**Issue**: StreamCatch doesn't launch
- **Solution**: Check that `main.py` exists in the folder
- **Alternative**: Manually run: `venv\Scripts\python.exe main.py`

---

### Using PowerShell Script

1. **Right-click** on the Start Menu
2. **Select** "Windows PowerShell (Admin)" or "Terminal (Admin)"
3. **Allow** PowerShell to run scripts:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```
4. **Type** `Y` and press Enter to confirm
5. **Navigate** to StreamCatch folder:
   ```powershell
   cd "C:\path\to\StreamCatch"
   ```
6. **Run** the script:
   ```powershell
   .\install-and-run.ps1
   ```
7. **Watch** the colored output showing progress
8. **StreamCatch** will launch when complete

### PowerShell Script Options

**Skip virtual environment creation:**
```powershell
.\install-and-run.ps1 -SkipVenv
```

**Force recreate virtual environment:**
```powershell
.\install-and-run.ps1 -Force
```

---

## Manual Installation (If scripts don't work)

If the automated scripts fail, you can install manually:

### Step 1: Open Command Prompt
- Press `Win + R`
- Type `cmd`
- Press Enter

### Step 2: Navigate to StreamCatch
```cmd
cd C:\path\to\StreamCatch
```

### Step 3: Create virtual environment
```cmd
python -m venv venv
```

### Step 4: Activate virtual environment
```cmd
venv\Scripts\activate
```

### Step 5: Upgrade pip
```cmd
python -m pip install --upgrade pip
```

### Step 6: Install dependencies
```cmd
pip install -r requirements.txt
```

### Step 7: Run StreamCatch
```cmd
python main.py
```

---

## After Installation

### Launching StreamCatch

After the setup script completes, you can launch StreamCatch in several ways:

**Method 1: Desktop Shortcut** (Easiest)
- Double-click the "StreamCatch" shortcut on your desktop

**Method 2: Start Menu**
- Search for "StreamCatch" in Windows Start Menu
- Click the result to launch

**Method 3: Command Prompt**
```cmd
cd C:\path\to\StreamCatch
venv\Scripts\python.exe main.py
```

**Method 4: Run the batch script again**
```cmd
install-and-run.bat
```

---

## Configuration

### Settings Location
Settings are automatically saved to:
```
C:\Users\[YourUsername]\.streamcatch\config.json
```

This file stores:
- Theme preference (light/dark mode)
- Future: Download preferences, custom settings

### Logs Location
Application logs are saved to:
```
C:\path\to\StreamCatch\streamcatch.log
```

Check this file if you encounter issues.

---

## Uninstallation

To completely remove StreamCatch:

1. **Delete the StreamCatch folder**
2. **Delete desktop shortcuts** (right-click → Delete)
3. **Uninstall Start Menu shortcut**:
   - Right-click Start Menu
   - Select "Uninstall" on StreamCatch
4. **Optional**: Delete configuration:
   - Delete `C:\Users\[YourUsername]\.streamcatch\` folder

Python itself will remain installed for other programs.

---

## Getting Help

### Common Issues

**Issue**: "ModuleNotFoundError: No module named 'yt_dlp'"
- **Solution**: Run `install-and-run.bat` again
- **Alternative**: Manually run: `venv\Scripts\pip.exe install yt_dlp`

**Issue**: "No module named 'tkinter'"
- **Solution**: Reinstall Python with "tcl/tk and IDLE" selected
- **Download**: https://www.python.org/downloads/

**Issue**: Download fails with network error
- **Solution**: Check your internet connection
- **Alternative**: Use Settings tab → Proxy to configure proxy

**Issue**: GUI doesn't open
- **Solution**: Check `streamcatch.log` for error details
- **Report**: Create an issue on GitHub with log contents

### Support Resources

- **Documentation**: https://github.com/AmirrezaFarnamTaheri/StreamCatch/blob/main/README.md
- **Issues**: https://github.com/AmirrezaFarnamTaheri/StreamCatch/issues
- **Discussions**: GitHub Discussions tab

---

## Advanced Options

### Running with Custom Python Path

If you have multiple Python versions:

```cmd
C:\Python311\python.exe main.py
```

### Creating Custom Shortcuts

Create a batch file called `run-streamcatch.bat`:

```batch
@echo off
cd /d "%~dp0"
venv\Scripts\python.exe main.py
pause
```

### Updating Dependencies

To update to the latest compatible versions:

```cmd
cd C:\path\to\StreamCatch
venv\Scripts\python.exe -m pip install --upgrade -r requirements.txt
```

---

## Version History

- **2.0** - Rebrand to StreamCatch with Flet UI
- **1.0** - Initial release

---

## License

StreamCatch is licensed under the MIT License. See LICENSE file for details.

---

**Last Updated**: November 2024
**Tested On**: Windows 10, Windows 11
**Python**: 3.8, 3.9, 3.10, 3.11+
