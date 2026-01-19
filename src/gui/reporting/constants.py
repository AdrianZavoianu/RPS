"""Shared constants for report rendering (PDF and Preview)."""

from __future__ import annotations

# Colors for print (light background)
PRINT_COLORS = {
    "text": "#1f2937",
    "text_muted": "#6b7280",
    "border": "#d1d5db",
    "grid": "#e5e7eb",
    "header_bg": "#f3f4f6",
    "row_alt": "#f9fafb",
    "plot_bg": "#f8f9fa",
}

# Plot colors - high contrast for light background (12 colors for load cases)
PLOT_COLORS = (
    "#dc2626", "#2563eb", "#16a34a", "#ea580c", "#7c3aed",
    "#0891b2", "#ca8a04", "#db2777", "#4f46e5", "#059669",
    "#0284c7", "#be185d",
)

# Average line color - strong orange-red for light backgrounds
AVERAGE_COLOR = "#c2410c"
