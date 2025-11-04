"""Dialog for resolving load case conflicts across multiple files."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QScrollArea,
    QWidget,
)
from PyQt6.QtCore import Qt
from typing import Dict, List, Optional

from .styles import COLORS


class LoadCaseConflictDialog(QDialog):
    """
    Dialog for resolving load case conflicts when same load case appears in multiple files.

    Displays conflicts and allows user to choose which file's data to use for each
    conflicting load case.
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

        # Initialize default resolution (first file for each conflict)
        for load_case, sheet_files in conflicts.items():
            all_files = set()
            for files in sheet_files.values():
                all_files.update(files)
            self.resolution[load_case] = sorted(all_files)[0]

        self.setup_ui()
        self._apply_screen_geometry()

    def _apply_screen_geometry(self):
        """Set dialog to appropriate size based on content."""
        screen = self.screen().availableGeometry()

        # Base size on number of conflicts
        num_conflicts = len(self.conflicts)
        if num_conflicts <= 3:
            height = min(400, screen.height() * 0.5)
        elif num_conflicts <= 10:
            height = min(600, screen.height() * 0.7)
        else:
            height = int(screen.height() * 0.8)

        width = min(800, int(screen.width() * 0.6))

        self.resize(width, height)

        # Center on screen
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)

    def setup_ui(self):
        """Create dialog UI."""
        self.setWindowTitle("Resolve Load Case Conflicts")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Header
        header_layout = self._create_header()
        layout.addLayout(header_layout)

        # Quick action buttons
        quick_actions = self._create_quick_action_buttons()
        layout.addLayout(quick_actions)

        # Scrollable conflict list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
        """)

        container = QWidget()
        conflict_layout = QVBoxLayout(container)
        conflict_layout.setSpacing(16)

        for load_case in sorted(self.conflicts.keys()):
            sheet_files = self.conflicts[load_case]
            conflict_widget = self._create_conflict_widget(load_case, sheet_files)
            conflict_layout.addWidget(conflict_widget)

        conflict_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll, stretch=1)

        # Dialog buttons
        button_layout = self._create_button_layout()
        layout.addLayout(button_layout)

        # Apply styling
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
            QRadioButton {{
                color: {COLORS['text']};
                font-size: 14px;
                padding: 4px;
            }}
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
            }}
            QRadioButton::indicator:unchecked {{
                border: 2px solid {COLORS['border']};
                border-radius: 9px;
                background-color: {COLORS['card']};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {COLORS['accent']};
                border-radius: 9px;
                background-color: {COLORS['accent']};
            }}
            QRadioButton:hover {{
                color: {COLORS['accent']};
            }}
            QPushButton {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                border-color: {COLORS['accent']};
            }}
            QPushButton:pressed {{
                background-color: {COLORS['border']};
            }}
        """)

    def _create_header(self) -> QVBoxLayout:
        """Create header section."""
        layout = QVBoxLayout()
        layout.setSpacing(8)

        title = QLabel("⚠️ Duplicate Load Cases Detected")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['warning']};")
        layout.addWidget(title)

        subtitle = QLabel(
            f"Found {len(self.conflicts)} duplicate load case(s) across files.\n\n"
            "The same load case appears in multiple Excel files. "
            "Choose which file to import for each duplicate:"
        )
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS['muted']};")
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        return layout

    def _create_quick_action_buttons(self) -> QHBoxLayout:
        """Create quick action buttons for bulk conflict resolution."""
        layout = QHBoxLayout()

        # Get list of unique files involved in conflicts
        all_files = set()
        for sheet_files in self.conflicts.values():
            for files in sheet_files.values():
                all_files.update(files)

        sorted_files = sorted(all_files)

        if len(sorted_files) > 1:
            for file_name in sorted_files:
                btn = QPushButton(f"Use '{file_name}' for All")
                btn.clicked.connect(
                    lambda checked, f=file_name: self._apply_file_to_all(f)
                )
                layout.addWidget(btn)

        layout.addStretch()
        return layout

    def _create_conflict_widget(
        self,
        load_case: str,
        sheet_files: Dict[str, List[str]]
    ) -> QGroupBox:
        """Create widget for one conflicting load case."""
        group = QGroupBox(f"Load Case: {load_case}")
        layout = QVBoxLayout()
        layout.setSpacing(8)

        # Show which sheets have this conflict
        sheets_list = ', '.join(sorted(sheet_files.keys()))
        sheets_label = QLabel(f"Appears in: {sheets_list}")
        sheets_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 13px; font-style: italic;")
        sheets_label.setWordWrap(True)
        layout.addWidget(sheets_label)

        # Radio buttons for file selection
        button_group = QButtonGroup(group)

        # Get unique files (across all sheets)
        all_files = set()
        for files in sheet_files.values():
            all_files.update(files)

        for i, file_name in enumerate(sorted(all_files)):
            radio = QRadioButton(f"Use: {file_name}")
            button_group.addButton(radio)
            layout.addWidget(radio)

            # Set checked state based on current resolution
            if self.resolution.get(load_case) == file_name:
                radio.setChecked(True)

            radio.toggled.connect(
                lambda checked, lc=load_case, f=file_name:
                self._on_selection(lc, f) if checked else None
            )

        # Option to skip this load case entirely
        skip_radio = QRadioButton("Skip this load case (don't import)")
        skip_radio.setStyleSheet(f"color: {COLORS['danger']}; font-weight: bold;")
        button_group.addButton(skip_radio)
        layout.addWidget(skip_radio)

        if self.resolution.get(load_case) is None:
            skip_radio.setChecked(True)

        skip_radio.toggled.connect(
            lambda checked, lc=load_case:
            self._on_selection(lc, None) if checked else None
        )

        group.setLayout(layout)
        return group

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
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
                color: {COLORS['text']};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        ok_btn = QPushButton("Apply Resolution")
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
            QPushButton:pressed {{
                background-color: #4fc3d0;
            }}
        """)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

        return layout

    # Event Handlers

    def _on_selection(self, load_case: str, file_name: Optional[str]):
        """Track user's file selection for each conflict."""
        self.resolution[load_case] = file_name

    def _apply_file_to_all(self, file_name: str):
        """Quick action: use one file for all conflicts."""
        for load_case in self.conflicts.keys():
            self.resolution[load_case] = file_name

        # Update UI - find and check corresponding radio buttons
        # (This would require storing radio button references, simplified for now)
        # User will see the effect after clicking OK

        # Show feedback
        self.findChild(QLabel).setText(
            f"⚠️ Will use '{file_name}' for all {len(self.conflicts)} conflicts"
        )

    # Public API

    def get_resolution(self) -> Dict[str, Optional[str]]:
        """
        Get user's resolution choices.

        Returns:
            Dict mapping load_case → chosen_file (or None to skip)
        """
        return self.resolution.copy()
