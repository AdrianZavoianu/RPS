"""Minimalist dialog for selecting load cases to import."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QCheckBox,
    QWidget,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Set, Dict, List, Tuple

from .styles import COLORS


class LoadCaseItem(QWidget):
    """Modern, minimalist load case item widget."""

    toggled = pyqtSignal(str, bool)  # load_case, checked

    def __init__(self, load_case: str, files: List[str], parent=None):
        super().__init__(parent)
        self.load_case = load_case
        self.files = files
        self._is_checked = True

        self._setup_ui()

    def _setup_ui(self):
        """Create minimalist item layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(16)

        # Checkbox (clear visual design)
        self.checkbox = QCheckBox()
        self.checkbox.setChecked(True)
        self.checkbox.toggled.connect(self._on_toggled)
        self.checkbox.setStyleSheet(f"""
            QCheckBox {{
                spacing: 0px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
                border: 2px solid {COLORS['border']};
                border-radius: 4px;
                background-color: {COLORS['background']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['accent']};
                background-color: {COLORS['card']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: #7fedfa;
                border-color: #7fedfa;
            }}
        """)
        # Add checkmark character using Unicode
        self.checkbox.setText("✓" if self.checkbox.isChecked() else "")
        layout.addWidget(self.checkbox)

        # Load Case Name (50% width - half of previous)
        name_label = QLabel(self.load_case)
        name_label.setStyleSheet(f"""
            font-size: 14px;
            font-weight: 500;
            color: {COLORS['text']};
        """)
        layout.addWidget(name_label, stretch=2)

        # Files (comma-separated, left-aligned)
        files_text = ', '.join(self.files)
        self.files_label = QLabel(files_text)
        self.files_label.setStyleSheet(f"""
            font-size: 13px;
            color: {COLORS['muted']};
        """)
        self.files_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.files_label.setToolTip(files_text)
        layout.addWidget(self.files_label, stretch=3)

        # Style the container
        self.setStyleSheet(f"""
            LoadCaseItem {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {COLORS['border']};
            }}
            LoadCaseItem:hover {{
                background-color: rgba(255, 255, 255, 0.03);
            }}
        """)

    def _on_toggled(self, checked: bool):
        """Handle checkbox toggle."""
        self._is_checked = checked
        self.toggled.emit(self.load_case, checked)

        # Update checkbox appearance - show/hide checkmark
        self.checkbox.setText("✓" if checked else "")

        # Visual feedback - dim text when unchecked
        if not checked:
            # Dim the entire row
            self.setStyleSheet(f"""
                LoadCaseItem {{
                    background-color: rgba(0, 0, 0, 0.2);
                    border: none;
                    border-bottom: 1px solid {COLORS['border']};
                }}
                LoadCaseItem:hover {{
                    background-color: rgba(0, 0, 0, 0.25);
                }}
            """)
            # Dim the files label
            self.files_label.setStyleSheet(f"""
                font-size: 13px;
                color: {COLORS['border']};
            """)
        else:
            # Restore normal appearance
            self.setStyleSheet(f"""
                LoadCaseItem {{
                    background-color: transparent;
                    border: none;
                    border-bottom: 1px solid {COLORS['border']};
                }}
                LoadCaseItem:hover {{
                    background-color: rgba(255, 255, 255, 0.03);
                }}
            """)
            # Restore files label
            self.files_label.setStyleSheet(f"""
                font-size: 13px;
                color: {COLORS['muted']};
            """)

    def is_checked(self) -> bool:
        """Return checkbox state."""
        return self._is_checked

    def set_checked(self, checked: bool):
        """Set checkbox state programmatically."""
        self.checkbox.setChecked(checked)
        # Update checkmark display
        self.checkbox.setText("✓" if checked else "")


