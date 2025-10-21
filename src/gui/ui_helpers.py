"""
UI Helper functions for applying GMP-style component styling to PyQt6 widgets.
"""

from PyQt6.QtWidgets import QPushButton, QLabel
from typing import Literal

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