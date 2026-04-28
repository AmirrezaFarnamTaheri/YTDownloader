# Installation

## Recommended: Prebuilt Release

Download the latest release from:

<https://github.com/AmirrezaFarnamTaheri/YTDownloader/releases>

### Windows

1. Download `StreamCatch_Setup_vX.Y.Z.exe`.
2. Run the installer.
3. Launch StreamCatch from the Start Menu or the optional desktop shortcut.

The Windows installer installs one standalone executable:

```text
StreamCatch.exe
```

The release build embeds app assets, icons, and locale files into the onefile
Nuitka executable, so no separate `assets/` or `locales/` folders are required
beside the installed EXE.

### Linux

1. Download the Linux release artifact.
2. If using a Debian package, install with:

```bash
sudo dpkg -i StreamCatch-Linux-amd64.deb
sudo apt-get install -f
```

3. Launch from the app menu or the `streamcatch` command.

### macOS

1. Download the DMG release artifact.
2. Open the DMG and drag StreamCatch into `Applications`.
3. If macOS blocks first launch, approve it in System Settings.

### Android

1. Download `StreamCatch-Android.apk`.
2. Allow installation from trusted downloaded files.
3. Install and launch.

## Optional System Dependency

FFmpeg is strongly recommended for format conversion, muxing, audio extraction,
thumbnail embedding, and other post-processing tasks. Some downloads still work
without FFmpeg, but the best StreamCatch experience assumes it is installed.

## Run From Source

```bash
git clone https://github.com/AmirrezaFarnamTaheri/YTDownloader.git
cd YTDownloader
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python main.py
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

## Build From Source

Desktop onefile build:

```bash
python scripts/build_installer.py
```

Windows installer generation requires Inno Setup. Without Inno Setup, the build
still produces the standalone executable under `dist/`.

Mobile build:

```bash
python scripts/build_mobile.py --target apk
```
