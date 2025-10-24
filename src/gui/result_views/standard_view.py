"""Reusable view combining table and plot for directional results."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from processing.result_service import ResultDataset
from ..results_plot_widget import ResultsPlotWidget
from ..results_table_widget import ResultsTableWidget


class StandardResultView(QWidget):
    """Container widget hosting the table/plot pair for a dataset."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.table = ResultsTableWidget()
        self.plot = ResultsPlotWidget()

        self._configure_layout()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def set_dataset(self, dataset: ResultDataset) -> None:
        """Populate the table and plot with the provided dataset."""
        self.table.load_dataset(dataset)
        self.plot.load_dataset(dataset)

    def clear(self) -> None:
        """Reset both table and plot."""
        self.table.clear_data()
        self.plot.clear_plots()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _configure_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet(
            """
            QSplitter {
                padding: 0px;
                margin: 0px;
            }
            QSplitter::handle {
                background-color: transparent;
                margin: 0px 4px;
            }
            """
        )

        splitter.addWidget(self.table)
        splitter.addWidget(self.plot)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        self._splitter = splitter

    def _connect_signals(self) -> None:
        self.table.selection_changed.connect(self.plot.highlight_load_cases)
        self.table.load_case_hovered.connect(self.plot.hover_load_case)
        self.table.hover_cleared.connect(self.plot.clear_hover)
