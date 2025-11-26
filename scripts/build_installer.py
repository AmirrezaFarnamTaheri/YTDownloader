import os
import subprocess
import shutil
import sys
from pathlib import Path


def build_installer():
    """
    Build a compiled StreamCatch binary and, on Windows with Inno Setup
    available, a full installer.

    This uses Nuitka instead of PyInstaller to produce a true native
    executable, then hands off to Inno Setup (setup.iss) for packaging.
    """
    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist"
    dist_dir.mkdir(exist_ok=True)

    print("Building StreamCatch with Nuitka...")

    # Build compiled binary
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        "--windows-console-mode=disable",
        f"--include-data-dir={root / 'assets'}=assets",
        f"--include-data-dir={root / 'locales'}=locales",
        f"--output-dir={dist_dir}",
        "--output-filename",
        "StreamCatch.exe" if os.name == "nt" else "streamcatch",
        str(root / "main.py"),
    ]

    subprocess.check_call(cmd)

    # 2. Optionally build Windows installer via Inno Setup
    if os.name == "nt":
        iscc = shutil.which("iscc")
        if iscc:
            print("Inno Setup found. Building installer...")
            subprocess.check_call([iscc, str(root / "installers" / "setup.iss")])
            print("Installer built in installers/output/")
        else:
            print("Inno Setup (iscc) not found. Skipping installer generation.")
            print("Standalone executable is in dist/StreamCatch.exe")
    else:
        print("Non-Windows platform detected; only standalone binary was built.")
        print("Output is in dist/")


if __name__ == "__main__":
    build_installer()
