"""Widget behavior tests."""

from __future__ import annotations

import pyqtgraph as pg

from gui.all_rotations_widget import AllRotationsWidget
from gui.beam_rotations_widget import BeamRotationsWidget
from gui.maxmin_drifts_widget import MaxMinDriftsWidget
from gui.results_plot_widget import ResultsPlotWidget
from gui.results_table_widget import ResultsTableWidget


def test_results_table_widget_load_data(qt_app, sample_result_dataset):
    """ResultsTableWidget loads dataset into table."""
    widget = ResultsTableWidget()
    widget.load_dataset(sample_result_dataset)

    assert widget.table.rowCount() == 2
    assert widget.table.columnCount() == 6
    assert widget.table.item(0, 0).text() == "Level 1"
    assert widget._dataset == sample_result_dataset


def test_results_plot_widget_scaling(qt_app, sample_result_dataset):
    """ResultsPlotWidget sets view ranges based on data."""
    widget = ResultsPlotWidget()
    widget.load_dataset(sample_result_dataset)

    assert len(widget._plot_items) == len(sample_result_dataset.load_case_columns)

    plot = widget._get_plot_from_container(widget.envelope_plot)
    x_range, y_range = plot.getViewBox().viewRange()

    data_vals = sample_result_dataset.data[sample_result_dataset.load_case_columns].values.flatten().tolist()
    min_val = min(data_vals)
    max_val = max(data_vals)

    assert x_range[0] <= min_val
    assert x_range[1] >= max_val
    assert y_range[0] <= 0
    assert y_range[1] >= 1


def test_maxmin_drifts_widget_data_binding(qt_app, sample_maxmin_dataset):
    """MaxMinDriftsWidget binds dataset to plots and tables."""
    widget = MaxMinDriftsWidget()
    widget.load_dataset(sample_maxmin_dataset)

    assert widget.current_base_type == "Drifts"
    assert widget.x_plot_items
    assert widget.x_min_table.rowCount() > 0
    assert widget.x_max_table.rowCount() > 0


def test_all_rotations_widget_histogram(qt_app, rotations_df_max, rotations_df_min):
    """AllRotationsWidget builds histogram items."""
    widget = AllRotationsWidget()
    widget.load_dataset(rotations_df_max, rotations_df_min)

    plot_item = widget.histogram_widget.getPlotItem()
    assert any(isinstance(item, pg.BarGraphItem) for item in plot_item.items)


def test_beam_rotations_widget_tabs(qt_app, beam_rotations_df_max, beam_rotations_df_min):
    """BeamRotationsWidget tab switching updates current mode."""
    widget = BeamRotationsWidget()
    widget.load_dataset(beam_rotations_df_max, beam_rotations_df_min, "Beam-1")

    widget.set_active_tab("plot")
    assert widget.tab_widget.currentIndex() == 1
    assert widget.current_mode == "plot"

    widget.set_active_tab("table")
    assert widget.tab_widget.currentIndex() == 0
    assert widget.current_mode == "table"
