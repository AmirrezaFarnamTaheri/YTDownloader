# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

def _project_dir() -> Path:
    # When executed by PyInstaller, ``__file__`` is not always populated in the
    # spec execution namespace. Fall back to the provided spec path (the first
    # ``.spec`` argument) or the current working directory so the project root
    # can still be resolved on all platforms.
    spec_arg = next((Path(arg) for arg in sys.argv[1:] if arg.endswith('.spec')), None)
    if '__file__' in globals():
        return Path(__file__).resolve().parent
    if spec_arg and spec_arg.exists():
        return spec_arg.resolve().parent
    return Path.cwd()


project_dir = _project_dir()


def _collect_datas():
    datas = []
    locales_dir = project_dir / "locales"
    if locales_dir.exists():
        datas.append((str(locales_dir / "*.json"), "locales"))
    assets_dir = project_dir / "assets"
    if assets_dir.exists():
        datas.append((str(assets_dir / "*"), "assets"))
    return datas


a = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=_collect_datas(),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='StreamCatch',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
