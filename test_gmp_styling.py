#!/usr/bin/env python3
"""
Test script to demonstrate GMP-style button variants and typography in RPS.
Run this to see all the new styling options.
"""

import sys
from PyQt6.QtWidgets import QApplication, QDialog, QVBoxLayout, QHBoxLayout, QLabel
from PyQt6.QtCore import Qt

# Add src to path
sys.path.insert(0, 'src')

from gui.styles import get_stylesheet
from gui.ui_helpers import create_styled_button, create_styled_label


class StyleDemo(QDialog):
    """Demo dialog showing all GMP-style components."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("RPS - GMP Style Demo")
        self.setMinimumSize(600, 500)
        self._create_ui()

    def _create_ui(self):
        """Create demo UI showing all style variants."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Typography demo
        layout.addWidget(create_styled_label("Typography Styles", "header"))
        layout.addWidget(create_styled_label("This is a subheader style", "subheader"))
        layout.addWidget(create_styled_label("This is normal text (default)", ""))
        layout.addWidget(create_styled_label("This is muted text for secondary information", "muted"))
        layout.addWidget(create_styled_label("This is small text for details", "small"))

        # Button variants demo
        layout.addWidget(create_styled_label("Button Variants", "header"))

        button_row1 = QHBoxLayout()
        button_row1.addWidget(create_styled_button("Primary Button", "primary"))
        button_row1.addWidget(create_styled_button("Secondary Button", "secondary"))
        button_row1.addWidget(create_styled_button("Danger Button", "danger"))
        button_row1.addWidget(create_styled_button("Ghost Button", "ghost"))
        layout.addLayout(button_row1)

        # Button sizes demo
        layout.addWidget(create_styled_label("Button Sizes", "subheader"))

        button_row2 = QHBoxLayout()
        button_row2.addWidget(create_styled_button("Small", "primary", "sm"))
        button_row2.addWidget(create_styled_button("Medium (Default)", "primary", "md"))
        button_row2.addWidget(create_styled_button("Large", "primary", "lg"))
        layout.addLayout(button_row2)

        # Info
        layout.addWidget(create_styled_label("🎨 Styling matches GMP frontend design system", "muted"))

        layout.addStretch()


def main():
    """Run the style demo."""
    app = QApplication(sys.argv)

    # Apply the updated GMP-style theme
    app.setStyleSheet(get_stylesheet())

    demo = StyleDemo()
    demo.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()