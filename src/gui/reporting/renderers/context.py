"""Render context providing scale-aware dimensions for PDF and Preview rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass
class RenderContext:
    """Context for rendering that handles scale differences between PDF and Preview.
    
    PDF uses mm_to_px conversion (typically ~11.8 at 300 DPI).
    Preview uses fixed pixel values (scaled to ~2.5x for display).
    """
    
    # Scale factor: mm to pixels (PDF) or base unit multiplier (Preview)
    scale: float
    
    # Font sizes
    font_size_small: int = 6
    font_size_normal: int = 7
    font_size_header: int = 8
    font_size_title: int = 9
    
    # Whether this is PDF (high-res) or Preview (screen)
    is_pdf: bool = False
    
    @classmethod
    def for_pdf(cls, mm_to_px: float) -> "RenderContext":
        """Create context for PDF rendering at given DPI."""
        return cls(
            scale=mm_to_px,
            font_size_small=7,
            font_size_normal=7,
            font_size_header=8,
            font_size_title=9,
            is_pdf=True,
        )
    
    @classmethod
    def for_preview(cls) -> "RenderContext":
        """Create context for preview rendering (fixed pixel scale)."""
        return cls(
            scale=1.0,  # Preview uses direct pixel values
            font_size_small=5,
            font_size_normal=6,
            font_size_header=6,
            font_size_title=7,
            is_pdf=False,
        )
    
    def mm(self, value: float) -> int:
        """Convert mm to pixels (PDF) or return scaled value (Preview)."""
        if self.is_pdf:
            return int(value * self.scale)
        # Preview: mm values are pre-converted to pixel ratios
        # Approximate: 1mm ≈ 2.5px at preview scale
        return int(value * 2.5)
    
    def px(self, value: int) -> int:
        """Return pixel value (for preview) or convert from base (for PDF)."""
        if self.is_pdf:
            # PDF: convert from "preview pixels" to actual pixels
            return int(value * self.scale / 2.5)
        return value
    
    # Standard dimensions (in mm for PDF, will be converted)
    @property
    def row_height(self) -> int:
        return self.mm(4) if self.is_pdf else 12
    
    @property
    def header_height(self) -> int:
        return self.mm(5) if self.is_pdf else 16
    
    @property
    def story_col_width(self) -> int:
        return self.mm(12) if self.is_pdf else 45
    
    @property
    def plot_margin_left(self) -> int:
        return self.mm(15) if self.is_pdf else 50
    
    @property
    def plot_margin_right(self) -> int:
        return self.mm(3) if self.is_pdf else 10
    
    @property
    def plot_margin_top(self) -> int:
        return self.mm(3) if self.is_pdf else 10
    
    @property
    def plot_margin_bottom(self) -> int:
        return self.mm(12) if self.is_pdf else 38
