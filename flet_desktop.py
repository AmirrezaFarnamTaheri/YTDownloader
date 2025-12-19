"""
Shim module for flet_desktop to prevent Nuitka build crashes or runtime installation attempts.
Required for flet==0.21.2 on Windows if the environment forces a check for this module.
"""

__version__ = "0.21.2"
