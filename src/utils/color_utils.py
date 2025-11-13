"""Color utilities for gradient interpolation and color schemes."""

from PyQt6.QtGui import QColor


def interpolate_color(
    value: float,
    min_val: float,
    max_val: float,
    start_color: str,
    end_color: str
) -> QColor:
    """
    Interpolate between two colors based on normalized value.

    Args:
        value: The value to interpolate
        min_val: Minimum value in range
        max_val: Maximum value in range
        start_color: Starting color (hex or color name)
        end_color: Ending color (hex or color name)

    Returns:
        QColor interpolated between start and end colors
    """
    # Parse colors
    start_rgb = QColor(start_color)
    end_rgb = QColor(end_color)

    # Normalize value to 0-1 range
    range_val = max_val - min_val if max_val != min_val else 1
    normalized = (value - min_val) / range_val if range_val > 0 else 0.5

    # Clamp to 0-1
    normalized = max(0.0, min(1.0, normalized))

    # Interpolate RGB components
    r = int(start_rgb.red() + (end_rgb.red() - start_rgb.red()) * normalized)
    g = int(start_rgb.green() + (end_rgb.green() - start_rgb.green()) * normalized)
    b = int(start_rgb.blue() + (end_rgb.blue() - start_rgb.blue()) * normalized)

    return QColor(r, g, b)


# Predefined color schemes for gradients
COLOR_SCHEMES = {
    'blue_orange': ('#3b82f6', '#fb923c'),  # Blue to Orange (default)
    'orange_blue': ('#fb923c', '#3b82f6'),  # Orange to Blue (reversed - for lower values being more critical)
    'green_red': ('#2ed573', '#e74c3c'),    # Green to Red
    'cool_warm': ('#60a5fa', '#f87171'),    # Cool blue to Warm red
    'teal_yellow': ('#14b8a6', '#fbbf24'),  # Teal to Yellow
}


def get_gradient_color(value: float, min_val: float, max_val: float, scheme: str = 'blue_orange') -> QColor:
    """
    Get gradient color using a named color scheme.

    Args:
        value: The value to interpolate
        min_val: Minimum value in range
        max_val: Maximum value in range
        scheme: Color scheme name from COLOR_SCHEMES

    Returns:
        QColor from the specified gradient scheme
    """
    start_color, end_color = COLOR_SCHEMES.get(scheme, COLOR_SCHEMES['blue_orange'])
    return interpolate_color(value, min_val, max_val, start_color, end_color)
