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
             print("WARNING: Could not determine Nuitka version via module, but import succeeded.")

    print("\nStep 2: Building with Nuitka...")

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
        f"--output-filename={'StreamCatch.exe' if os.name == 'nt' else 'streamcatch'}",
        str(root / "main.py"),
    ]

    # Add --no-lto on Windows to prevent memory issues
    if os.name == "nt":
        cmd.append("--no-lto")

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
