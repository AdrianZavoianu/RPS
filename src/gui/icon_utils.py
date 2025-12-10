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


def create_settings_icon(size: int = 18, color: str = None) -> QIcon:
    """Create a gear/settings icon with proper tooth shape.

    Args:
        size: Icon size in pixels
        color: Hex color string (defaults to muted text color)

    Returns:
        QIcon: Gear icon
    """
    from PyQt6.QtGui import QColor, QPen, QBrush, QPainterPath
    from PyQt6.QtCore import QPointF
    import math

    from .styles import COLORS

    if color is None:
        color = COLORS['muted']

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    center = size / 2
    outer_radius = size * 0.46
    inner_radius = size * 0.28
    hole_radius = size * 0.15
    num_teeth = 8
    tooth_width = 0.35  # Width of tooth as fraction of tooth spacing

    pen_color = QColor(color)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QBrush(pen_color))

    # Build gear path with rectangular teeth
    path = QPainterPath()

    for i in range(num_teeth):
        # Angle for this tooth
        base_angle = (i * 2 * math.pi / num_teeth) - math.pi / 2
        half_tooth = (math.pi / num_teeth) * tooth_width

        # Tooth outer corners
        angle1 = base_angle - half_tooth
        angle2 = base_angle + half_tooth

        # Valley angles (between teeth)
        valley_start = base_angle + half_tooth
        valley_end = base_angle + (2 * math.pi / num_teeth) - half_tooth

        if i == 0:
            # Start at outer edge of first tooth
            x = center + outer_radius * math.cos(angle1)
            y = center + outer_radius * math.sin(angle1)
            path.moveTo(x, y)

        # Outer edge of tooth
        x = center + outer_radius * math.cos(angle2)
        y = center + outer_radius * math.sin(angle2)
        path.lineTo(x, y)

        # Down to inner radius
        x = center + inner_radius * math.cos(angle2)
        y = center + inner_radius * math.sin(angle2)
        path.lineTo(x, y)

        # Along inner radius to next tooth
        x = center + inner_radius * math.cos(valley_end)
        y = center + inner_radius * math.sin(valley_end)
        path.lineTo(x, y)

        # Up to next tooth outer
        next_angle1 = valley_end
        x = center + outer_radius * math.cos(next_angle1)
        y = center + outer_radius * math.sin(next_angle1)
        path.lineTo(x, y)

    path.closeSubpath()

    # Cut out center hole
    hole_path = QPainterPath()
    hole_path.addEllipse(QPointF(center, center), hole_radius, hole_radius)
    path = path.subtracted(hole_path)

    painter.drawPath(path)
    painter.end()

    return QIcon(pixmap)


def get_colored_icon_pixmap(icon_name: str, color: str, size: int = 24) -> QPixmap:
    """Load a mask icon and colorize it with the specified color.

    Args:
        icon_name: Name of the icon file (without extension) in resources/icons
        color: Hex color string to apply to the icon
        size: Desired size in pixels

    Returns:
        QPixmap: Colorized icon pixmap
    """
    from PyQt6.QtGui import QColor, QImage

    icon_path = ICONS_DIR / f"{icon_name}.png"
    if not icon_path.exists():
        # Return empty pixmap if icon doesn't exist
        return QPixmap(size, size)

    # Load the original image
    image = QImage(str(icon_path))
    if image.isNull():
        return QPixmap(size, size)

    # Convert to ARGB32 format for pixel manipulation
    image = image.convertToFormat(QImage.Format.Format_ARGB32)

    # Apply color to all pixels while preserving alpha
    target_color = QColor(color)
    for y in range(image.height()):
        for x in range(image.width()):
            pixel = image.pixelColor(x, y)
            if pixel.alpha() > 0:
                # Keep alpha, replace RGB with target color
                new_color = QColor(target_color)
                new_color.setAlpha(pixel.alpha())
                image.setPixelColor(x, y, new_color)

    # Convert to pixmap and scale
    pixmap = QPixmap.fromImage(image)
    if size > 0:
        pixmap = pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

    return pixmap
