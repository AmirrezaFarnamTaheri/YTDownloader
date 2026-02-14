"""Build installer script"""

import importlib.util
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


def _module_available(module_name: str) -> bool:
    """Return True if the module can be imported in the active interpreter."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ValueError, AttributeError):
        return False


def _append_optional_package_includes(cmd: list[str], package_names: list[str]) -> None:
    """
    Append Nuitka package includes only when modules are available.

    This avoids hard build failures when Windows-local Python envs are
    partially provisioned.
    """
    missing: list[str] = []
    for package_name in package_names:
        if _module_available(package_name):
            cmd.append(f"--include-package={package_name}")
        else:
            missing.append(package_name)

    if missing:
        print(
            "WARNING: Missing optional runtime packages for explicit Nuitka includes: "
            + ", ".join(missing)
        )
        print(
            "WARNING: Build continues, but install requirements for best runtime parity:"
            " pip install -r requirements.txt"
        )


def _check_native_compiler() -> None:
    """Fail early with a helpful message when no C compiler is present."""
    # Nuitka on Windows can bootstrap toolchains itself with
    # --assume-yes-for-downloads; don't block that flow.
    if os.name == "nt":
        return

    if shutil.which("gcc") or shutil.which("clang"):
        return

    print(
        "ERROR: No C compiler found (gcc/clang). Nuitka cannot build native binaries.",
        file=sys.stderr,
    )
    if os.name != "nt":
        print(
            "ERROR: Install build tools, e.g. on Debian/Ubuntu: sudo apt-get install build-essential",
            file=sys.stderr,
        )
    sys.exit(1)


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

    _check_native_compiler()

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

    # For fast local verification builds, allow disabling onefile packaging:
    # STREAMCATCH_ONEFILE=0 python scripts/build_installer.py
    onefile_enabled = os.environ.get("STREAMCATCH_ONEFILE", "1").strip() != "0"
    if sys.platform != "darwin" and onefile_enabled:
        cmd.append("--onefile")

    # LTO significantly increases build time and can be unstable on constrained hosts.
    # Opt-in via STREAMCATCH_ENABLE_LTO=1 for release-grade optimization.
    lto_enabled = os.environ.get("STREAMCATCH_ENABLE_LTO", "").strip() == "1"

    cmd.extend(
        [
            "--lto=yes" if lto_enabled else "--lto=no",
            # Flet often needs explicit data for assets
            f"--include-data-dir={root / 'assets'}=assets",
            f"--include-data-dir={root / 'locales'}=locales",
            f"--output-dir={dist_dir}",
            f"--output-filename={output_name}",
            # Optimizations for yt-dlp build time
            "--nofollow-import-to=yt_dlp.extractor.lazy_extractors",
            "--nofollow-import-to=pytest",
            "--include-package-data=yt_dlp",
        ]
    )

    # Debian/Ubuntu Python builds may not ship static libpython by default.
    if os.name != "nt":
        cmd.append("--static-libpython=no")

    # Optional explicit package inclusion can significantly increase compile time.
    # Keep it opt-in for release builds that require strict bundling parity.
    include_optional = (
        os.environ.get("STREAMCATCH_INCLUDE_OPTIONAL_PACKAGES", "").strip() == "1"
    )
    if include_optional:
        _append_optional_package_includes(
            cmd,
            ["pypresence", "pydrive2", "defusedxml", "keyring", "certifi"],
        )
    else:
        print(
            "INFO: Skipping explicit optional-package includes "
            "(set STREAMCATCH_INCLUDE_OPTIONAL_PACKAGES=1 to enable)."
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
    if os.name == "nt" and not onefile_enabled:
        print("INFO: STREAMCATCH_ONEFILE=0 -> building non-onefile standalone output.")

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
                subprocess.check_call(
                    [
                        iscc,
                        f"/DMyAppVersion={version_str}",
                        str(root / "installers" / "setup.iss"),
                    ]
                )
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
