"""Data parsing and conversion utilities."""


def parse_percentage_value(val) -> float:
    """
    Parse a value that might be a percentage string or numeric.

    Args:
        val: Value to parse (can be "1.23%" or 0.0123)

    Returns:
        Float value as percentage (1.23 for "1.23%" or 0.0123)
    """
    if isinstance(val, str) and '%' in val:
        return float(val.replace('%', ''))
    try:
        return float(val) * 100  # Convert decimal to percentage
    except (ValueError, TypeError):
        return 0.0


def parse_numeric_safe(val, default: float = 0.0) -> float:
    """
    Safely parse a value to float with fallback.

    Args:
        val: Value to parse
        default: Default value if parsing fails

    Returns:
        Parsed float or default value
    """
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def format_value(value: float, decimal_places: int, unit: str = '') -> str:
    """
    Format a numeric value with specified precision and unit.

    Args:
        value: Numeric value to format
        decimal_places: Number of decimal places
        unit: Optional unit suffix (e.g., '%', 'g', 'kN')

    Returns:
        Formatted string
    """
    return f"{value:.{decimal_places}f}{unit}"
