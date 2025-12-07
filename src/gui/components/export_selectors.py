"""Reusable selectors for export dialogs."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QCheckBox,
    QScrollArea,
)
from PyQt6.QtCore import Qt

from gui.design_tokens import FormStyles, PALETTE


class ResultTypeSelector(QWidget):
    """Scrollable selector for result types grouped by category."""

    def __init__(self, available_types: dict[str, list[str]], parent=None) -> None:
        super().__init__(parent)
        self.checkboxes: dict[str, QCheckBox] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        types_scroll = QScrollArea()
        types_scroll.setWidgetResizable(True)
        types_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        types_scroll.setStyleSheet(FormStyles.scroll_area())

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(0)

        def add_section(title: str, type_list: list[str]) -> None:
            if not type_list:
                return
            label = QLabel(title)
            label.setStyleSheet(
                f"color: {PALETTE['accent_primary']}; font-size: 13px; font-weight: 600; padding: 6px 0;"
            )
            container_layout.addWidget(label)
            for base_type in type_list:
                checkbox = QCheckBox(base_type)
                checkbox.setStyleSheet(FormStyles.checkbox(indent=False))
                checkbox.setChecked(True)
                self.checkboxes[base_type] = checkbox
                container_layout.addWidget(checkbox)

        add_section("Global Results", available_types.get("global", []))
        add_section("Element Results", available_types.get("element", []))
        add_section("Joint Results", available_types.get("joint", []))
        container_layout.addStretch()

        types_scroll.setWidget(container)
        layout.addWidget(types_scroll)

    def set_all(self, checked: bool) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(checked)

    def selected_base_types(self) -> list[str]:
        return [name for name, checkbox in self.checkboxes.items() if checkbox.isChecked()]


class ResultSetSelector(QWidget):
    """Scrollable selector for result sets."""

    def __init__(self, result_sets: list[tuple[int, str]], parent=None) -> None:
        super().__init__(parent)
        self.checkboxes: dict[int, QCheckBox] = {}
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sets_scroll = QScrollArea()
        sets_scroll.setWidgetResizable(True)
        sets_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sets_scroll.setStyleSheet(FormStyles.scroll_area())

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)
        container_layout.setSpacing(0)

        for rs_id, rs_name in result_sets:
            checkbox = QCheckBox(rs_name)
            checkbox.setStyleSheet(FormStyles.checkbox(indent=False))
            checkbox.setChecked(True)
            self.checkboxes[rs_id] = checkbox
            container_layout.addWidget(checkbox)

        container_layout.addStretch()
        sets_scroll.setWidget(container)
        layout.addWidget(sets_scroll)

    def set_all(self, checked: bool) -> None:
        for checkbox in self.checkboxes.values():
            checkbox.setChecked(checked)

    def selected_ids(self) -> list[int]:
        return [rs_id for rs_id, checkbox in self.checkboxes.items() if checkbox.isChecked()]
