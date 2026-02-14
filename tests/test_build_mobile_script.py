"""Tests for scripts/build_mobile.py helpers."""

from pathlib import Path

import scripts.build_mobile as build_mobile


def test_normalize_version():
    assert build_mobile._normalize_version("v2.1.3") == "2.1.3"
    assert build_mobile._normalize_version("2") == "2.0.0"
    assert build_mobile._normalize_version("release-5.4") == "5.4.0"
    assert build_mobile._normalize_version("") == "2.0.0"


def test_find_build_artifacts(tmp_path: Path):
    build_dir = tmp_path / "build" / "apk"
    build_dir.mkdir(parents=True)
    first = build_dir / "old.apk"
    second = build_dir / "new.apk"
    first.write_bytes(b"old")
    second.write_bytes(b"new")

    artifacts = build_mobile._find_build_artifacts(tmp_path, "apk")

    assert len(artifacts) == 2
    assert all(path.suffix == ".apk" for path in artifacts)


def test_temporary_requirements_swap_enabled(tmp_path: Path):
    requirements = tmp_path / "requirements.txt"
    mobile_requirements = tmp_path / "requirements-mobile.txt"

    requirements.write_text("desktop-dep\n", encoding="utf-8")
    mobile_requirements.write_text("mobile-dep\n", encoding="utf-8")

    with build_mobile._temporary_requirements_swap(
        requirements,
        mobile_requirements,
        enabled=True,
    ):
        assert requirements.read_text(encoding="utf-8") == "mobile-dep\n"

    assert requirements.read_text(encoding="utf-8") == "desktop-dep\n"


def test_temporary_requirements_swap_disabled(tmp_path: Path):
    requirements = tmp_path / "requirements.txt"
    mobile_requirements = tmp_path / "requirements-mobile.txt"

    requirements.write_text("desktop-dep\n", encoding="utf-8")
    mobile_requirements.write_text("mobile-dep\n", encoding="utf-8")

    with build_mobile._temporary_requirements_swap(
        requirements,
        mobile_requirements,
        enabled=False,
    ):
        assert requirements.read_text(encoding="utf-8") == "desktop-dep\n"

    assert requirements.read_text(encoding="utf-8") == "desktop-dep\n"
