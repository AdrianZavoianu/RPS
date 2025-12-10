"""Sheet-based conflict resolution dialog - clearer and more granular."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QComboBox,
    QScrollArea,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from PyQt6.QtCore import Qt
from typing import Dict, List, Set, Tuple, Optional

from .styles import COLORS


class SheetConflictDialog(QDialog):
    """
    Sheet-based conflict resolution dialog.

    Shows a list of all sheets/result types, indicating which have conflicts.
    For sheets with conflicts, shows which load cases conflict and allows
    choosing source file per conflicting load case.
    """

    def __init__(
        self,
        file_load_cases: Dict[str, Dict[str, List[str]]],
        selected_load_cases: Set[str],
        parent=None
    ):
        """
        Initialize sheet-based conflict dialog.

        Args:
            file_load_cases: {
                "file1.xlsx": {
                    "Story Drifts": ["DES_X", "DES_Y", "MCE_X"],
                    "Story Forces": ["DES_X", "DES_Y"]
                },
                "file2.xlsx": {
                    "Story Drifts": ["DES_X", "SLE_X"],
                    "Story Forces": ["DES_X", "MCE_X"]
                }
            }
            selected_load_cases: Set of load cases user selected to import
            parent: Parent widget
        """
        super().__init__(parent)
        self.file_load_cases = file_load_cases
        self.selected_load_cases = selected_load_cases

        # Analyze conflicts per sheet
        self.sheet_conflicts = self._analyze_sheet_conflicts()

        # Resolution: {sheet_name: {load_case: file_name or None}}
        self.resolution = {}
        for sheet, conflicts in self.sheet_conflicts.items():
            self.resolution[sheet] = {}
            for lc, files in conflicts.items():
                # Default to first file alphabetically
                self.resolution[sheet][lc] = sorted(files)[0]

        self.setup_ui()
        self._apply_geometry()

    def _analyze_sheet_conflicts(self) -> Dict[str, Dict[str, List[str]]]:
        """
        Analyze which sheets have conflicts.

        Returns:
            {
                "Story Drifts": {
                    "DES_X": ["file1.xlsx", "file2.xlsx"],
                    "MCE_X": ["file2.xlsx", "file3.xlsx"]
                },
                "Story Forces": {...}
            }
        """
        sheet_conflicts = {}

        # Get all sheet types
        all_sheets = set()
        for file_data in self.file_load_cases.values():
            all_sheets.update(file_data.keys())

        for sheet_name in all_sheets:
            lc_files = {}  # load_case → list of files

            for file_name, sheets in self.file_load_cases.items():
                if sheet_name not in sheets:
                    continue

                for load_case in sheets[sheet_name]:
                    # Only check selected load cases
                    if load_case not in self.selected_load_cases:
                        continue

                    if load_case not in lc_files:
                        lc_files[load_case] = []
                    lc_files[load_case].append(file_name)

            # Find conflicts (more than one file per load case)
            conflicts = {
                lc: files for lc, files in lc_files.items()
                if len(files) > 1
            }

            if conflicts:
                sheet_conflicts[sheet_name] = conflicts

        return sheet_conflicts

    def _apply_geometry(self):
        """Set dialog size."""
        screen = self.screen().availableGeometry()
        width = min(1000, int(screen.width() * 0.7))
        height = min(800, int(screen.height() * 0.8))

        self.resize(width, height)

        # Center
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)

    def setup_ui(self):
        """Create UI."""
        self.setWindowTitle("Resolve Conflicts by Sheet/Result Type")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header = self._create_header()
        layout.addLayout(header)

        # Sheet list with conflict indicators
        sheet_list = self._create_sheet_list()
        layout.addWidget(sheet_list, stretch=1)

        # Buttons
        buttons = self._create_buttons()
        layout.addLayout(buttons)

        # Styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}
            QGroupBox {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 8px;
                padding: 16px;
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                font-size: 14px;
            }}
            QGroupBox::title {{
                color: {COLORS['text']};
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
                font-weight: bold;
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QComboBox {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 6px 10px;
                font-size: 13px;
                min-width: 200px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {COLORS['text']};
                margin-right: 8px;
            }}
            QTableWidget {{
                background-color: {COLORS['card']};
                gridline-color: #1e2329;
                border: none;
                font-size: 13px;
            }}
            QTableWidget::item {{
                padding: 6px;
                color: {COLORS['text']};
                border: none;
            }}
            QTableWidget::item:alternate {{
                background-color: rgba(255, 255, 255, 0.02);
            }}
            QHeaderView {{
                background-color: {COLORS['hover']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['hover']};
                color: {COLORS['text']};
                padding: 4px 8px;
                border: none;
                border-right: 1px solid #1e2329;
                border-bottom: 1px solid #1e2329;
                font-weight: bold;
                font-size: 13px;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
        """)

    def _create_header(self) -> QVBoxLayout:
        """Create header."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        title = QLabel("⚠️ Resolve Data Conflicts")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['warning']};")
        layout.addWidget(title)

        num_sheets = len(self.sheet_conflicts)
        total_conflicts = sum(len(conflicts) for conflicts in self.sheet_conflicts.values())

        subtitle = QLabel(
            f"Found conflicts in {num_sheets} sheet(s) / result type(s) "
            f"with {total_conflicts} duplicate load case(s).\n\n"
            "Below is a list of all sheets being imported. "
            "For sheets with conflicts, choose which file to use for each conflicting load case."
        )
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS['muted']};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        return layout

    def _create_sheet_list(self) -> QScrollArea:
        """Create scrollable list of sheets with conflict resolution."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(16)

        # Get all sheets
        all_sheets = set()
        for file_data in self.file_load_cases.values():
            all_sheets.update(file_data.keys())

        for sheet_name in sorted(all_sheets):
            if sheet_name in self.sheet_conflicts:
                # Has conflicts - show resolution UI
                widget = self._create_conflict_sheet_widget(sheet_name)
            else:
                # No conflicts - just show indicator
                widget = self._create_no_conflict_sheet_widget(sheet_name)
            layout.addWidget(widget)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _create_no_conflict_sheet_widget(self, sheet_name: str) -> QGroupBox:
        """Create widget for sheet without conflicts."""
        group = QGroupBox(f"✓ {sheet_name}")
        group.setStyleSheet(f"""
            QGroupBox::title {{
                color: {COLORS['success']};
            }}
        """)

        layout = QVBoxLayout()
        label = QLabel("No conflicts - all load cases unique")
        label.setStyleSheet(f"color: {COLORS['muted']}; font-style: italic;")
        layout.addWidget(label)

        group.setLayout(layout)
        return group

    def _create_conflict_sheet_widget(self, sheet_name: str) -> QGroupBox:
        """Create widget for sheet with conflicts."""
        conflicts = self.sheet_conflicts[sheet_name]

        group = QGroupBox(f"⚠ {sheet_name} ({len(conflicts)} conflict(s))")
        group.setStyleSheet(f"""
            QGroupBox::title {{
                color: {COLORS['warning']};
            }}
        """)

        layout = QVBoxLayout()
        layout.setSpacing(12)

        # Info text
        info = QLabel(
            f"{len(conflicts)} load case(s) appear in multiple files. "
            "Choose which file to use for each:"
        )
        info.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Table showing conflicts
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Load Case", "Files with Conflict", "Use File"])
        table.setRowCount(len(conflicts))
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)

        # Column sizing
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        table.setMaximumHeight(min(300, 60 + len(conflicts) * 40))

        for row, (load_case, files) in enumerate(sorted(conflicts.items())):
            # Load case name
            lc_item = QTableWidgetItem(load_case)
            lc_item.setFlags(lc_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row, 0, lc_item)

            # Files
            files_str = ', '.join(sorted(files))
            files_item = QTableWidgetItem(files_str)
            files_item.setFlags(files_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            files_item.setToolTip(files_str)
            table.setItem(row, 1, files_item)

            # Dropdown for file selection
            combo = QComboBox()
            for file_name in sorted(files):
                combo.addItem(file_name)
            combo.addItem("❌ Skip (don't import)")

            # Set current selection
            current = self.resolution[sheet_name].get(load_case)
            if current is None:
                combo.setCurrentText("❌ Skip (don't import)")
            else:
                combo.setCurrentText(current)

            combo.currentTextChanged.connect(
                lambda text, sn=sheet_name, lc=load_case:
                self._on_file_selected(sn, lc, text)
            )

            table.setCellWidget(row, 2, combo)

        layout.addWidget(table)

        group.setLayout(layout)
        return group

    def _create_buttons(self) -> QHBoxLayout:
        """Create dialog buttons."""
        layout = QHBoxLayout()
        layout.addStretch()

        cancel_btn = QPushButton("Cancel Import")
        cancel_btn.setMinimumSize(120, 40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['card']};
                color: {COLORS['muted']};
                border: 1px solid {COLORS['border']};
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                color: {COLORS['text']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Continue Import →")
        ok_btn.setMinimumSize(150, 40)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: #0a0c10;
                border: none;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #7fedfa;
            }}
        """)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

        return layout

    def _on_file_selected(self, sheet_name: str, load_case: str, file_selection: str):
        """Handle file selection for a conflicting load case."""
        if file_selection == "❌ Skip (don't import)":
            self.resolution[sheet_name][load_case] = None
        else:
            self.resolution[sheet_name][load_case] = file_selection

    def get_resolution(self) -> Dict[str, Dict[str, Optional[str]]]:
        """
        Get resolution by sheet and load case.

        Returns:
            {
                "Story Drifts": {
                    "DES_X": "file1.xlsx",
                    "MCE_X": None  # Skip
                },
                "Story Forces": {...}
            }
        """
        return self.resolution.copy()
