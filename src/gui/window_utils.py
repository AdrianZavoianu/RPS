"""
Utility functions for window styling and platform-specific features.
"""

import sys
from PyQt6.QtCore import Qt


def enable_dark_title_bar(window):
    """
    Enable dark title bar on Windows 10/11.

    This makes the window title bar dark to match the app theme.
    Only works on Windows - safely ignored on other platforms.
    """
    if sys.platform == "win32":
        try:
            from ctypes import windll, byref, sizeof, c_int

            # Get window handle
            hwnd = int(window.winId())

            # Windows 10/11 dark mode
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20 (Windows 11)
            # DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19 (Windows 10)
            DWMWA_USE_IMMERSIVE_DARK_MODE = 20

            # Try Windows 11 first
            value = c_int(1)  # 1 = dark mode, 0 = light mode
            result = windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                byref(value),
                sizeof(value)
            )

            # If Windows 11 API failed, try Windows 10
            if result != 0:
                DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1 = 19
                windll.dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    DWMWA_USE_IMMERSIVE_DARK_MODE_BEFORE_20H1,
                    byref(value),
                    sizeof(value)
                )

        except Exception as e:
            # Silently fail on non-Windows or if API not available
            print(f"Could not enable dark title bar: {e}")
            pass


def set_windows_app_id(app_id="StructuralEng.RPS.App.1.0"):
    """
    Set Windows App User Model ID for proper taskbar integration.

    This ensures the app has its own taskbar identity and icon.
    """
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        except Exception:
            pass
