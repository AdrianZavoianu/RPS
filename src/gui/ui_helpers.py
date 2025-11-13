"""
UI Helper functions for applying GMP-style component styling to PyQt6 widgets.
"""

from PyQt6.QtWidgets import QPushButton, QLabel, QDialog, QWidget
from PyQt6.QtCore import QTimer
from typing import Literal, Optional

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