class LoadCaseSelectionDialog(QDialog):
    """
    Minimalist dialog for selecting which load cases to import.

    Features:
    - Clean, modern list design (not standard table)
    - Checkbox + Load Case Name (compact) + Files
    - No filtering panel
    - Optimized to show 15+ load cases without scrolling
    """

    def __init__(
        self,
        all_load_cases: Set[str],
        load_case_sources: Dict[str, List[Tuple[str, str]]],
        result_set_name: str,
        parent=None
    ):
        """
        Initialize load case selection dialog.

        Args:
            all_load_cases: Set of all discovered load case names
            load_case_sources: Mapping of load_case → [(file_name, sheet_name), ...]
            result_set_name: Name of result set being imported to
            parent: Parent widget
        """
        super().__init__(parent)
        self.all_load_cases = sorted(all_load_cases)
        self.load_case_sources = load_case_sources
        self.result_set_name = result_set_name
        self.selected_load_cases = set(all_load_cases)  # Default: all selected

        # Track load case items
        self.load_case_items: Dict[str, LoadCaseItem] = {}

        self.setup_ui()
        self._apply_geometry()

    def _apply_geometry(self):
        """Set dialog to match folder import dialog size."""
        width = 1400
        height = 750

        self.resize(width, height)

        # Center on screen
        screen = self.screen().availableGeometry()
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)

    def setup_ui(self):
        """Create minimalist UI."""
        self.setWindowTitle(f"Select Load Cases - {self.result_set_name}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Quick Actions (Select All / None)
        actions_layout = self._create_quick_actions()
        layout.addLayout(actions_layout)

        # Scrollable Load Case List
        scroll_area = self._create_load_case_list()
        layout.addWidget(scroll_area, stretch=1)

        # Dialog Buttons
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

        # Apply global styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QScrollArea {{
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                background-color: {COLORS['card']};
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['card']};
                width: 12px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 6px;
                min-height: 30px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)

    def _create_header(self) -> QVBoxLayout:
        """Create header section."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        title = QLabel("Select Load Cases")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['text']};")
        layout.addWidget(title)

        subtitle = QLabel(
            f"Found {len(self.all_load_cases)} load case(s) across all files. "
            f"Importing into result set \"{self.result_set_name}\""
        )
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS['muted']};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        return layout

    def _create_quick_actions(self) -> QHBoxLayout:
        """Create quick action buttons (Select All / None)."""
        layout = QHBoxLayout()
        layout.setSpacing(12)

        # Select All button
        select_all_btn = QPushButton("Select All")
        select_all_btn.setFixedHeight(32)
        select_all_btn.clicked.connect(self._select_all)
        select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['accent']};
                border: 1px solid {COLORS['accent']};
                border-radius: 4px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: rgba(103, 232, 249, 0.1);
            }}
            QPushButton:pressed {{
                background-color: rgba(103, 232, 249, 0.2);
            }}
        """)
        layout.addWidget(select_all_btn)

        # Select None button
        select_none_btn = QPushButton("Select None")
        select_none_btn.setFixedHeight(32)
        select_none_btn.clicked.connect(self._select_none)
        select_none_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 0 16px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                color: {COLORS['text']};
                border-color: {COLORS['accent']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
        """)
        layout.addWidget(select_none_btn)

        layout.addStretch()

        return layout

    def _create_load_case_list(self) -> QScrollArea:
        """Create scrollable list of load case items."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        # Container for list items
        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)

        # Create item for each load case
        for lc in self.all_load_cases:
            sources = self.load_case_sources.get(lc, [])
            files = sorted(set(f for f, s in sources))

            item = LoadCaseItem(lc, files)
            item.toggled.connect(self._on_item_toggled)
            self.load_case_items[lc] = item
            container_layout.addWidget(item)

        container_layout.addStretch()
        scroll_area.setWidget(container)

        return scroll_area

    def _create_button_layout(self) -> QHBoxLayout:
        """Create dialog button layout."""
        layout = QHBoxLayout()
        layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setMinimumSize(100, 40)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['card']};
                color: {COLORS['muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                color: {COLORS['text']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        self.continue_btn = QPushButton("Continue →")
        self.continue_btn.setMinimumSize(120, 40)
        self.continue_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: #0a0c10;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: #7fedfa;
            }}
            QPushButton:pressed {{
                background-color: #4fc3d0;
            }}
            QPushButton:disabled {{
                background-color: {COLORS['border']};
                color: {COLORS['muted']};
            }}
        """)
        self.continue_btn.clicked.connect(self.accept)
        layout.addWidget(self.continue_btn)

        return layout

    # Event Handlers

    def _on_item_toggled(self, load_case: str, checked: bool):
        """Handle item checkbox toggle."""
        if checked:
            self.selected_load_cases.add(load_case)
        else:
            self.selected_load_cases.discard(load_case)

        # Enable/disable continue button based on selection
        self.continue_btn.setEnabled(len(self.selected_load_cases) > 0)

    def _select_all(self):
        """Select all load cases."""
        for item in self.load_case_items.values():
            item.set_checked(True)

    def _select_none(self):
        """Deselect all load cases."""
        for item in self.load_case_items.values():
            item.set_checked(False)

    def get_selected_load_cases(self) -> Set[str]:
        """Return the set of selected load cases."""
        return self.selected_load_cases
