"""
Results Processing System (RPS) - Main Entry Point

A desktop application for processing structural engineering results from ETABS/SAP2000.
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from gui.main_window import MainWindow
from gui.styles import get_stylesheet
from gui.window_utils import set_windows_app_id
from database.base import init_db


def main():
    """Main application entry point."""
    # Initialize database (create tables if they don't exist)
    init_db()

    # Set Windows-specific app ID for taskbar
    set_windows_app_id("StructuralEng.RPS.App.1.0")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("Results Processing System")
    app.setOrganizationName("StructuralEngineering")

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Set modern font
    font = QFont("Segoe UI", 10)
    app.setFont(font)

    # Apply modern dark theme stylesheet
    app.setStyleSheet(get_stylesheet())

    # Create and show main window
    window = MainWindow()
    window.show()

    # Start event loop
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
