# Mobile App Deployment Guide

This project previously shipped a **Kivy/KivyMD** mobile client under the `mobile/` directory.
That implementation is now **fully deprecated and removed** in favor of the unified
Flet-based application that can be packaged for Android and iOS.

For current mobile deployment instructions, please see the up‑to‑date guide in:

- `SETUP_MOBILE.md` – building Android APK / iOS IPA with `flet build`

If you still have local Kivy artifacts, they can be safely deleted. All future
work should target the Flet entry point (`main.py`) so desktop and mobile
share the same codebase.
