"""Shared table rendering logic for PDF and Preview."""

from __future__ import annotations

from typing import List, Optional
import pandas as pd

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QColor, QFont, QPen

from ..constants import PRINT_COLORS
from .context import RenderContext


class TableRenderer:
    """Renders data tables for reports (global results, element results, etc.)."""
    
    def __init__(self, painter: QPainter, ctx: RenderContext):
        self.painter = painter
        self.ctx = ctx
    
    def draw_global_table(
        self,
        x: int, y: int, width: int,
        df: pd.DataFrame,
        decimals: int = 3,
        is_pushover: bool = False,
        max_rows: int = 20,
    ) -> int:
        """Draw a global results table (story-based data).
        
        Returns: Height used by the table.
        """
        if df is None or df.empty:
            return 0
        
        row_h = self.ctx.row_height
        header_h = self.ctx.header_height
        max_rows = min(len(df), max_rows)
        
        # Determine columns to display
        if is_pushover:
            summary = [c for c in df.columns if c in {'Max', 'Min'}]
        else:
            summary = [c for c in df.columns if c in {'Avg', 'Max', 'Min'}]
        
        load_cases = [c for c in df.columns 
                     if c not in {'Story', 'Avg', 'Max', 'Min', 'Average', 'Maximum', 'Minimum'}]
        data_cols = load_cases[:11] + summary[:3]
        
        if not data_cols:
            return 0
        
        story_w = self.ctx.story_col_width
        col_w = (width - story_w) // len(data_cols)
        
        # Header background
        self.painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        self.painter.setPen(QColor(PRINT_COLORS["text"]))
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_header, QFont.Weight.DemiBold))
        
        # Header labels
        self.painter.drawText(x, y, story_w, header_h, Qt.AlignmentFlag.AlignCenter, "Story")
        for i, col in enumerate(data_cols):
            cx = x + story_w + i * col_w
            label = str(col)[:6]
            self.painter.drawText(cx, y, col_w, header_h, Qt.AlignmentFlag.AlignCenter, label)
        
        # Data rows
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_normal))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h
            
            # Alternating row background
            if row_i % 2 == 1:
                self.painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))
            
            # Story label
            story = str(df['Story'].iloc[row_i])[:8] if 'Story' in df.columns else str(df.index[row_i])[:8]
            self.painter.setPen(QColor(PRINT_COLORS["text"]))
            self.painter.drawText(x, ry, story_w, row_h, Qt.AlignmentFlag.AlignCenter, story)
            
            # Value cells
            for col_i, col in enumerate(data_cols):
                cx = x + story_w + col_i * col_w
                val = df[col].iloc[row_i]
                if pd.isna(val):
                    txt = "-"
                elif isinstance(val, (int, float)):
                    txt = f"{val:.{decimals}f}"
                else:
                    txt = str(val)[:6]
                self.painter.drawText(cx, ry, col_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
        
        # Border and grid lines
        total_h = header_h + max_rows * row_h
        self.painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        self.painter.drawRect(x, y, width, total_h)
        
        # Vertical lines
        self.painter.drawLine(x + story_w, y, x + story_w, y + total_h)
        for i in range(1, len(data_cols)):
            lx = x + story_w + i * col_w
            self.painter.drawLine(lx, y, lx, y + total_h)
        
        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            self.painter.drawLine(x, ly, x + width, ly)
        
        return total_h
    
    def draw_element_table(
        self,
        x: int, y: int, width: int,
        df: pd.DataFrame,
        load_cases: List[str],
        columns_config: List[dict],
        decimals: int = 2,
        max_rows: int = 10,
    ) -> int:
        """Draw an element results table (beam/column rotations, etc.).
        
        Args:
            columns_config: List of dicts with 'name', 'width_mm', 'field' keys
            
        Returns: Height used by the table.
        """
        if df is None or df.empty or len(df) == 0:
            return 0
        
        row_h = self.ctx.row_height
        header_h = self.ctx.header_height
        max_rows = min(len(df), max_rows)
        
        # Determine which summary columns are present
        summary_cols = [c for c in ["Avg", "Max", "Min"] if c in df.columns]
        
        # Calculate column widths
        fixed_width = sum(self.ctx.mm(c['width_mm']) for c in columns_config)
        summary_w = self.ctx.mm(10)
        num_summary = len(summary_cols)
        fixed_width += summary_w * num_summary
        
        remaining_w = width - fixed_width
        num_load_cases = len(load_cases)
        lc_w = max(self.ctx.mm(7), remaining_w // num_load_cases) if num_load_cases > 0 else self.ctx.mm(8)
        
        # Header
        self.painter.fillRect(x, y, width, header_h, QColor(PRINT_COLORS["header_bg"]))
        self.painter.setPen(QColor(PRINT_COLORS["text"]))
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_header, QFont.Weight.DemiBold))
        
        cx = x
        for col_cfg in columns_config:
            col_width = self.ctx.mm(col_cfg['width_mm'])
            self.painter.drawText(cx, y, col_width, header_h, Qt.AlignmentFlag.AlignCenter, col_cfg['name'])
            cx += col_width
        
        for lc in load_cases:
            label = str(lc)[:4]
            self.painter.drawText(cx, y, lc_w, header_h, Qt.AlignmentFlag.AlignCenter, label)
            cx += lc_w
        
        for col in summary_cols:
            self.painter.drawText(cx, y, summary_w, header_h, Qt.AlignmentFlag.AlignCenter, col)
            cx += summary_w
        
        # Data rows
        self.painter.setFont(QFont("Segoe UI", self.ctx.font_size_normal))
        for row_i in range(max_rows):
            ry = y + header_h + row_i * row_h
            
            if row_i % 2 == 1:
                self.painter.fillRect(x, ry, width, row_h, QColor(PRINT_COLORS["row_alt"]))
            
            self.painter.setPen(QColor(PRINT_COLORS["text"]))
            cx = x
            
            # Fixed columns
            for col_cfg in columns_config:
                col_width = self.ctx.mm(col_cfg['width_mm'])
                field = col_cfg['field']
                val = str(df[field].iloc[row_i])[:col_cfg.get('max_chars', 6)] if field in df.columns else ""
                self.painter.drawText(cx, ry, col_width, row_h, Qt.AlignmentFlag.AlignCenter, val)
                cx += col_width
            
            # Load case values
            for lc in load_cases:
                val = df[lc].iloc[row_i] if lc in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{val:.{decimals}f}"
                self.painter.drawText(cx, ry, lc_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += lc_w
            
            # Summary columns
            for col in summary_cols:
                val = df[col].iloc[row_i] if col in df.columns else 0
                if pd.isna(val):
                    txt = "-"
                else:
                    txt = f"{val:.{decimals}f}"
                self.painter.drawText(cx, ry, summary_w, row_h, Qt.AlignmentFlag.AlignCenter, txt)
                cx += summary_w
        
        # Border and grid
        total_h = header_h + max_rows * row_h
        actual_w = cx - x  # Actual width used
        
        self.painter.setPen(QPen(QColor(PRINT_COLORS["border"]), 1))
        self.painter.drawRect(x, y, actual_w, total_h)
        
        # Vertical lines
        cx = x
        for col_cfg in columns_config:
            cx += self.ctx.mm(col_cfg['width_mm'])
            self.painter.drawLine(cx, y, cx, y + total_h)
        for _ in load_cases:
            cx += lc_w
            self.painter.drawLine(cx, y, cx, y + total_h)
        for i in range(len(summary_cols) - 1):
            cx += summary_w
            self.painter.drawLine(cx, y, cx, y + total_h)
        
        # Horizontal lines
        for i in range(max_rows + 1):
            ly = y + header_h + i * row_h
            self.painter.drawLine(x, ly, x + actual_w, ly)
        
        return total_h
