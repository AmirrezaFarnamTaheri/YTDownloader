# Mobile Setup Guide (iOS & Android)

StreamCatch is built with [Flet](https://flet.dev), which allows deploying the application to mobile devices (iOS and Android).

## Prerequisites

*   **Python 3.8+**
*   **Flutter SDK** (Required for compiling to mobile)
*   **Flet** (`pip install flet`)

## 1. Android Setup

### Using Flet App (Easiest)
1.  Install the **Flet** app from the Google Play Store.
2.  Run StreamCatch on your PC in "Web" mode:
    ```bash
    export FLET_WEB=1
    python main.py
    ```
3.  Ensure your phone and PC are on the same Wi-Fi.
4.  Open the Flet app on your phone and enter your PC's IP address + port (e.g., `http://192.168.1.50:8550`).

### Building APK (Advanced)
To build a standalone APK, you need to use the `flet build` command (requires Flutter).

1.  Install dependencies:
    ```bash
    pip install flet
    ```
2.  Build the APK:
    ```bash
    flet build apk
    ```
3.  The output APK will be in the `build/apk` folder.

## 2. iOS Setup

### Using Flet App
1.  Install the **Flet** app from the App Store (TestFlight).
2.  Run StreamCatch on your PC in "Web" mode.
3.  Connect via the Flet app using your PC's Local IP.

### Building IPA
*   Requires a Mac with Xcode installed.
1.  Run:
    ```bash
    flet build ipa
    ```
2.  Open the generated project in Xcode to sign and deploy to your device.

## 3. Considerations for Mobile

*   **Storage Permissions**: Ensure the app has permission to write to storage. The default download path `Path.home() / "Downloads"` works on Android but requires permissions.
*   **Background Execution**: Mobile OSs may kill the app if it runs in the background for too long. Keep the app open during large downloads.
*   **FFmpeg**: `yt-dlp` relies on FFmpeg for merging formats. The mobile build of Flet/Python usually includes a basic FFmpeg or relies on `yt-dlp`'s pure python fallback (which may be slower or limited). For full performance, you may need to build a custom recipe including FFmpeg.

## Troubleshooting
*   **"Connection Refused"**: Ensure your firewall allows connections on port 8550.
*   **"Storage Error"**: Check app permissions in Android Settings.
