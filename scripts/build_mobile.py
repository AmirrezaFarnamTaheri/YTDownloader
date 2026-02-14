"""Build mobile bundles with mobile-safe dependencies."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sysconfig
from contextlib import contextmanager
from pathlib import Path


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build StreamCatch mobile apps.")
    parser.add_argument(
        "--target",
        choices=("apk", "aab", "ipa"),
        default="apk",
        help="Mobile target to build (default: apk).",
    )
    parser.add_argument(
        "--build-version",
        default=os.environ.get("APP_VERSION", "2.0.0"),
        help="Build version (default: APP_VERSION env or 2.0.0).",
    )
    parser.add_argument(
        "--project",
        default="StreamCatch",
        help="Project name for bundle metadata.",
    )
    parser.add_argument(
        "--org",
        default="com.jules.streamcatch",
        help="Reverse-domain org identifier.",
    )
    parser.add_argument(
        "--product",
        default="StreamCatch",
        help="Product name shown in UI metadata.",
    )
    parser.add_argument(
        "--description",
        default="Ultimate Video Downloader",
        help="Bundle description string.",
    )
    parser.add_argument(
        "--build-number",
        default=os.environ.get("BUILD_NUMBER"),
        help="Optional build number for Android/iOS.",
    )
    parser.add_argument(
        "--template",
        default=None,
        help="Path or URL to a custom Flet Flutter template.",
    )
    parser.add_argument(
        "--template-dir",
        default=None,
        help="Relative path to a template inside a repository.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose Flet build output.",
    )
    parser.add_argument(
        "--skip-requirements-swap",
        action="store_true",
        help="Do not temporarily replace requirements.txt with mobile requirements.",
    )
    parser.add_argument(
        "--requirements-file",
        default="requirements.txt",
        help="Main requirements file path (default: requirements.txt).",
    )
    parser.add_argument(
        "--mobile-requirements-file",
        default="requirements-mobile.txt",
        help="Mobile requirements file path (default: requirements-mobile.txt).",
    )
    return parser.parse_args()


def _normalize_version(raw: str) -> str:
    value = (raw or "2.0.0").strip()
    value = value[1:] if value.startswith("v") else value
    if re.fullmatch(r"\d+\.\d+\.\d+", value):
        return value
    parts = re.split(r"[^\d]+", value)
    numeric = [p for p in parts if p]
    if not numeric:
        return "2.0.0"
    while len(numeric) < 3:
        numeric.append("0")
    return ".".join(numeric[:3])


def _find_flet_executable() -> str:
    flet_exe = shutil.which("flet")
    if flet_exe:
        return flet_exe

    candidates = []
    scripts_path = sysconfig.get_path("scripts")
    if scripts_path:
        candidates.append(
            Path(scripts_path) / ("flet.exe" if os.name == "nt" else "flet")
        )

    if os.name == "nt":
        user_scripts = sysconfig.get_path("scripts", scheme="nt_user")
        if user_scripts:
            candidates.append(Path(user_scripts) / "flet.exe")

    for candidate in candidates:
        if candidate and candidate.exists():
            return str(candidate)

    raise FileNotFoundError("Flet CLI not found. Install with: pip install flet")


def _run_build(root: Path, args: argparse.Namespace) -> None:
    build_version = _normalize_version(args.build_version)
    cmd = [
        _find_flet_executable(),
        "build",
        args.target,
        "--build-version",
        build_version,
        "--project",
        args.project,
        "--org",
        args.org,
        "--product",
        args.product,
        "--description",
        args.description,
        "--module-name",
        "main",
    ]

    if args.build_number:
        cmd.extend(["--build-number", str(args.build_number)])

    if args.template:
        cmd.extend(["--template", args.template])
        if args.template_dir:
            cmd.extend(["--template-dir", args.template_dir])

    if args.verbose:
        cmd.append("-v")

    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("FLET_CLI_NO_RICH_OUTPUT", "1")

    subprocess.check_call(cmd, cwd=str(root), env=env)


def _resolve_requirements_paths(
    root: Path, args: argparse.Namespace
) -> tuple[Path, Path]:
    requirements_path = root / args.requirements_file
    mobile_requirements_path = root / args.mobile_requirements_file
    if not requirements_path.exists():
        raise FileNotFoundError(f"Missing {requirements_path}")
    if not mobile_requirements_path.exists():
        raise FileNotFoundError(f"Missing {mobile_requirements_path}")
    return requirements_path, mobile_requirements_path


@contextmanager
def _temporary_requirements_swap(
    requirements_path: Path,
    mobile_requirements_path: Path,
    *,
    enabled: bool,
):
    """Temporarily swap requirements.txt with mobile-safe dependencies."""
    if not enabled:
        yield
        return

    original_requirements = requirements_path.read_text(encoding="utf-8")
    mobile_requirements = mobile_requirements_path.read_text(encoding="utf-8")

    requirements_path.write_text(mobile_requirements, encoding="utf-8")
    try:
        yield
    finally:
        requirements_path.write_text(original_requirements, encoding="utf-8")


def _find_build_artifacts(root: Path, target: str) -> list[Path]:
    """Return artifacts generated by the current build target."""
    build_root = root / "build"
    if not build_root.exists():
        return []

    suffix_map = {"apk": ".apk", "aab": ".aab", "ipa": ".ipa"}
    suffix = suffix_map.get(target)
    if not suffix:
        return []

    return sorted(
        [p for p in build_root.rglob(f"*{suffix}") if p.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def main() -> None:
    """Main entry point for the mobile build script."""
    args = _parse_args()
    root = Path(__file__).resolve().parent.parent
    requirements_path, mobile_requirements_path = _resolve_requirements_paths(
        root, args
    )

    print(f"Building mobile target: {args.target}")
    print(f"Build version: {_normalize_version(args.build_version)}")
    print(
        f"Requirements swap: {'disabled' if args.skip_requirements_swap else 'enabled'}"
    )

    with _temporary_requirements_swap(
        requirements_path,
        mobile_requirements_path,
        enabled=not args.skip_requirements_swap,
    ):
        _run_build(root, args)

    artifacts = _find_build_artifacts(root, args.target)
    if not artifacts:
        raise FileNotFoundError(
            f"No {args.target.upper()} artifacts were found under {root / 'build'} after build."
        )

    print("Build artifacts:")
    for artifact in artifacts[:5]:
        print(f" - {artifact}")


if __name__ == "__main__":
    main()
