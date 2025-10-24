"""Icon utilities for the RPS application."""

from pathlib import Path
from PyQt6.QtGui import QIcon, QPixmap, QPainter
from PyQt6.QtCore import Qt

# Icon paths
ICONS_DIR = Path(__file__).parent.parent.parent / "resources" / "icons"


def get_app_icon() -> QIcon:
    """Get the main application icon.

    Looks for icon files in this order:
    1. app_icon.ico (Windows native, multi-size)
    2. app_icon.png (Cross-platform)
    3. Auto-generated placeholder

    Returns:
        QIcon: Application icon, or empty icon if file doesn't exist
    """
    # Try .ico first (Windows native, best quality)
    ico_path = ICONS_DIR / "app_icon.ico"
    if ico_path.exists():
        return QIcon(str(ico_path))

    # Try .png next
    png_path = ICONS_DIR / "app_icon.png"
    if png_path.exists():
        return QIcon(str(png_path))

    # Return a generated placeholder icon if no files exist
    return create_placeholder_icon()


def get_window_icon(window_type: str = "default") -> QIcon:
    """Get icon for specific window type.

    Args:
        window_type: Type of window (e.g., "project", "import", "settings")

    Returns:
        QIcon: Window-specific icon or app icon as fallback
    """
    icon_path = ICONS_DIR / f"{window_type}_icon.png"
    if icon_path.exists():
        return QIcon(str(icon_path))

    return get_app_icon()


def create_placeholder_icon(size: int = 64) -> QIcon:
    """Create a simple placeholder icon with geometric shape.

    Uses design system colors and geometric aesthetic.

    Args:
        size: Icon size in pixels

    Returns:
        QIcon: Generated placeholder icon
    """
    from .styles import COLORS

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Draw rounded rect background
    from PyQt6.QtGui import QColor, QPen, QBrush
    from PyQt6.QtCore import QRectF

    # Background
    bg_color = QColor(COLORS['card'])
    painter.setBrush(QBrush(bg_color))
    painter.setPen(QPen(QColor(COLORS['border']), 2))
    painter.drawRoundedRect(QRectF(2, 2, size-4, size-4), 8, 8)

    # Draw geometric "RPS" text
    from PyQt6.QtGui import QFont
    font = QFont("Inter", int(size * 0.3))
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(QColor(COLORS['accent']))
    painter.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, "RPS")

    painter.end()

    return QIcon(pixmap)


def set_app_icons(app):
    """Set application-wide icon.

    Call this in main.py after creating QApplication.

    Args:
        app: QApplication instance
    """
    app.setWindowIcon(get_app_icon())
