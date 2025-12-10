"""Settings popup for project detail window."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QPushButton,
)

from gui.styles import COLORS
from gui.settings_manager import settings


class SettingsPopup(QWidget):
    """Popup widget for global settings."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setup_ui()

    def setup_ui(self):
        """Setup the settings UI."""
        self.setFixedSize(280, 165)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
            }}
            QLabel {{
                color: {COLORS['text']};
                font-size: 13px;
                border: none;
            }}
            QLabel#header {{
                color: {COLORS['accent']};
                font-size: 14px;
                font-weight: 600;
                border: none;
            }}
            QCheckBox {{
                color: {COLORS['text']};
                font-size: 12px;
                spacing: 8px;
                border: none;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['background']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['accent']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Header
        header = QLabel("Settings")
        header.setObjectName("header")
        layout.addWidget(header)

        # Plot settings section
        plot_section = QLabel("Plot Options")
        plot_section.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px; font-weight: 500;")
        layout.addWidget(plot_section)

        # Shading checkbox
        self.shading_checkbox = QCheckBox("Enable envelope shading")
        self.shading_checkbox.setToolTip("Show shaded area between min and max values across all load cases")
        self.shading_checkbox.setChecked(settings.plot_shading_enabled)
        self.shading_checkbox.toggled.connect(self._on_shading_toggled)
        layout.addWidget(self.shading_checkbox)

        # Layout section
        layout_section = QLabel("Layout Options")
        layout_section.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px; font-weight: 500;")
        layout.addWidget(layout_section)

        # Layout borders checkbox
        self.borders_checkbox = QCheckBox("Show layout borders")
        self.borders_checkbox.setToolTip("Show borders between header, browser, and content zones")
        self.borders_checkbox.setChecked(settings.layout_borders_enabled)
        self.borders_checkbox.toggled.connect(self._on_borders_toggled)
        layout.addWidget(self.borders_checkbox)

        # Add stretch to push content up
        layout.addStretch()

    def _on_shading_toggled(self, checked: bool):
        """Handle shading toggle."""
        settings.plot_shading_enabled = checked

    def _on_borders_toggled(self, checked: bool):
        """Handle layout borders toggle."""
        settings.layout_borders_enabled = checked

    def show_below(self, widget: QWidget):
        """Show popup below widget, ensuring it stays within screen bounds."""
        # Get position below widget
        pos = widget.mapToGlobal(widget.rect().bottomLeft())
        x, y = pos.x(), pos.y() + 4

        # Get screen geometry
        screen = QGuiApplication.screenAt(pos)
        if screen:
            screen_rect = screen.availableGeometry()

            # Adjust if popup would go off right edge
            if x + self.width() > screen_rect.right():
                x = screen_rect.right() - self.width() - 8

            # Adjust if popup would go off bottom edge
            if y + self.height() > screen_rect.bottom():
                # Show above the widget instead
                y = widget.mapToGlobal(widget.rect().topLeft()).y() - self.height() - 4

            # Ensure not off left or top edge
            x = max(screen_rect.left() + 8, x)
            y = max(screen_rect.top() + 8, y)

        self.move(x, y)
        self.show()
