import os
import shutil
import subprocess
import sys
from pathlib import Path


def build_installer():
    """
    Build a compiled StreamCatch binary and, on Windows with Inno Setup
    available, a full installer.

    This uses Nuitka instead of PyInstaller to produce a true native
    executable, then hands off to Inno Setup (setup.iss) for packaging.
    """
    print("\n" + "=" * 60)
    print("StreamCatch Build Script")
    print("=" * 60 + "\n")

    root = Path(__file__).resolve().parent.parent
    dist_dir = root / "dist"
    dist_dir.mkdir(exist_ok=True)

    print("Step 1: Checking Python environment...")
    print(f"Python: {sys.version}")
    print(f"Root: {root}")
    print(f"Dist: {dist_dir}")

    # Verify requirements
    try:
        import nuitka
        from nuitka import Version

        print(f"Nuitka version: {Version.getNuitkaVersion()}")
    except ImportError:
        print("ERROR: Nuitka not installed. Run: pip install nuitka")
        sys.exit(1)
    except AttributeError:
        # Fallback for some versions or if structure differs
        try:
            subprocess.run([sys.executable, "-m", "nuitka", "--version"], check=True)
        except Exception:
            print(
                "WARNING: Could not determine Nuitka version via module, but import succeeded."
            )

    print("\nStep 2: Building with Nuitka...")

    # Build compiled binary
    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--onefile",
        # Enable LTO if stable, otherwise disable for speed/memory
        # "--lto=no",
        # Flet often needs explicit data for assets
        f"--include-data-dir={root / 'assets'}=assets",
        f"--include-data-dir={root / 'locales'}=locales",
        f"--output-dir={dist_dir}",
        f"--output-filename={'StreamCatch.exe' if os.name == 'nt' else 'streamcatch'}",
    ]

    # Windows specific flags
    if os.name == "nt":
        cmd.extend(
            [
                "--windows-console-mode=disable",
                "--windows-icon-from-ico=assets/icon.ico",
                "--company-name=StreamCatch",
                "--product-name=StreamCatch",
                "--file-version=2.0.0.0",
                "--product-version=2.0.0.0",
                "--copyright=Copyright © 2024 Jules",
            ]
        )
    elif sys.platform == "darwin":
        # MacOS specific flags
        cmd.extend(
            [
                "--macos-create-app-bundle",
                "--macos-app-icon=assets/icon.icns",  # Assuming icon exists
                "--macos-app-name=StreamCatch",
                "--macos-app-version=2.0.0",
            ]
        )

    # Linux/Mac specific flags (if any needed for Nuitka)
    if sys.platform.startswith("linux"):
        # Ensure patchelf is used
        pass

    cmd.append(str(root / "main.py"))

    # Remove empty strings
    cmd = [c for c in cmd if c]

    print(f"Build command: {' '.join(cmd)}\n")

    try:
        subprocess.check_call(cmd)
        print("\n✓ Build completed successfully\n")
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed with exit code {e.returncode}\n", file=sys.stderr)
        sys.exit(1)

    # 2. Optionally build Windows installer via Inno Setup
    if os.name == "nt":
        iscc = shutil.which("iscc")
        if iscc:
            print("Step 3: Building Windows installer...")
            try:
                subprocess.check_call([iscc, str(root / "installers" / "setup.iss")])
                print("✓ Installer built in installers/output/\n")
            except subprocess.CalledProcessError as e:
                print(
                    f"✗ Installer build failed with exit code {e.returncode}\n",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print("⚠ Inno Setup (iscc) not found. Skipping installer generation.")
            print("⚠ Standalone executable is in dist/StreamCatch.exe\n")
    else:
        print("Non-Windows platform: standalone binary built.")
        print(f"Output is in {dist_dir}/\n")

    print("=" * 60)
    print("Build complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        build_installer()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFATAL ERROR: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)
