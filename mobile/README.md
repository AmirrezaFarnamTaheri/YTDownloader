# Mobile YTDownloader

This directory contains the mobile version of the YTDownloader application, built using [Kivy](https://kivy.org/) and [KivyMD](https://kivymd.readthedocs.io/).

## Prerequisites

*   Python 3.8+
*   Kivy
*   KivyMD
*   Buildozer (for building APKs)

## Installation

1.  Install dependencies:
    ```bash
    pip install kivy kivymd
    ```

2.  Run the app locally:
    ```bash
    python main.py
    ```

## Building for Android (APK)

To build the Android APK, you need [Buildozer](https://github.com/kivy/buildozer) installed on a Linux machine (or WSL).

1.  Install Buildozer:
    ```bash
    pip install buildozer
    sudo apt update
    sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
    ```

2.  Build the APK:
    ```bash
    cd mobile
    buildozer android debug
    ```

The generated APK will be in the `mobile/bin/` directory.
