"""
UI Helper functions for applying GMP-style component styling to PyQt6 widgets.
"""

from PyQt6.QtWidgets import QPushButton, QLabel, QDialog, QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from typing import Literal, Optional, Tuple

ButtonVariant = Literal["primary", "secondary", "danger", "ghost"]
ButtonSize = Literal["sm", "md", "lg"]
LabelStyle = Literal["header", "subheader", "muted", "small"]


def apply_button_style(button: QPushButton,
                      variant: ButtonVariant = "primary",
                      size: ButtonSize = "md") -> None:
    """
    Apply GMP-style button styling to a QPushButton.

    Args:
        button: The QPushButton to style
        variant: Button style variant (primary, secondary, danger, ghost)
        size: Button size (sm, md, lg)
    """
    if variant != "primary":
        button.setProperty("styleClass", variant)

    if size != "md":
        button.setProperty("size", size)

    # Force style refresh
    button.style().unpolish(button)
    button.style().polish(button)


def apply_label_style(label: QLabel, style: LabelStyle) -> None:
    """
    Apply GMP-style label styling to a QLabel.

    Args:
        label: The QLabel to style
        style: Label style (header, subheader, muted, small)
    """
    label.setProperty("styleClass", style)

    # Force style refresh
    label.style().unpolish(label)
    label.style().polish(label)


def create_styled_button(text: str,
                        variant: ButtonVariant = "primary",
                        size: ButtonSize = "md") -> QPushButton:
    """
    Create a new QPushButton with GMP styling applied.

    Args:
        text: Button text
        variant: Button style variant
        size: Button size

    Returns:
        Styled QPushButton
    """
    button = QPushButton(text)
    apply_button_style(button, variant, size)
    return button


def create_styled_label(text: str, style: LabelStyle) -> QLabel:
    """
    Create a new QLabel with GMP styling applied.

    Args:
        text: Label text
        style: Label style

    Returns:
        Styled QLabel
    """
    label = QLabel(text)
    apply_label_style(label, style)
    return label


def create_tab_button(text: str, active: bool = False) -> QPushButton:
    """Create a tab-like push button with underline accent styling."""
    btn = QPushButton(text)
    btn.setCheckable(True)
    btn.setChecked(active)
    btn.setFixedHeight(32)
    btn.setMinimumWidth(80)
    return btn


def create_text_link_button(text: str) -> QPushButton:
    """Create a text link style button for lightweight actions."""
    btn = QPushButton(text)
    return btn


def show_dialog_with_blur(dialog: QDialog, parent: Optional[QWidget] = None) -> int:
    """
    Show a modal dialog with blur overlay on parent window.

    Args:
        dialog: The dialog to show
        parent: Parent widget to apply blur overlay to

    Returns:
        Dialog result code
    """
    from gui.blur_overlay import BlurOverlay

    overlay = None

    if parent:
        # Create and show blur overlay
        overlay = BlurOverlay(parent)
        overlay.show_animated()

        # Ensure dialog is on top
        QTimer.singleShot(50, lambda: dialog.raise_())

    # Show dialog
    result = dialog.exec()

    # Hide overlay
    if overlay:
        overlay.hide_animated()
        QTimer.singleShot(250, overlay.deleteLater)

    return result


def create_checkbox_icons(size: int = 20) -> Tuple[QIcon, QIcon]:
    """Create checkbox icons for unchecked and checked states.

    Args:
        size: Size of the icon in pixels (default: 20)

    Returns:
        Tuple of (unchecked_icon, checked_icon)
    """
    # Unchecked icon (empty)
    unchecked_pixmap = QPixmap(size, size)
    unchecked_pixmap.fill(Qt.GlobalColor.transparent)
    unchecked_icon = QIcon(unchecked_pixmap)

    # Checked icon (with checkmark)
    checked_pixmap = QPixmap(size, size)
    checked_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(checked_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw checkmark
    painter.setPen(QPen(QColor("#ffffff"), 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    # Checkmark path (optimized for visibility)
    painter.drawLine(int(size * 0.25), int(size * 0.5), int(size * 0.4), int(size * 0.65))
    painter.drawLine(int(size * 0.4), int(size * 0.65), int(size * 0.75), int(size * 0.3))

    painter.end()
    checked_icon = QIcon(checked_pixmap)

    return unchecked_icon, checked_icon
