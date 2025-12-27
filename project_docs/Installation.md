# Installation

## Windows
1.  Download the latest `StreamCatch_Setup_vX.X.X.exe` from the [Releases](https://github.com/AmirrezaFarnamTaheri/YTDownloader/releases) page.
2.  Double-click the installer.
3.  Follow the on-screen prompts.
4.  StreamCatch will be added to your Start Menu.
5.  The installer ships a compiled native binary (no Python runtime required).

## Linux (Debian/Ubuntu)
1.  Download the `.deb` package (`streamcatch_X.X.X_amd64.deb`).
2.  Install via terminal:
    ```bash
    sudo dpkg -i streamcatch_X.X.X_amd64.deb
    sudo apt-get install -f  # Fix dependencies if needed
    ```
3.  Run `streamcatch` from the terminal or your application menu.
4.  The package includes a compiled native binary.

## macOS
1.  Download the `.dmg` file (`StreamCatch-X.X.X-macOS.dmg`).
2.  Open the image.
3.  Drag "StreamCatch.app" to your Applications folder.
4.  **Note**: You may need to allow the app in "System Settings > Privacy & Security" if it's not signed by an identified developer.
5.  The app bundle contains the compiled native binary.

## From Source
See [Developer Guide](Developer-Guide.md#setup).
