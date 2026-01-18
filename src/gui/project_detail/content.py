"""Content area builder for ProjectDetailWindow."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QHeaderView, QStackedWidget
from PyQt6.QtCore import Qt

from gui.styles import COLORS
from gui.ui_helpers import create_styled_label
from gui.result_views import StandardResultView
from gui.result_views.comparison_view import ComparisonResultView
from gui.result_views.pushover_curve_view import PushoverCurveView
from gui.result_views.time_series_animated_view import TimeSeriesAnimatedView
from gui.maxmin_drifts_widget import MaxMinDriftsWidget
from gui.all_rotations_widget import AllRotationsWidget
from gui.soil_pressure_plot_widget import SoilPressurePlotWidget
from gui.comparison_all_rotations_widget import ComparisonAllRotationsWidget
from gui.comparison_joint_scatter_widget import ComparisonJointScatterWidget
from gui.components.results_table_header import ClickableTableWidget


@dataclass
class ContentArea:
    widget: QWidget
    content_title: QWidget
    standard_view: StandardResultView
    comparison_view: ComparisonResultView
    maxmin_widget: MaxMinDriftsWidget
    all_rotations_widget: AllRotationsWidget
    comparison_all_rotations_widget: ComparisonAllRotationsWidget
    comparison_joint_scatter_widget: ComparisonJointScatterWidget
    soil_pressure_plot_widget: SoilPressurePlotWidget
    beam_rotations_table: QTableWidget
    pushover_curve_view: PushoverCurveView
    time_series_view: TimeSeriesAnimatedView
    # Reporting view placeholder - set by window.py after ReportView is created
    _report_view_placeholder: Optional[QWidget] = None

    def set_report_view(self, report_view: QWidget) -> None:
        """Set the report view widget (called by window after creation)."""
        self._report_view_placeholder = report_view

    def get_report_view(self) -> Optional[QWidget]:
        """Get the report view widget."""
        return self._report_view_placeholder

    def hide_all(self) -> None:
        """Hide all views in the content area."""
        self.standard_view.hide()
        self.comparison_view.hide()
        self.maxmin_widget.hide()
        self.all_rotations_widget.hide()
        self.comparison_all_rotations_widget.hide()
        self.comparison_joint_scatter_widget.hide()
        self.beam_rotations_table.hide()
        self.soil_pressure_plot_widget.hide()
        self.pushover_curve_view.hide()
        self.time_series_view.hide()

    def show_standard(self) -> None:
        self.hide_all()
        self.standard_view.show()

    def show_comparison(self) -> None:
        self.hide_all()
        self.comparison_view.show()

    def show_maxmin(self) -> None:
        self.hide_all()
        self.maxmin_widget.show()

    def show_all_rotations(self) -> None:
        self.hide_all()
        self.all_rotations_widget.show()

    def show_comparison_rotations(self) -> None:
        self.hide_all()
        self.comparison_all_rotations_widget.show()

    def show_comparison_scatter(self) -> None:
        self.hide_all()
        self.comparison_joint_scatter_widget.show()

    def show_beam_table(self) -> None:
        self.hide_all()
        self.beam_rotations_table.show()

    def show_soil_pressure(self) -> None:
        self.hide_all()
        self.soil_pressure_plot_widget.show()

    def show_pushover_curve(self) -> None:
        self.hide_all()
        self.pushover_curve_view.show()

    def show_time_series(self) -> None:
        self.hide_all()
        self.time_series_view.show()


def build_content_area() -> ContentArea:
    """Build the content area widget and return references to its views."""
    widget = QWidget()
    layout = QVBoxLayout(widget)
    layout.setContentsMargins(6, 4, 6, 4)
    layout.setSpacing(4)

    # Content header with result type title
    content_header = QWidget()
    content_header.setFixedHeight(32)
    content_header_layout = QHBoxLayout(content_header)
    content_header_layout.setContentsMargins(4, 2, 4, 2)
    content_header_layout.setSpacing(8)

    content_title = create_styled_label("Select a result type", "header")
    content_title.setStyleSheet("font-size: 18px; font-weight: 600;")
    content_header_layout.addWidget(content_title)
    content_header_layout.addStretch()

    layout.addWidget(content_header, stretch=0)
    layout.addSpacing(8)

    standard_view = StandardResultView()
    standard_view.clear()
    layout.addWidget(standard_view, stretch=1)

    comparison_view = ComparisonResultView()
    comparison_view.hide()
    layout.addWidget(comparison_view, stretch=1)

    maxmin_widget = MaxMinDriftsWidget()
    maxmin_widget.hide()
    layout.addWidget(maxmin_widget)

    all_rotations_widget = AllRotationsWidget()
    all_rotations_widget.hide()
    layout.addWidget(all_rotations_widget)

    comparison_all_rotations_widget = ComparisonAllRotationsWidget()
    comparison_all_rotations_widget.hide()
    layout.addWidget(comparison_all_rotations_widget)

    comparison_joint_scatter_widget = ComparisonJointScatterWidget()
    comparison_joint_scatter_widget.hide()
    layout.addWidget(comparison_joint_scatter_widget)

    soil_pressure_plot_widget = SoilPressurePlotWidget()
    soil_pressure_plot_widget.hide()
    layout.addWidget(soil_pressure_plot_widget)

    beam_rotations_table = ClickableTableWidget()
    beam_rotations_table.setStyleSheet(
        f"""
            QTableWidget {{
                background-color: {COLORS['background']};
                border: none;
                gridline-color: #1e2329;
                color: {COLORS['text']};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QHeaderView {{
                background-color: {COLORS['card']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['accent']};
                padding: 4px 4px;
                border: none;
                border-right: 1px solid #1e2329;
                border-bottom: 1px solid #1e2329;
                font-weight: 600;
                text-align: center;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
            QHeaderView::section:hover {{
                background-color: #1f2937;
                color: #67e8f9;
            }}
        """
    )
    beam_rotations_table.verticalHeader().setVisible(False)
    beam_rotations_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
    beam_rotations_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    beam_rotations_table.setSizeAdjustPolicy(QTableWidget.SizeAdjustPolicy.AdjustToContents)
    header = beam_rotations_table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    header.setStretchLastSection(False)
    beam_rotations_table.hide()
    layout.addWidget(beam_rotations_table)

    pushover_curve_view = PushoverCurveView()
    pushover_curve_view.hide()
    layout.addWidget(pushover_curve_view)

    time_series_view = TimeSeriesAnimatedView()
    time_series_view.hide()
    layout.addWidget(time_series_view)

    return ContentArea(
        widget=widget,
        content_title=content_title,
        standard_view=standard_view,
        comparison_view=comparison_view,
        maxmin_widget=maxmin_widget,
        all_rotations_widget=all_rotations_widget,
        comparison_all_rotations_widget=comparison_all_rotations_widget,
        comparison_joint_scatter_widget=comparison_joint_scatter_widget,
        soil_pressure_plot_widget=soil_pressure_plot_widget,
        beam_rotations_table=beam_rotations_table,
        pushover_curve_view=pushover_curve_view,
        time_series_view=time_series_view,
    )
