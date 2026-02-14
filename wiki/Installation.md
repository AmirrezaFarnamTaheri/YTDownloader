# Installation Guide

## Prebuilt Releases

Download binaries from:

- <https://github.com/AmirrezaFarnamTaheri/YTDownloader/releases>

## Windows (Installer / EXE)

1. Download `StreamCatch-Windows-Installer.exe` (or `StreamCatch_Setup_vX.Y.Z.exe`).
2. Run installer and follow prompts.
3. Launch StreamCatch from Start Menu.

Standalone binary builds place `StreamCatch.exe` in `dist/`.

## Linux (Debian/Ubuntu)

1. Download `StreamCatch-Linux-amd64.deb`.
2. Install:

```bash
sudo dpkg -i StreamCatch-Linux-amd64.deb
sudo apt-get install -f
```

3. Launch via app menu or `streamcatch` command.

## macOS

1. Download `StreamCatch-macOS.dmg`.
2. Open DMG and drag app into `Applications`.
3. If needed, approve app under macOS Security settings.

## Android (APK)

1. Download `StreamCatch-Android.apk` from Releases.
2. Enable trusted/unknown-source install on your device.
3. Install APK and launch.

## Build From Source

### App Runtime

```bash
python3 -m pip install -r requirements.txt
python3 main.py
```

### Desktop Native Build

```bash
python3 scripts/build_installer.py
```

### Android APK Build

```bash
python3 scripts/build_mobile.py --target apk
```

## Notes

- FFmpeg is recommended for full post-processing features.
- Mobile builds require Flutter/Flet mobile toolchain availability.
