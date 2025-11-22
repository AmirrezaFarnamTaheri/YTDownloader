# ⚠️ DEPRECATED: Kivy Mobile App

**Note:** This Kivy-based mobile implementation is deprecated and no longer actively maintained. The project has moved to a unified **Flet-based** architecture that supports Windows, Linux, macOS, Android, and iOS from a single codebase (`main.py`).

## How to Build Mobile App (Flet)

To build the modern mobile application using Flet:

1.  **Install Flet:**
    ```bash
    pip install flet
    ```

2.  **Build for Android:**
    ```bash
    flet build apk
    ```

3.  **Build for iOS:**
    ```bash
    flet build ipa
    ```

(See project root `README.md` or `WIKI.md` for detailed build instructions).

---

## Legacy Kivy Instructions (Archived)

*The files in this directory (`main.py`, `buildozer.spec`) correspond to the old Kivy implementation.*

### Prerequisites
*   Python 3.8+
*   Kivy, KivyMD
*   Buildozer
