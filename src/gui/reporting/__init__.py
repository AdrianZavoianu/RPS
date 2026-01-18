"""Reporting package for PDF report generation.

This package provides components for generating PDF reports of analysis results:
- ReportWindow: Dialog window containing the report builder
- ReportView: Main view with checkbox tree and A4 preview
- ReportCheckboxTree: Section selection via checkboxes
- ReportPreviewWidget: A4 page preview display
- PDFGenerator: QPrinter-based PDF export
"""

from .report_view import ReportView
from .report_window import ReportWindow

__all__ = [
    "ReportView",
    "ReportWindow",
]
