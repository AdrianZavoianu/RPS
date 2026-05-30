"""Dialog for resolving conflicts between new import data and existing database data."""

from typing import Dict, Set, Tuple

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QWidget,
    QButtonGroup,
    QRadioButton,
    QGroupBox,
)

from gui.styles import COLORS
from gui.ui_helpers import create_styled_button, create_styled_label


class ExistingDataConflictDialog(QDialog):
    """
    Dialog to resolve conflicts when appending to an existing result set.

    Allows the user to decide, per load case and result type, whether to keep
    existing data or replace it with the new incoming data.
    """

    def __init__(self, conflicts: Dict[str, Set[str]] | Set[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Existing Data Conflict Resolution")
        self.setMinimumSize(720, 560)

        self.conflicts_by_load_case = self._normalize_conflicts(conflicts)
        self.button_groups: Dict[Tuple[str, str], QButtonGroup] = {}
        self.result_types = sorted(
            {
                result_type
                for result_types in self.conflicts_by_load_case.values()
                for result_type in result_types
            }
        )

        self._build_ui()

    @staticmethod
    def _normalize_conflicts(conflicts: Dict[str, Set[str]] | Set[str]) -> Dict[str, Set[str]]:
        if isinstance(conflicts, dict):
            return {load_case: set(result_types) for load_case, result_types in conflicts.items()}
        return {load_case: {"All Result Types"} for load_case in conflicts}

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = create_styled_label("Resolve Existing Data Conflicts", "header")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 20px; font-weight: 600;")
        main_layout.addWidget(header)

        # Description
        result_type_count = sum(
            len(result_types) for result_types in self.conflicts_by_load_case.values()
        )
        desc_text = (
            f"The selected import overlaps {len(self.conflicts_by_load_case)} load case(s) "
            f"and {result_type_count} result type entr{'y' if result_type_count == 1 else 'ies'}. "
            "Choose independently which existing result types to keep and which to replace."
        )
        desc = QLabel(desc_text)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS['muted']}; font-size: 14px; line-height: 1.4;")
        main_layout.addWidget(desc)

        # Warning
        warning_box = QWidget()
        warning_box.setStyleSheet(
            f"""
            background-color: rgba(255, 140, 0, 0.1);
            border: 1px solid #ff8c00;
            border-radius: 6px;
        """
        )
        warning_layout = QHBoxLayout(warning_box)
        warning_icon = QLabel("⚠️")
        warning_label = QLabel(
            "<b>Warning:</b> Selecting 'Replace with New Data' will completely delete "
            "the existing rows for that load case and result type before importing."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet(f"color: {COLORS['text']};")
        warning_layout.addWidget(warning_icon)
        warning_layout.addWidget(warning_label, stretch=1)
        main_layout.addWidget(warning_box)

        # Bulk Actions
        bulk_layout = QHBoxLayout()
        bulk_layout.addWidget(QLabel("Apply to all:"))

        keep_all_btn = create_styled_button("Keep Existing", "ghost", "sm")
        keep_all_btn.clicked.connect(lambda: self._set_all_options("keep"))
        bulk_layout.addWidget(keep_all_btn)

        replace_all_btn = create_styled_button("Replace with New", "ghost", "sm")
        replace_all_btn.clicked.connect(lambda: self._set_all_options("replace"))
        bulk_layout.addWidget(replace_all_btn)

        bulk_layout.addStretch()
        main_layout.addLayout(bulk_layout)

        # Result-type bulk actions
        type_bulk_group = QGroupBox("Apply by result type")
        type_bulk_group.setStyleSheet(
            f"""
            QGroupBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
                color: {COLORS['text']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """
        )
        type_bulk_layout = QVBoxLayout(type_bulk_group)
        type_bulk_layout.setSpacing(6)

        for result_type in self.result_types:
            row = QHBoxLayout()
            row.addWidget(QLabel(result_type), stretch=1)

            keep_type_btn = create_styled_button("Keep all", "ghost", "sm")
            keep_type_btn.clicked.connect(
                lambda _checked=False, rt=result_type: self._set_result_type_options(rt, "keep")
            )
            row.addWidget(keep_type_btn)

            replace_type_btn = create_styled_button("Replace all", "ghost", "sm")
            replace_type_btn.clicked.connect(
                lambda _checked=False, rt=result_type: self._set_result_type_options(rt, "replace")
            )
            row.addWidget(replace_type_btn)
            type_bulk_layout.addLayout(row)

        main_layout.addWidget(type_bulk_group)

        # Scrollable list of conflicts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"""
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['background']};
            }}
        """
        )

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(12)

        # Group box styling
        group_style = f"""
            QGroupBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 12px;
                font-weight: bold;
                color: {COLORS['text']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
            QRadioButton {{
                color: {COLORS['text']};
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 7px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['background']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['accent']};
                border: 2px solid {COLORS['accent']};
            }}
        """

        for lc in sorted(self.conflicts_by_load_case):
            result_types = self.conflicts_by_load_case[lc]
            group = QGroupBox(lc)
            group.setStyleSheet(group_style)
            group_layout = QVBoxLayout(group)

            for result_type in sorted(result_types):
                row = QWidget()
                row_layout = QHBoxLayout(row)
                row_layout.setContentsMargins(0, 0, 0, 0)
                row_layout.setSpacing(12)

                label = QLabel(result_type)
                label.setStyleSheet(f"color: {COLORS['text']}; font-weight: 600;")
                row_layout.addWidget(label, stretch=1)

                btn_group = QButtonGroup(self)
                self.button_groups[(lc, result_type)] = btn_group

                rb_keep = QRadioButton("Keep")
                rb_keep.setProperty("action", "keep")
                rb_keep.setChecked(True)

                rb_replace = QRadioButton("Replace")
                rb_replace.setProperty("action", "replace")

                btn_group.addButton(rb_keep)
                btn_group.addButton(rb_replace)

                row_layout.addWidget(rb_keep)
                row_layout.addWidget(rb_replace)
                group_layout.addWidget(row)

            container_layout.addWidget(group)

        container_layout.addStretch()
        scroll.setWidget(container)
        main_layout.addWidget(scroll, stretch=1)

        # Bottom buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = create_styled_button("Cancel Import", "ghost")
        cancel_btn.clicked.connect(self.reject)

        continue_btn = create_styled_button("Continue Import", "primary")
        continue_btn.clicked.connect(self.accept)

        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(continue_btn)
        main_layout.addLayout(btn_layout)

    def _set_all_options(self, action: str):
        """Set all radio buttons to the specified action."""
        for btn_group in self.button_groups.values():
            for btn in btn_group.buttons():
                if btn.property("action") == action:
                    btn.setChecked(True)
                    break

    def _set_result_type_options(self, result_type: str, action: str):
        """Set all radio buttons for a result type across load cases."""
        for (_load_case, item_result_type), btn_group in self.button_groups.items():
            if item_result_type != result_type:
                continue
            for btn in btn_group.buttons():
                if btn.property("action") == action:
                    btn.setChecked(True)
                    break

    def get_resolution(self) -> Dict[str, Dict[str, str]]:
        """
        Get the user's resolution choices.

        Returns:
            Dict mapping load_case_name -> result type -> action ("keep" or "replace")
        """
        resolution: Dict[str, Dict[str, str]] = {}
        for (lc, result_type), btn_group in self.button_groups.items():
            checked_btn = btn_group.checkedButton()
            if checked_btn:
                resolution.setdefault(lc, {})[result_type] = checked_btn.property("action")
        return resolution
