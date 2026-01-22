"""Design tokens and shared style helpers aligned with DESIGN.md."""

from __future__ import annotations

from typing import Dict, Final

import os
import tempfile

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap

# Color palette (see DESIGN.md)
PALETTE: Final[Dict[str, str]] = {
    "bg_primary": "#0a0c10",
    "bg_secondary": "#161b22",
    "bg_tertiary": "#1c2128",
    "bg_hover": "rgba(255, 255, 255, 0.03)",
    "text_primary": "#d1d5db",
    "text_secondary": "#9ca3af",
    "text_muted": "#7f8b9a",
    "accent_primary": "#4a7d89",
    "accent_secondary": "#67e8f9",
    "accent_hover": "rgba(74, 125, 137, 0.18)",
    "accent_selected": "rgba(74, 125, 137, 0.12)",
    "border_default": "#2c313a",
    "border_subtle": "rgba(255, 255, 255, 0.05)",
    "success": "#10b981",
    "warning": "#f59e0b",
    "error": "#ef4444",
    "info": "#3b82f6",
}

# Spacing scale (4px increments)
SPACING: Final[Dict[str, int]] = {
    "xxs": 4,
    "xs": 8,
    "sm": 12,
    "md": 16,
    "lg": 24,
    "xl": 32,
    "xxl": 48,
}

# Typography sizes (px)
TYPOGRAPHY: Final[Dict[str, int]] = {
    "tiny": 12,
    "small": 13,
    "body": 14,
    "subheader": 18,
    "header": 24,
}

_CHECKMARK_CACHE: str | None = None


def get_checkbox_checkmark_url() -> str:
    global _CHECKMARK_CACHE
    if _CHECKMARK_CACHE and os.path.exists(_CHECKMARK_CACHE):
        return _CHECKMARK_CACHE.replace("\\", "/")

    pixmap = QPixmap(18, 18)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor("#ffffff"), 2.4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(4, 9, 7, 12)
    painter.drawLine(7, 12, 14, 5)
    painter.end()

    temp_dir = tempfile.gettempdir()
    path = os.path.join(temp_dir, "rps_checkbox_check.png")
    pixmap.save(path, "PNG")
    _CHECKMARK_CACHE = path
    return path.replace("\\", "/")


