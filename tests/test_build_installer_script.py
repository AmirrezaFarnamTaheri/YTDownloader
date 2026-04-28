"""Tests for scripts/build_installer.py helpers."""

from pathlib import Path

import pytest

import scripts.build_installer as build_installer


def test_normalize_app_version_handles_tags_and_dev_versions():
    assert build_installer._normalize_app_version("v2.1.3") == "2.1.3"
    assert build_installer._normalize_app_version("release-5.4") == "5.4.0"
    assert build_installer._normalize_app_version("dev-123") == "123.0.0"
    assert build_installer._normalize_app_version("") == "2.0.0"


def test_normalize_windows_file_version_is_always_four_numeric_parts():
    assert build_installer._normalize_windows_file_version("v2.1.3") == "2.1.3.0"
    assert build_installer._normalize_windows_file_version("dev-123") == "123.0.0.0"


def test_find_built_binary_discovers_nested_nuitka_output(tmp_path: Path):
    dist = tmp_path / "dist"
    nested = dist / "main.dist"
    nested.mkdir(parents=True)
    expected = nested / "StreamCatch.exe"
    expected.write_bytes(b"binary")

    assert build_installer._find_built_binary(dist, "StreamCatch.exe") == expected


def test_verify_build_output_copies_onefile_to_dist_root(tmp_path: Path):
    dist = tmp_path / "dist"
    nested = dist / "onefile-build"
    nested.mkdir(parents=True)
    emitted = nested / "streamcatch"
    emitted.write_bytes(b"binary")

    resolved = build_installer._verify_build_output(
        dist,
        "streamcatch",
        onefile=True,
    )

    assert resolved == dist / "streamcatch"
    assert resolved.read_bytes() == b"binary"


def test_verify_build_output_fails_clearly_when_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError, match="Expected build output"):
        build_installer._verify_build_output(tmp_path, "missing.exe", onefile=True)


def test_runtime_package_includes_are_deterministic():
    cmd = ["python", "-m", "nuitka"]

    build_installer._append_runtime_package_includes(cmd, ["flet", "yt_dlp"])

    assert "--include-package=flet" in cmd
    assert "--include-package=yt_dlp" in cmd
