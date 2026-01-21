"""Tests for gui.helpers.table_utils."""

import math

import pandas as pd
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

from gui.helpers.table_utils import (
    apply_alternating_row_colors,
    apply_row_style,
    calculate_row_average,
    clear_table,
    compute_average_series,
    create_styled_table_item,
    format_number,
    get_decimals_for_result_type,
    hide_table_widget,
    resize_table_to_content,
    show_table_widget,
)


class DummyWidget:
    def __init__(self):
        self.shown = False
        self.hidden = False
        self.text = None

    def show(self):
        self.shown = True

    def hide(self):
        self.hidden = True

    def setText(self, text):
        self.text = text


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    # Process pending events to prevent hangs
    app.processEvents()
    return app


def test_calculate_row_average_ignores_none_and_nan():
    values = [1.0, None, math.nan, 3.0]
    assert calculate_row_average(values) == 2.0


def test_calculate_row_average_returns_none_for_empty_values():
    assert calculate_row_average([None, math.nan]) is None


def test_compute_average_series_basic():
    df = pd.DataFrame({"A": [1.0, None], "B": [3.0, 4.0], "C": ["x", "y"]})
    series = compute_average_series(df, ["A", "B"])
    assert series is not None
    assert series.tolist() == [2.0, 4.0]


def test_compute_average_series_absolute():
    df = pd.DataFrame({"A": [-1.0, -2.0], "B": [1.0, 2.0]})
    series = compute_average_series(df, ["A", "B"], absolute=True)
    assert series is not None
    assert series.tolist() == [1.0, 2.0]


def test_compute_average_series_returns_none_for_invalid_inputs():
    df = pd.DataFrame({"A": [1.0]})
    assert compute_average_series(df, []) is None
    assert compute_average_series(df, ["Missing"]) is None


def test_compute_average_series_returns_none_when_all_nan():
    df = pd.DataFrame({"A": [math.nan], "B": [math.nan]})
    assert compute_average_series(df, ["A", "B"]) is None


def test_format_number_handles_none_and_signs():
    assert format_number(None) == "-"
    assert format_number(math.nan) == "-"
    assert format_number(1.2345, decimals=2) == "1.23"
    assert format_number(1.2345, decimals=2, show_sign=True) == "+1.23"
    assert format_number(-1.2345, decimals=2, show_sign=True) == "-1.23"


def test_get_decimals_for_result_type_uses_config():
    assert get_decimals_for_result_type("Drifts") == 2
    assert get_decimals_for_result_type("UnknownType") == 4


def test_get_decimals_for_result_type_supports_dict_config(monkeypatch):
    import config.result_config as result_config

    monkeypatch.setattr(result_config, "RESULT_CONFIGS", {"Fake": {"decimals": 3}})
    assert get_decimals_for_result_type("Fake") == 3


def test_create_styled_table_item_sets_properties():
    _ensure_app()
    color = QColor("red")
    item = create_styled_table_item(
        "value",
        color=color,
        alignment=Qt.AlignmentFlag.AlignRight,
        editable=False,
    )

    assert item.text() == "value"
    assert item.textAlignment() == int(Qt.AlignmentFlag.AlignRight)
    assert not (item.flags() & Qt.ItemFlag.ItemIsEditable)
    assert item.foreground().color() == color
    assert getattr(item, "_original_color") == color


def test_resize_table_to_content_sets_fixed_height():
    app = _ensure_app()
    table = QTableWidget(2, 2)
    table.setRowHeight(0, 10)
    table.setRowHeight(1, 20)
    app.processEvents()  # Process after row height changes

    resize_table_to_content(table)
    app.processEvents()  # Process after resize

    # Test that min and max height are equal (fixed height)
    assert table.maximumHeight() == table.minimumHeight()
    # Test that height is at least the sum of row heights
    assert table.maximumHeight() >= 10 + 20


def test_apply_row_style_sets_colors():
    app = _ensure_app()
    table = QTableWidget(2, 2)
    for row in range(2):
        for col in range(2):
            table.setItem(row, col, QTableWidgetItem(f"{row}-{col}"))
    app.processEvents()

    background = QColor("yellow")
    text_color = QColor("blue")
    apply_row_style(table, 0, background, text_color)
    app.processEvents()

    for col in range(2):
        item = table.item(0, col)
        assert item.background().color() == background
        assert item.foreground().color() == text_color


def test_apply_alternating_row_colors_sets_rows():
    app = _ensure_app()
    table = QTableWidget(2, 2)
    for row in range(2):
        for col in range(2):
            table.setItem(row, col, QTableWidgetItem("x"))
    app.processEvents()

    color1 = QColor("red")
    color2 = QColor("green")
    apply_alternating_row_colors(table, color1, color2)
    app.processEvents()

    for col in range(2):
        assert table.item(0, col).background().color() == color1
        assert table.item(1, col).background().color() == color2


def test_clear_table_resets_rows_only():
    app = _ensure_app()
    table = QTableWidget(2, 3)
    table.setItem(0, 0, QTableWidgetItem("x"))
    app.processEvents()

    clear_table(table)
    app.processEvents()

    assert table.rowCount() == 0
    assert table.columnCount() == 3


def test_show_hide_table_widget_updates_label():
    table = DummyWidget()
    label = DummyWidget()
    table._label_widget = label

    show_table_widget(table, label_text="Ready")
    assert table.shown
    assert label.shown
    assert label.text == "Ready"

    hide_table_widget(table)
    assert table.hidden
    assert label.hidden