class FormStyles:
    """Helper methods for generating consistent form/dialog styles."""

    @staticmethod
    def dialog() -> str:
        c = PALETTE
        t = TYPOGRAPHY
        return f"""
        QDialog {{
            background-color: {c['bg_primary']};
            color: {c['text_primary']};
            font-size: {t['body']}px;
        }}

        QLabel {{
            color: {c['text_primary']};
            font-size: {t['body']}px;
        }}

        QLineEdit, QComboBox {{
            background-color: {c['bg_tertiary']};
            border: 1px solid {c['border_default']};
            border-radius: 6px;
            padding: 8px 12px;
            color: {c['text_primary']};
            font-size: {t['body']}px;
        }}

        QLineEdit:focus,
        QComboBox:focus {{
            border-color: {c['accent_primary']};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 18px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 6px solid {c['text_secondary']};
            margin-right: 8px;
        }}
        """

    @staticmethod
    def group_box() -> str:
        c = PALETTE
        return f"""
        QGroupBox {{
            background-color: {c['bg_secondary']};
            border: 1px solid {c['border_default']};
            border-radius: 8px;
            margin-top: 12px;
            padding: 16px 12px 12px 12px;
        }}
        QGroupBox::title {{
            color: {c['text_secondary']};
            subcontrol-origin: margin;
            left: 12px;
            top: 6px;
            padding: 0 6px 0 6px;
            background-color: transparent;
        }}
        """

    @staticmethod
    def checkbox(*, indent: bool = True) -> str:
        c = PALETTE
        margin_left = "16px" if indent else "8px"
        checkmark_url = get_checkbox_checkmark_url()
        return f"""
        QCheckBox {{
            spacing: 8px;
            color: {c['text_primary']};
            padding: 6px 0;
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 2px solid {c['border_default']};
            background-color: {c['bg_primary']};
            margin-left: {margin_left};
            margin-right: 8px;
        }}
        QCheckBox::indicator:hover {{
            border-color: {c['accent_primary']};
            background-color: {c['bg_secondary']};
        }}
        QCheckBox::indicator:checked {{
            background-color: {c['accent_primary']};
            border-color: {c['accent_primary']};
            image: url({checkmark_url});
        }}
        QCheckBox:hover {{
            background-color: {c['bg_hover']};
            border-radius: 4px;
        }}
        """

    @staticmethod
    def scroll_area() -> str:
        c = PALETTE
        return f"""
        QScrollArea {{
            border: 1px solid {c['border_default']};
            border-radius: 6px;
            background-color: {c['bg_secondary']};
        }}
        QScrollArea > QWidget {{
            background-color: transparent;
        }}
        """

    @staticmethod
    def progress_bar() -> str:
        """Style for QProgressBar widgets."""
        c = PALETTE
        return f"""
        QProgressBar {{
            border: none;
            border-radius: 4px;
            background-color: {c['bg_secondary']};
            height: 8px;
            text-align: center;
        }}
        QProgressBar::chunk {{
            background-color: {c['accent_primary']};
            border-radius: 4px;
        }}
        """

    @staticmethod
    def list_widget() -> str:
        """Style for QListWidget widgets."""
        c = PALETTE
        return f"""
        QListWidget {{
            background-color: {c['bg_tertiary']};
            border: 1px solid {c['border_default']};
            border-radius: 6px;
            padding: 4px;
            color: {c['text_primary']};
        }}
        QListWidget::item {{
            padding: 6px 8px;
            border-radius: 4px;
        }}
        QListWidget::item:selected {{
            background-color: {c['accent_selected']};
            color: {c['text_primary']};
        }}
        QListWidget::item:hover {{
            background-color: {c['bg_hover']};
        }}
        """

    @staticmethod
    def text_log() -> str:
        """Style for read-only text areas (logs, status displays)."""
        c = PALETTE
        t = TYPOGRAPHY
        return f"""
        QTextEdit, QPlainTextEdit {{
            background-color: {c['bg_primary']};
            border: 1px solid {c['border_default']};
            border-radius: 6px;
            padding: 8px;
            color: {c['text_secondary']};
            font-family: monospace;
            font-size: {t['small']}px;
        }}
        """

    @staticmethod
    def tab_widget() -> str:
        """Style for QTabWidget."""
        c = PALETTE
        t = TYPOGRAPHY
        return f"""
        QTabWidget::pane {{
            border: 1px solid {c['border_default']};
            border-radius: 6px;
            background-color: {c['bg_secondary']};
            margin-top: -1px;
        }}
        QTabBar::tab {{
            background-color: {c['bg_tertiary']};
            color: {c['text_secondary']};
            padding: 8px 16px;
            border: 1px solid {c['border_default']};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 2px;
            font-size: {t['body']}px;
        }}
        QTabBar::tab:selected {{
            background-color: {c['bg_secondary']};
            color: {c['text_primary']};
            border-color: {c['border_default']};
        }}
        QTabBar::tab:hover:!selected {{
            background-color: {c['bg_hover']};
        }}
        """

    @staticmethod
    def tab_widget_minimal() -> str:
        """Style for minimal/underline QTabWidget (used in plot widgets)."""
        c = PALETTE
        return f"""
        QTabWidget::pane {{
            border: none;
            background-color: transparent;
        }}
        QTabBar::tab {{
            background-color: transparent;
            color: {c['text_secondary']};
            padding: 8px 14px;
            border: none;
            margin-right: 6px;
        }}
        QTabBar::tab:selected {{
            background-color: transparent;
            color: {c['accent_secondary']};
            border-bottom: 2px solid {c['accent_secondary']};
        }}
        QTabBar::tab:hover {{
            background-color: transparent;
            color: {c['text_primary']};
        }}
        """

    @staticmethod
    def splitter() -> str:
        """Style for QSplitter handles."""
        c = PALETTE
        return f"""
        QSplitter::handle {{
            background-color: {c['border_default']};
        }}
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        QSplitter::handle:hover {{
            background-color: {c['accent_primary']};
        }}
        """

    @staticmethod
    def table_widget() -> str:
        """Style for QTableWidget."""
        c = PALETTE
        t = TYPOGRAPHY
        return f"""
        QTableWidget {{
            background-color: {c['bg_secondary']};
            border: 1px solid {c['border_default']};
            border-radius: 6px;
            gridline-color: {c['border_subtle']};
            color: {c['text_primary']};
            font-size: {t['body']}px;
        }}
        QTableWidget::item {{
            padding: 4px 8px;
        }}
        QTableWidget::item:selected {{
            background-color: {c['accent_selected']};
            color: {c['text_primary']};
        }}
        QHeaderView::section {{
            background-color: {c['bg_tertiary']};
            color: {c['text_secondary']};
            padding: 6px 8px;
            border: none;
            border-bottom: 1px solid {c['border_default']};
            font-weight: 500;
        }}
        """

    @staticmethod
    def header_label(size: str = "header") -> str:
        """Style for header labels.
        
        Args:
            size: Typography size key ("header", "subheader", etc.)
        """
        c = PALETTE
        t = TYPOGRAPHY
        font_size = t.get(size, t["header"])
        return f"color: {c['text_primary']}; font-size: {font_size}px; font-weight: 600;"

    @staticmethod
    def secondary_label() -> str:
        """Style for secondary/description labels."""
        c = PALETTE
        t = TYPOGRAPHY
        return f"color: {c['text_secondary']}; font-size: {t['small']}px;"

    @staticmethod
    def muted_label() -> str:
        """Style for muted/help text labels."""
        c = PALETTE
        t = TYPOGRAPHY
        return f"color: {c['text_muted']}; font-size: {t['tiny']}px; font-style: italic;"
