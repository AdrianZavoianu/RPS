"""Header and footer rendering for report preview pages."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QColor, QFont, QPixmap, QPen, QImage

from .constants import PRINT_COLORS
from .report_layout import HEADER_HEIGHT, FOOTER_HEIGHT


class ReportHeaderFooter:
    """Renders the header and footer for report pages."""

    def __init__(self, logo: QPixmap | None = None) -> None:
        self._logo = logo if logo is not None else QPixmap()

    @staticmethod
    def load_colorized_logo(logo_path: Path) -> QPixmap:
        """Load logo mask and colorize it for print (dark color on light background)."""
        if not logo_path.exists():
            return QPixmap()

        image = QImage(str(logo_path))
        if image.isNull():
            return QPixmap()

        # Use dark teal color for print
        logo_color = QColor("#1f5c6a")
        image = image.convertToFormat(QImage.Format.Format_ARGB32)

        # Colorize each pixel based on alpha
        for y in range(image.height()):
            for x in range(image.width()):
                pixel = image.pixelColor(x, y)
                if pixel.alpha() > 0:
                    new_color = QColor(logo_color)
                    new_color.setAlpha(pixel.alpha())
                    image.setPixelColor(x, y, new_color)

        return QPixmap.fromImage(image)

    def draw_header(self, painter: QPainter, x: int, y: int, width: int, project_name: str) -> None:
        """Draw compact header with logo and project name."""
        # Logo - 22px height, positioned at top
        logo_h = 22
        if not self._logo.isNull():
            scaled = self._logo.scaledToHeight(logo_h, Qt.TransformationMode.SmoothTransformation)
            painter.drawPixmap(x, y, scaled)
            logo_w = scaled.width()
        else:
            logo_w = 0

        # Project name - aligned with logo
        painter.setPen(QColor(PRINT_COLORS["text"]))
        painter.setFont(QFont("Segoe UI", 9))
        text_rect = QRectF(x + logo_w + 10, y, width - logo_w - 10, logo_h)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, project_name)

        # Separator - small gap below logo
        painter.setPen(QPen(QColor(PRINT_COLORS["grid"]), 1))
        painter.drawLine(x, y + HEADER_HEIGHT, x + width, y + HEADER_HEIGHT)

    def draw_footer(self, painter: QPainter, x: int, y: int, width: int, page_number: int) -> None:
        """Draw the footer with page number."""
        painter.setPen(QColor(PRINT_COLORS["text_muted"]))
        painter.setFont(QFont("Segoe UI", 7))
        painter.drawText(
            x,
            y,
            width,
            FOOTER_HEIGHT,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            f"Page {page_number}",
        )
