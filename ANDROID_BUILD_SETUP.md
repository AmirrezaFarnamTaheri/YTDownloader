# Android Build Setup & Troubleshooting Guide

## Overview

This document explains the Android Buildozer setup and how to resolve the `sdkmanager` error that occurs during the build process.

## The Problem

When running `buildozer android debug`, you may encounter this error:

```
# sdkmanager path "/home/runner/.buildozer/android/platform/android-sdk/tools/bin/sdkmanager" does not exist, sdkmanager is not installed
Error: Process completed with exit code 1.
```

### Root Cause

Buildozer was looking for the `sdkmanager` tool in the old Android SDK directory structure (`tools/bin/`), but modern Android SDK uses the new `cmdline-tools` structure. The Android SDK cmdline-tools were not downloaded or extracted in the correct location.

## Solution

### Automated Setup (Recommended)

A setup script has been provided to automatically configure your Android build environment:

```bash
bash setup_android_build.sh
```

This script will:
1. Verify all prerequisites (Java, Python, Git, etc.)
2. Create the correct directory structure for Android SDK
3. Download the Android Command Line Tools
4. Extract and set them up in the correct location (`~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/`)
5. Accept Android SDK licenses
6. Install required SDK components (platform-tools, Android 33 SDK, build-tools 33.0.0)

### Manual Setup Steps

If you prefer to set up manually:

```bash
# 1. Create the directory structure
mkdir -p ~/.buildozer/android/platform/android-sdk/cmdline-tools
mkdir -p ~/.android
touch ~/.android/repositories.cfg

# 2. Download Android Command Line Tools
cd ~/.buildozer/android/platform/android-sdk/cmdline-tools
wget https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip
unzip commandlinetools-linux-11076708_latest.zip
mv cmdline-tools latest
rm commandlinetools-linux-11076708_latest.zip

# 3. Accept licenses
yes | ~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager --licenses

# 4. Install SDK components
~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager \
    "platform-tools" \
    "platforms;android-33" \
    "build-tools;33.0.0"
```

## Building the APK

After setup is complete, build the Android APK:

```bash
cd mobile
buildozer android debug
```

The APK will be created in `mobile/bin/`

## Configuration

The buildozer configuration is in `mobile/buildozer.spec`. Key settings:

```ini
# App configuration
title = StreamCatch
package.name = streamcatch
package.domain = com.ytdownloader
version = 1.0.0

# Python dependencies
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,requests,urllib3,certifi

# Android settings
android.api = 33              # Target API
android.minapi = 21           # Minimum API
android.ndk = 25b             # NDK version
android.archs = arm64-v8a,armeabi-v7a  # Build architectures

# Path to sdkmanager (tells Buildozer where to find it)
sdkmanager_path = $HOME/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager
```

## Prerequisites

Before building, ensure you have:

- **Java Development Kit (JDK)**: `sudo apt-get install openjdk-17-jdk`
- **Python 3.8+**: `python3 --version`
- **Buildozer**: `pip install buildozer`
- **Cython**: `pip install cython==0.29.33`
- **Git**: `sudo apt-get install git`
- **System tools**: `sudo apt-get install zip unzip`

## Build System Dependencies (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y \
    git zip unzip openjdk-17-jdk python3-pip \
    autoconf automake libtool pkg-config zlib1g-dev \
    libncurses5-dev libncursesw5-dev \
    cmake libffi-dev libssl-dev
```

## Troubleshooting

### "sdkmanager command not found"
- Ensure you ran the setup script or followed the manual setup steps
- Verify the path: `ls ~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager`

### "License agreements have not been accepted"
- Run: `yes | ~/.buildozer/android/platform/android-sdk/cmdline-tools/latest/bin/sdkmanager --licenses`

### Build takes too long
- First build can take 30+ minutes as it downloads Python, Kivy, and other dependencies
- Subsequent builds are much faster
- Check the buildozer log: `cat .buildozer/android/platform/build-<app>_0/build.log`

### Out of disk space
- Android builds need ~10-15 GB of space for:
  - Android SDK & NDK
  - Python-for-Android dependencies
  - App build artifacts
- Clean cache if needed: `buildozer android clean`

### Network issues during build
- Buildozer downloads many dependencies - a stable internet connection is essential
- If a download fails, buildozer may not retry automatically
- You can manually trigger re-download by clearing cache: `rm -rf .buildozer/`

## Continuous Integration (GitHub Actions)

The GitHub Actions workflow (`.github/workflows/build-mobile.yml`) automatically:
1. Sets up the environment on Ubuntu runners
2. Runs the setup commands
3. Builds the APK
4. Uploads artifacts

You can trigger the workflow by:
- Pushing a version tag: `git tag v1.0.0 && git push origin v1.0.0`
- Manually in GitHub Actions → Build Mobile Apps → Run workflow

## Environment Variables

If needed, you can configure these before building:

```bash
# Disable verbose output
export BUILDOZER_LOG_LEVEL=1

# Set custom build path
export BUILDOZER_ANDROID_ACCEPT_SDK_LICENSE=True

# Force specific Cython version
export CYTHON_VERSION=0.29.33
```

## References

- [Buildozer Documentation](https://buildozer.readthedocs.io/)
- [Python-for-Android](https://github.com/kivy/python-for-android)
- [Kivy Framework](https://kivy.org/)
- [KivyMD](https://kivymd.readthedocs.io/)
