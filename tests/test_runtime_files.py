from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dockerfile_download_path_env_matches_volume():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "ENV STREAMCATCH_DOWNLOAD_PATH=/app/downloads" in dockerfile
    assert 'VOLUME ["/app/downloads", "/home/streamcatch/.streamcatch"]' in dockerfile


def test_dockerfile_healthcheck_uses_configured_port():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "FLET_SERVER_PORT=8550" in dockerfile
    assert "localhost:${FLET_SERVER_PORT}" in dockerfile


def test_compose_passes_download_path_to_container():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    assert "STREAMCATCH_DOWNLOAD_PATH=/app/downloads" in compose
    assert "./downloads:/app/downloads" in compose


def test_generated_build_outputs_are_ignored():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "build_logs/" in gitignore
    assert "installers/output/" in gitignore
    assert "*.exe" in gitignore
    assert "export.json" in gitignore
    assert ".mypy_cache/" in gitignore
    assert ".ruff_cache/" in gitignore


def test_inno_installer_has_nonzero_version_fallback():
    setup_script = (ROOT / "installers" / "setup.iss").read_text(encoding="utf-8")

    assert '#define MyAppVersion "2.0.0"' in setup_script
    assert '#define MyAppVersion "0.0.0"' not in setup_script


def test_inno_installer_installs_only_onefile_executable():
    setup_script = (ROOT / "installers" / "setup.iss").read_text(encoding="utf-8")

    assert 'Source: "..\\dist\\StreamCatch.exe"' in setup_script
    assert 'Source: "..\\locales\\*"' not in setup_script
    assert 'Source: "..\\assets\\*"' not in setup_script


def test_release_workflows_do_not_use_zero_version_fallbacks():
    workflow = (ROOT / ".github" / "workflows" / "build-desktop.yml").read_text(
        encoding="utf-8"
    )

    assert "0.0.0" not in workflow
