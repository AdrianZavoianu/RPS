"""Reusable view combining table and plot for directional results."""

from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from services.result_service import ResultDataset
from ..results_plot_widget import ResultsPlotWidget
from ..results_table_widget import ResultsTableWidget


class StandardResultView(QWidget):
    """Container widget hosting the table/plot pair for a dataset."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.table = ResultsTableWidget()
        self.plot = ResultsPlotWidget()
        self._initial_sizes_set = False

        self._configure_layout()
        self._connect_signals()

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def showEvent(self, event) -> None:
        """Set splitter proportions after widget is shown with actual size."""
        super().showEvent(event)
        if not self._initial_sizes_set:
            # Defer size setting until after layout is complete
            QTimer.singleShot(0, self._apply_splitter_proportions)
            self._initial_sizes_set = True

    def set_dataset(self, dataset: ResultDataset, shorthand_mapping: dict = None) -> None:
        """
        Populate the table and plot with the provided dataset.

        Args:
            dataset: The result dataset to display
            shorthand_mapping: Optional mapping for pushover load case names (full -> shorthand)
        """
        self.table.load_dataset(dataset, shorthand_mapping=shorthand_mapping)
        self.plot.load_dataset(dataset, shorthand_mapping=shorthand_mapping)

        # Force splitter proportions after data is loaded
        QTimer.singleShot(100, self._apply_splitter_proportions)

    def clear(self) -> None:
        """Reset both table and plot."""
        self.table.clear_data()
        self.plot.clear_plots()

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _apply_splitter_proportions(self) -> None:
        """Let table take minimum width needed, give remaining space to plot."""
        # Don't force specific sizes - let stretch factors and minimum widths work together
        # Table has minimum width set to content, stretch factor 1
        # Plot has no minimum, stretch factor 2 (gets twice as much extra space)
        pass

    def _configure_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(12)  # Increased handle width for more spacing
        splitter.setStyleSheet(
            """
            QSplitter {
                padding: 0px;
                margin: 0px;
            }
            QSplitter::handle {
                background-color: transparent;
                margin: 0px 6px;  # Increased margin for more spacing between table and plot
            }
            """
        )

        splitter.addWidget(self.table)
        splitter.addWidget(self.plot)

        # Table: minimum size (content width), stretch factor 1
        # Plot: gets remaining space, stretch factor 2 (prefers to grow more)
        splitter.setStretchFactor(0, 1)  # Table - just what it needs
        splitter.setStretchFactor(1, 2)  # Plot - gets more of the extra space

        layout.addWidget(splitter)

        self._splitter = splitter

    def _connect_signals(self) -> None:
        self.table.selection_changed.connect(self.plot.highlight_load_cases)
        self.table.load_case_hovered.connect(self.plot.hover_load_case)
        self.table.hover_cleared.connect(self.plot.clear_hover)
