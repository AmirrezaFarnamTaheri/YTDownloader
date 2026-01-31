"""Build installer script"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Avoid compiling yt-dlp's massive lazy extractor table, which can exhaust
# the Windows C compiler heap when Nuitka converts it to C code.
os.environ.setdefault("YTDLP_NO_LAZY_EXTRACTORS", "1")


def ensure_macos_app_bundle(dist_dir: Path, app_name: str, binary_name: str) -> Path:
    """Assemble a .app bundle in ``dist/`` for downstream packaging.

    Nuitka's onefile output can scatter macOS bundle parts across helper
    directories. CI expects a concrete ``dist/StreamCatch.app`` for DMG
    creation, so we copy or build the bundle if it is missing.
    """

    target = dist_dir / f"{app_name}.app"
    if target.exists():
        return target

    # First, check if Nuitka produced a bundle elsewhere under dist/.
    for candidate in dist_dir.rglob("*.app"):
        if candidate.is_dir():
            shutil.copytree(candidate, target, dirs_exist_ok=True)
            return target

    # Fallback: construct a minimal bundle from the emitted files.
    contents_dir = target / "Contents"
    macos_dir = contents_dir / "MacOS"
    resources_dir = contents_dir / "Resources"
    macos_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(exist_ok=True)

    info_plist = dist_dir / "Info.plist"
    if info_plist.exists():
        shutil.copy2(info_plist, contents_dir / "Info.plist")

    resources_src = dist_dir / "Resources"
    if resources_src.exists():
        for item in resources_src.iterdir():
            dest = resources_dir / item.name
            if item.is_dir():
                shutil.copytree(item, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dest)

    binary_src = dist_dir / binary_name
    if binary_src.exists():
        shutil.copy2(binary_src, macos_dir / app_name)

    return target


# pylint: disable=too-many-branches, too-many-statements


def _find_iscc() -> str | None:
    """Locate ISCC.exe for Inno Setup across common install locations."""
    iscc = shutil.which("iscc")
    if iscc:
        return iscc

    candidates = [
        Path(os.environ.get("LOCALAPPDATA", ""))
        / "Programs"
        / "Inno Setup 6"
        / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    ]

    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)

    return None


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
        # pylint: disable=import-outside-toplevel
        # pylint: disable=unused-import
        import nuitka  # noqa: F401 - import for availability check
        from nuitka import Version

        print(f"Nuitka version: {Version.getNuitkaVersion()}")
    except ImportError:
        print("ERROR: Nuitka not installed. Run: pip install nuitka")
        sys.exit(1)
    except AttributeError:
        # pylint: disable=broad-exception-caught
        # Fallback for some versions or if structure differs
        try:
            subprocess.run([sys.executable, "-m", "nuitka", "--version"], check=True)
        except Exception:
            print(
                "WARNING: Could not determine Nuitka version via module, but import succeeded."
            )

    print("\nStep 2: Building with Nuitka...")

    # Build compiled binary
    output_name = (
        "StreamCatch.exe"
        if os.name == "nt"
        else "StreamCatch" if sys.platform == "darwin" else "streamcatch"
    )

    cmd = [
        sys.executable,
        "-m",
        "nuitka",
        "--standalone",
        "--assume-yes-for-downloads",
        # Onefile yields a smaller distribution, but leave it disabled on
        # macOS so we can easily assemble a .app bundle for the DMG step.
    ]

    if sys.platform != "darwin":
        cmd.append("--onefile")

    cmd.extend(
        [
            # Enable LTO for optimization
            "--lto=yes",
            # Flet often needs explicit data for assets
            f"--include-data-dir={root / 'assets'}=assets",
            f"--include-data-dir={root / 'locales'}=locales",
            f"--output-dir={dist_dir}",
            f"--output-filename={output_name}",
            # Optimizations for yt-dlp build time
            "--nofollow-import-to=yt_dlp.extractor.lazy_extractors",
            "--include-package-data=yt_dlp",
            # Include important runtime dependencies that might be missed
            "--include-package=pypresence",
            "--include-package=pydrive2",
            "--include-package=defusedxml",
            "--include-package=keyring",
            "--include-package=certifi",
        ]
    )

    # Windows specific flags
    version_str = os.environ.get("APP_VERSION", "2.0.0").lstrip("v")

    # Ensure version string is valid for Windows (X.X.X.X)
    win_version = version_str
    if win_version.count(".") < 3:
        win_version += ".0" * (3 - win_version.count("."))

    if os.name == "nt":
        icon_path = root / "assets" / "icon_windows_native.ico"
        legacy_icon_path = root / "assets" / "icon.ico"
        fallback_icon_path = root / "assets" / "icon_windows.ico"
        if not icon_path.exists() and fallback_icon_path.exists():
            icon_path = fallback_icon_path
        if not icon_path.exists() and legacy_icon_path.exists():
            icon_path = legacy_icon_path
        if not icon_path.exists():
            # Fallback: try to use logo.svg or skip icon
            print(f"WARNING: {icon_path} not found, building without icon")
        else:
            cmd.append(f"--windows-icon-from-ico={icon_path}")
        cmd.extend(
            [
                "--windows-console-mode=disable",
                "--company-name=StreamCatch",
                "--product-name=StreamCatch",
                f"--file-version={win_version}",
                f"--product-version={win_version}",
                "--copyright=Copyright (c) 2024-2025 StreamCatch Team",
            ]
        )
    elif sys.platform == "darwin":
        # MacOS specific flags
        icon_path = root / "assets" / "icon_macos_native.icns"
        legacy_icon_path = root / "assets" / "icon.icns"
        fallback_icon_path = root / "assets" / "icon_macos.icns"
        if not icon_path.exists() and fallback_icon_path.exists():
            icon_path = fallback_icon_path
        if not icon_path.exists() and legacy_icon_path.exists():
            icon_path = legacy_icon_path
        cmd.extend(
            [
                "--macos-create-app-bundle",
                f"--macos-app-icon={icon_path}" if icon_path.exists() else "",
                "--macos-app-name=StreamCatch",
                f"--macos-app-version={version_str}",
            ]
        )

    cmd.append(str(root / "main.py"))

    # Remove empty strings
    cmd = [c for c in cmd if c]

    print(f"Build command: {' '.join(cmd)}\n")

    try:
        subprocess.check_call(cmd)
        print("\n[OK] Build completed successfully\n")
    except subprocess.CalledProcessError as e:
        print(
            f"\n[ERROR] Build failed with exit code {e.returncode}\n", file=sys.stderr
        )
        sys.exit(1)

    if sys.platform == "darwin":
        bundle_path = ensure_macos_app_bundle(dist_dir, "StreamCatch", output_name)
        print(f"macOS app bundle ready at: {bundle_path}\n")

    # 2. Optionally build Windows installer via Inno Setup
    if os.name == "nt":
        iscc = _find_iscc()
        if iscc:
            print("Step 3: Building Windows installer...")
            try:
                subprocess.check_call([iscc, str(root / "installers" / "setup.iss")])
                print("[OK] Installer built in installers/output/\n")
            except subprocess.CalledProcessError as e:
                print(
                    f"[ERROR] Installer build failed with exit code {e.returncode}\n",
                    file=sys.stderr,
                )
                sys.exit(1)
        else:
            print(
                "[WARNING] Inno Setup (iscc) not found. Skipping installer generation."
            )
            print("[INFO] Standalone executable is in dist/StreamCatch.exe\n")
    else:
        print("Non-Windows platform: standalone binary built.")
        print(f"Output is in {dist_dir}/\n")

    print("=" * 60)
    print("Build complete!")
    print("=" * 60)


if __name__ == "__main__":
    # pylint: disable=broad-exception-caught
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
