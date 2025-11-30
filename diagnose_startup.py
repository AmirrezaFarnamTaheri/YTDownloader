# diagnose_startup.py
"""
StreamCatch Startup Diagnostic Tool
Run this to identify why the application isn't starting.
"""
import os
import sys
from pathlib import Path


def check_python():
    print("\n" + "=" * 60)
    print("Python Environment")
    print("=" * 60)
    print(f"Version: {sys.version}")
    print(f"Executable: {sys.executable}")
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    print(f"Working Directory: {os.getcwd()}")


def check_dependencies():
    print("\n" + "=" * 60)
    print("Dependencies")
    print("=" * 60)

    deps = [
        "flet",
        "yt_dlp",
        "requests",
        "beautifulsoup4",
        "Pillow",
        "pyperclip",
        "pypresence",
    ]

    for dep in deps:
        try:
            __import__(dep)
            print(f"✓ {dep}")
        except ImportError as e:
            print(f"✗ {dep}: {e}")


def check_database():
    print("\n" + "=" * 60)
    print("Database")
    print("=" * 60)

    db_path = Path.home() / ".streamcatch" / "history.db"
    print(f"Path: {db_path}")
    print(f"Exists: {db_path.exists()}")

    if db_path.exists():
        print(f"Size: {db_path.stat().st_size} bytes")
        print(f"Writable: {os.access(db_path, os.W_OK)}")

        # Try to open
        try:
            import sqlite3

            conn = sqlite3.connect(db_path, timeout=1.0)
            conn.close()
            print("✓ Can open database")
        except Exception as e:
            print(f"✗ Cannot open database: {e}")


def check_config():
    print("\n" + "=" * 60)
    print("Configuration")
    print("=" * 60)

    config_path = Path.home() / ".streamcatch" / "config.json"
    print(f"Path: {config_path}")
    print(f"Exists: {config_path.exists()}")

    if config_path.exists():
        try:
            import json

            with open(config_path) as f:
                data = json.load(f)
            print(f"✓ Valid JSON with {len(data)} keys")
        except Exception as e:
            print(f"✗ Invalid config: {e}")


def check_ffmpeg():
    print("\n" + "=" * 60)
    print("FFmpeg")
    print("=" * 60)

    import shutil

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        print(f"✓ Found: {ffmpeg}")
    else:
        print("✗ Not found in PATH")


def check_clipboard():
    print("\n" + "=" * 60)
    print("Clipboard")
    print("=" * 60)

    try:
        import pyperclip

        test = pyperclip.paste()
        print(f"✓ Clipboard accessible")
    except Exception as e:
        print(f"✗ Clipboard error: {e}")


def test_flet():
    print("\n" + "=" * 60)
    print("Flet Test")
    print("=" * 60)

    try:
        import flet as ft

        print(f"✓ Flet imported")

        # Try to create a minimal app
        def test_app(page: ft.Page):
            page.add(ft.Text("Test"))
            print("✓ Flet app callback executed")
            page.window_destroy()

        print("Attempting to start Flet...")
        ft.app(target=test_app)
        print("✓ Flet started successfully")

    except Exception as e:
        print(f"✗ Flet error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    print("StreamCatch Startup Diagnostics")
    print("================================\n")

    check_python()
    check_dependencies()
    check_database()
    check_config()
    check_ffmpeg()
    check_clipboard()
    test_flet()

    print("\n" + "=" * 60)
    print("Diagnostics Complete")
    print("=" * 60)
    print("\nIf you see errors above, resolve them before running StreamCatch.")
    print("For support, share this output at: https://github.com/your-repo/issues")
