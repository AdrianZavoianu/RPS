"""Shared visual style constants for result tables and plots."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


DEFAULT_SERIES_COLORS: Tuple[str, ...] = (
    "#ff4757",
    "#1e90ff",
    "#2ed573",
    "#ff6348",
    "#a29bfe",
    "#00d2d3",
    "#ffa502",
    "#ff6b81",
    "#5f27cd",
    "#01a3a4",
    "#48dbfb",
    "#c44569",
    "#f8b500",
)

AVERAGE_SERIES_COLOR = "#ffa500"
ZERO_LINE_COLOR = "#4a7d89"

STORY_PADDING_STANDARD = 0.1
STORY_PADDING_MAXMIN = 0.1

TABLE_CELL_PADDING = "4px 6px"
TABLE_HEADER_PADDING = "4px 6px"


def series_color(index: int) -> str:
    """Return a deterministic color for the given series index."""
    if not DEFAULT_SERIES_COLORS:
        return "#d1d5db"
    return DEFAULT_SERIES_COLORS[index % len(DEFAULT_SERIES_COLORS)]
