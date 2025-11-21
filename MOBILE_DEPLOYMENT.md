# Mobile App Deployment Guide

This guide explains how to build and deploy StreamCatch mobile apps for iOS and Android using the automated GitHub Actions workflows.

## Overview

StreamCatch mobile apps are built using KivyMD framework and can be deployed to both Android and iOS platforms. The repository includes automated GitHub Actions workflows that build the apps on every tagged release or manual trigger.

## Files Added/Modified

### GitHub Actions Workflows

1. **`.github/workflows/build.yml`** (Updated)
   - Fixed deprecated `actions/upload-artifact@v3` → `actions/upload-artifact@v4`
   - Fixed deprecated `actions/download-artifact@v3` → `actions/download-artifact@v4`
   - Updated `actions/checkout@v3` → `actions/checkout@v4`
   - Builds desktop binaries for Windows, macOS, and Linux

2. **`.github/workflows/build-mobile.yml`** (New)
   - Builds Android APK using Buildozer
   - Builds iOS IPA using Kivy-iOS toolchain
   - Includes build caching for faster subsequent builds
   - Automatically creates GitHub releases with mobile app artifacts

### Mobile App Files

3. **`mobile/main.py`** (Fixed)
   - Fixed incomplete file - added `YTDownloaderApp().run()` at the end
   - KivyMD-based mobile application entry point

4. **`mobile/buildozer.spec`** (New)
   - Configuration file for building Android APKs
   - Specifies app name, package name, permissions, and dependencies
   - Configured for both ARM architectures (arm64-v8a, armeabi-v7a)

5. **`mobile/exportOptions.plist`** (New)
   - Configuration for iOS IPA export
   - Requires customization with your Apple Developer Team ID

6. **`.gitignore`** (Updated)
   - Added mobile build artifacts to ignore list
   - Prevents committing large build files

## How to Use

### Automated Builds (Recommended)

The mobile apps are automatically built when you:

1. **Push a version tag:**
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. **Manually trigger the workflow:**
   - Go to your GitHub repository
   - Click "Actions" tab
   - Select "Build Mobile Apps" workflow
   - Click "Run workflow"

### Build Artifacts

After a successful build, you can download the APK and IPA files from:
- GitHub Actions → Workflow run → Artifacts section
- GitHub Releases (for tagged versions)

## Android APK Build

The Android build uses [Buildozer](https://github.com/kivy/buildozer) to create standalone APK files.

### Local Build (Optional)

To build locally on Ubuntu/Linux:

```bash
cd mobile
pip install buildozer cython==0.29.33
buildozer android debug
```

The APK will be in `mobile/bin/` directory.

### Configuration

Edit `mobile/buildozer.spec` to customize:
- App name and version
- Package name and domain
- Required permissions
- Python dependencies
- Target Android API levels

## iOS IPA Build

The iOS build uses [Kivy-iOS](https://github.com/kivy/kivy-ios) toolchain to create IPA files.

### Requirements

⚠️ **Important:** iOS builds require:
- Apple Developer account
- Code signing certificates
- Provisioning profiles
- Team ID configuration

### Code Signing Setup

To enable iOS builds in CI/CD, you need to configure repository secrets:

1. Go to repository Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `APPLE_CERTIFICATE`: Base64-encoded signing certificate (.p12)
   - `APPLE_CERT_PASSWORD`: Certificate password
   - `PROVISIONING_PROFILE`: Base64-encoded provisioning profile
   - `APPLE_TEAM_ID`: Your Apple Developer Team ID

3. Update `mobile/exportOptions.plist`:
   ```xml
   <key>teamID</key>
   <string>YOUR_ACTUAL_TEAM_ID</string>
   ```

### Local Build (macOS only)

```bash
pip install kivy-ios
toolchain build python3 kivy kivymd
cd mobile
toolchain create StreamCatch .
```

Then open the generated Xcode project to build and sign.

## Troubleshooting

### Android Build Issues

1. **Build takes too long:**
   - First build can take 30+ minutes as it downloads Android SDK and NDK
   - Subsequent builds are faster due to caching

2. **Permission errors:**
   - Check that required permissions are listed in `buildozer.spec`
   - Android API 33+ requires runtime permission handling

3. **Dependency errors:**
   - Ensure all Python dependencies are listed in `requirements` in `buildozer.spec`
   - Some packages may not be compatible with mobile platforms

### iOS Build Issues

1. **Code signing failed:**
   - Verify your certificates and provisioning profiles are valid
   - Check that Team ID matches your Apple Developer account
   - Ensure bundle identifier matches provisioning profile

2. **Build not appearing in releases:**
   - iOS builds are marked as `continue-on-error: true`
   - Check workflow logs to see if the build completed
   - Build may succeed but artifact upload can fail without proper signing

## Next Steps

After downloading your built apps:

### Android
1. Enable "Unknown Sources" in Android Settings
2. Install the APK on your device
3. Grant required permissions when prompted

### iOS
1. Install via Xcode or TestFlight
2. For development builds, device must be registered in provisioning profile
3. For App Store distribution, submit through App Store Connect

## Support

For issues with:
- **Buildozer/Android builds:** Check [Buildozer documentation](https://buildozer.readthedocs.io/)
- **Kivy-iOS builds:** Check [Kivy-iOS documentation](https://kivy-ios.readthedocs.io/)
- **GitHub Actions:** Check workflow logs in the Actions tab
- **StreamCatch app:** Open an issue in this repository
