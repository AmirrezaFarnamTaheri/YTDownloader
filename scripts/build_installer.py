import os
import subprocess
import shutil
import sys
from pathlib import Path

def build_installer():
    print("Building StreamCatch...")

    # 1. Build with PyInstaller
    subprocess.check_call([
        sys.executable, "-m", "PyInstaller", "streamcatch.spec", "--clean", "--noconfirm"
    ])

    # 2. Check if Inno Setup is available (Windows)
    iscc = shutil.which("iscc")
    if iscc:
        print("Inno Setup found. Building installer...")
        subprocess.check_call([iscc, "installers/setup.iss"])
        print("Installer built in installers/output/")
    else:
        print("Inno Setup (iscc) not found. Skipping installer generation.")
        print("Standalone executable is in dist/StreamCatch.exe (Windows) or dist/StreamCatch (Linux/Mac)")

if __name__ == "__main__":
    build_installer()
