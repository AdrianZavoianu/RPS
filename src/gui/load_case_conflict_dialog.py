"""Dialog for resolving load case conflicts across multiple files."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QWidget,
    QSplitter,
)
from PyQt6.QtCore import Qt
from typing import Dict, List, Optional

from .styles import COLORS
from .ui_helpers import create_styled_button, create_styled_label


class LoadCaseConflictDialog(QDialog):
    """
    Dialog for resolving load case conflicts when same load case appears in multiple files.

    Displays conflicts organized by result type (sheet) with clean modern design.
    """

    def __init__(
        self,
        conflicts: Dict[str, Dict[str, List[str]]],
        parent=None
    ):
        """
        Initialize conflict resolution dialog.

        Args:
            conflicts: {
                "DES_X": {
                    "Story Drifts": ["file1.xlsx", "file2.xlsx"],
                    "Story Forces": ["file1.xlsx", "file2.xlsx"]
                },
                ...
            }
            parent: Parent widget
        """
        super().__init__(parent)
        self.conflicts = conflicts
        self.resolution = {}  # load_case → chosen_file (or None to skip)

        # Organize conflicts by sheet (result type)
        self.conflicts_by_sheet = self._organize_by_sheet()

        # Initialize default resolution (first file for each conflict)
        for load_case, sheet_files in conflicts.items():
            all_files = set()
            for files in sheet_files.values():
                all_files.update(files)
            if all_files:
                self.resolution[load_case] = sorted(all_files)[0]

        self._build_ui()

    def _organize_by_sheet(self) -> Dict[str, Dict[str, List[str]]]:
        """Reorganize conflicts by sheet name for grouped display."""
        by_sheet = {}
        for load_case, sheet_files in self.conflicts.items():
            for sheet, files in sheet_files.items():
                if len(files) > 1:  # Only actual conflicts
                    if sheet not in by_sheet:
                        by_sheet[sheet] = {}
                    by_sheet[sheet][load_case] = files
        return by_sheet

    def _build_ui(self) -> None:
        """Create modern dialog UI matching folder import design."""
        self.setWindowTitle("Resolve Load Case Conflicts")
        self.setMinimumSize(750, 700)
        self.resize(850, 750)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 8, 16, 16)
        main_layout.setSpacing(12)

        # Header
        header = create_styled_label("Resolve Load Case Conflicts", "header")
        header.setStyleSheet(f"color: {COLORS['text']}; font-size: 24px; font-weight: 600;")
        main_layout.addWidget(header)

        # Subtitle
        subtitle = QLabel(
            f"Found {len(self.conflicts)} duplicate load case(s). "
            "Select which file to use for each conflict, organized by result type."
        )
        subtitle.setStyleSheet(f"color: {COLORS['muted']}; font-size: 14px;")
        subtitle.setWordWrap(True)
        main_layout.addWidget(subtitle)

        # Main content area - split view
        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        content_splitter.setHandleWidth(1)
        content_splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {COLORS['border']};
            }}
        """)

        # Left: Result type list
        result_types_widget = self._create_result_types_panel()
        content_splitter.addWidget(result_types_widget)

        # Right: Conflict resolution area
        self.conflicts_panel = self._create_conflicts_panel()
        content_splitter.addWidget(self.conflicts_panel)

        # Set initial proportions (30% result types, 70% conflicts)
        content_splitter.setStretchFactor(0, 3)
        content_splitter.setStretchFactor(1, 7)

        main_layout.addWidget(content_splitter, stretch=1)

        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(12)
        button_layout.addStretch()

        cancel_btn = create_styled_button("Cancel", "ghost")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = create_styled_button("Apply Resolution", "primary")
        ok_btn.clicked.connect(self.accept)
        button_layout.addWidget(ok_btn)

        main_layout.addLayout(button_layout)

        # Apply base styling
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['background']};
            }}
        """)

        # Select first result type by default
        if self.conflicts_by_sheet:
            first_sheet = sorted(self.conflicts_by_sheet.keys())[0]
            self._show_conflicts_for_sheet(first_sheet)

    def _create_result_types_panel(self) -> QWidget:
        """Create left panel showing result type list."""
        panel = QGroupBox("Result Types")
        panel.setStyleSheet(self._groupbox_style())
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(4)

        # Create list of result types with conflict count
        for sheet in sorted(self.conflicts_by_sheet.keys()):
            count = len(self.conflicts_by_sheet[sheet])
            btn = create_styled_button(f"{sheet} ({count})", "ghost", "sm")
            btn.setStyleSheet(f"""
                QPushButton {{
                    text-align: left;
                    padding: 8px 12px;
                    font-size: 13px;
                    background-color: transparent;
                    color: {COLORS['text']};
                    border: none;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['card']};
                    color: {COLORS['accent']};
                }}
                QPushButton:pressed {{
                    background-color: {COLORS['hover']};
                }}
            """)
            btn.clicked.connect(lambda checked, s=sheet: self._show_conflicts_for_sheet(s))
            layout.addWidget(btn)

        layout.addStretch()
        return panel

    def _create_conflicts_panel(self) -> QGroupBox:
        """Create right panel for displaying conflicts."""
        panel = QGroupBox("Conflicts")
        panel.setStyleSheet(self._groupbox_style())
        self.conflicts_layout = QVBoxLayout(panel)
        self.conflicts_layout.setContentsMargins(8, 12, 8, 8)
        self.conflicts_layout.setSpacing(12)

        # Placeholder
        placeholder = QLabel("Select a result type to see conflicts")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {COLORS['muted']}; font-size: 14px; padding: 40px;")
        self.conflicts_layout.addWidget(placeholder)

        return panel

    def _show_conflicts_for_sheet(self, sheet: str) -> None:
        """Display conflicts for selected result type."""
        # Clear existing widgets
        while self.conflicts_layout.count() > 0:
            item = self.conflicts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Add title
        title = QLabel(f"{sheet}")
        title.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: 600; padding-bottom: 8px;")
        self.conflicts_layout.addWidget(title)

        # Add scrollable area for conflicts
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        container = QWidget()
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(8)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Add conflict widgets - flatter design
        conflicts = self.conflicts_by_sheet.get(sheet, {})
        for load_case in sorted(conflicts.keys()):
            files = conflicts[load_case]
            conflict_widget = self._create_conflict_widget(load_case, files, sheet)
            container_layout.addWidget(conflict_widget)

        container_layout.addStretch()
        scroll.setWidget(container)
        self.conflicts_layout.addWidget(scroll)

    def _create_conflict_widget(
        self,
        load_case: str,
        files: List[str],
        sheet: str
    ) -> QWidget:
        """Create widget for one conflicting load case."""
        widget = QWidget()
        widget.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
            }}
        """)

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        # Load case label
        label = QLabel(load_case)
        label.setStyleSheet(f"color: {COLORS['text']}; font-weight: 600; font-size: 13px; background: transparent; border: none;")
        layout.addWidget(label)

        # Radio buttons for file selection
        button_group = QButtonGroup(widget)

        for file_name in sorted(files):
            radio = QRadioButton(file_name)
            radio.setStyleSheet(self._radio_style())
            button_group.addButton(radio)
            layout.addWidget(radio)

            # Set checked state based on current resolution
            if self.resolution.get(load_case) == file_name:
                radio.setChecked(True)

            radio.toggled.connect(
                lambda checked, lc=load_case, f=file_name:
                self._on_selection(lc, f) if checked else None
            )

        # Option to skip this load case - subtle styling
        skip_radio = QRadioButton("Skip (don't import)")
        skip_radio.setStyleSheet(f"""
            QRadioButton {{
                color: {COLORS['muted']};
                font-size: 12px;
                padding: 2px 8px;
                font-style: italic;
                background: transparent;
                border: none;
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border: 2px solid {COLORS['border']};
                border-radius: 7px;
                background-color: {COLORS['background']};
            }}
            QRadioButton::indicator:hover {{
                border-color: {COLORS['muted']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['muted']};
                border-color: {COLORS['muted']};
            }}
            QRadioButton:hover {{
                color: {COLORS['text']};
            }}
        """)
        button_group.addButton(skip_radio)
        layout.addWidget(skip_radio)

        if self.resolution.get(load_case) is None:
            skip_radio.setChecked(True)

        skip_radio.toggled.connect(
            lambda checked, lc=load_case:
            self._on_selection(lc, None) if checked else None
        )

        return widget

    @staticmethod
    def _groupbox_style() -> str:
        """Get groupbox styling."""
        return f"""
            QGroupBox {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 12px;
                color: {COLORS['text']};
                font-weight: 600;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 4px;
            }}
        """

    @staticmethod
    def _radio_style() -> str:
        """Get radio button styling."""
        return f"""
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 13px;
                padding: 4px 8px;
                spacing: 8px;
            }}
            QRadioButton::indicator {{
                width: 16px;
                height: 16px;
                border: 2px solid {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['background']};
            }}
            QRadioButton::indicator:hover {{
                border-color: {COLORS['accent']};
                background-color: {COLORS['card']};
            }}
            QRadioButton::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
            QRadioButton:hover {{
                background-color: rgba(255, 255, 255, 0.03);
                border-radius: 4px;
            }}
        """

    def _on_selection(self, load_case: str, file_name: Optional[str]):
        """Track user's file selection for each conflict."""
        self.resolution[load_case] = file_name

    def get_resolution(self) -> Dict[str, Optional[str]]:
        """
        Get user's resolution choices.

        Returns:
            Dict mapping load_case → chosen_file (or None to skip)
        """
        return self.resolution.copy()
