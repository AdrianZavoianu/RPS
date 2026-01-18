"""Main reporting view with checkbox tree and A4 preview."""

from __future__ import annotations

import logging
from typing import Optional
from dataclasses import dataclass

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QComboBox,
    QPushButton,
    QScrollArea,
    QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer

from gui.styles import COLORS
from gui.ui_helpers import create_styled_label, create_styled_button
from services.project_runtime import ProjectRuntime

logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """Data container for a report section."""
    title: str              # "Story Drifts - X Direction"
    result_type: str        # "Drifts"
    direction: str          # "X"
    result_set_id: int
    category: str = "Global"  # "Global", "Element", "Joint"
    element_id: Optional[int] = None
    analysis_context: str = "NLTHA"  # "NLTHA" or "Pushover"


class ReportView(QWidget):
    """Main reporting interface with checkbox tree and A4 preview.

    Layout:
    ┌─────────────────────────────────────────────┐
    │ Result Set: [DES ▼]  [Print] [Export PDF]   │ Settings bar
    ├──────────────┬──────────────────────────────┤
    │ ☑ Global     │                              │
    │   ☑ Drifts   │     A4 Preview Area          │
    │     ☑ X      │     (scrollable)             │
    │     ☑ Y      │                              │
    │   ☐ Forces   │                              │
    │              │                              │
    └──────────────┴──────────────────────────────┘
         30%                    70%
    """

    section_selection_changed = pyqtSignal()

    def __init__(self, runtime: ProjectRuntime, parent: Optional[QWidget] = None, analysis_context: str = 'NLTHA'):
        super().__init__(parent)
        self.runtime = runtime
        self.result_service = runtime.result_service
        self.project_name = runtime.project.name
        self.project_id = runtime.project.id
        self.analysis_context = analysis_context  # 'NLTHA' or 'Pushover'

        self._selected_result_set_id: Optional[int] = None
        self._cached_sections: dict = {}  # Cache fetched datasets

        # Debounce timer for preview updates (300ms delay)
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(300)
        self._update_timer.timeout.connect(self._do_update_preview)

        self.setMinimumSize(800, 600)
        self._setup_ui()
        self._load_result_sets()

    def _setup_ui(self) -> None:
        """Build the reporting view UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Settings bar at top
        settings_bar = self._create_settings_bar()
        layout.addWidget(settings_bar)

        # Main splitter: checkbox tree (left) | preview area (right)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setObjectName("reportSplitter")
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet(f"""
            QSplitter#reportSplitter {{
                background-color: {COLORS['background']};
            }}
            QSplitter#reportSplitter::handle {{
                background-color: {COLORS['border']};
            }}
        """)

        # Left: Checkbox tree container
        tree_container = self._create_tree_container()
        splitter.addWidget(tree_container)

        # Right: Preview area
        preview_container = self._create_preview_container()
        splitter.addWidget(preview_container)

        # Set splitter proportions (30% tree, 70% preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([280, 800])

        layout.addWidget(splitter, stretch=1)

    def _create_settings_bar(self) -> QWidget:
        """Create the top settings bar with result set dropdown and buttons."""
        bar = QWidget()
        bar.setObjectName("settingsBar")
        bar.setFixedHeight(48)
        bar.setStyleSheet(f"""
            QWidget#settingsBar {{
                background-color: {COLORS['card']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Result set label and dropdown
        rs_label = create_styled_label("Result Set:", "muted")
        layout.addWidget(rs_label)

        self.result_set_combo = QComboBox()
        self.result_set_combo.setMinimumWidth(150)
        self.result_set_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['background']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                padding: 4px 8px;
                min-height: 24px;
            }}
            QComboBox:hover {{
                border-color: {COLORS['accent']};
            }}
            QComboBox::drop-down {{
                border: none;
                width: 20px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                selection-background-color: {COLORS['accent']};
            }}
        """)
        self.result_set_combo.currentIndexChanged.connect(self._on_result_set_changed)
        layout.addWidget(self.result_set_combo)

        layout.addStretch()

        # Select All / Clear buttons
        select_all_btn = create_styled_button("Select All", variant="ghost")
        select_all_btn.clicked.connect(self._on_select_all)
        layout.addWidget(select_all_btn)

        clear_btn = create_styled_button("Clear", variant="ghost")
        clear_btn.clicked.connect(self._on_clear_selection)
        layout.addWidget(clear_btn)

        # Separator
        sep = QWidget()
        sep.setFixedWidth(1)
        sep.setFixedHeight(24)
        sep.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(sep)

        # Print and Export buttons
        print_btn = create_styled_button("Print", variant="secondary")
        print_btn.setToolTip("Open print dialog")
        print_btn.clicked.connect(self._on_print_clicked)
        layout.addWidget(print_btn)

        export_btn = create_styled_button("Export PDF", variant="primary")
        export_btn.setToolTip("Export report to PDF file")
        export_btn.clicked.connect(self._on_export_clicked)
        layout.addWidget(export_btn)

        return bar

    def _create_tree_container(self) -> QWidget:
        """Create the left panel with checkbox tree."""
        container = QWidget()
        container.setObjectName("treeContainer")
        container.setMinimumWidth(200)
        container.setStyleSheet(f"QWidget#treeContainer {{ background-color: {COLORS['background']}; }}")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Header
        header = create_styled_label("Report Sections", "section")
        layout.addWidget(header)

        # Checkbox tree for section selection
        from .report_checkbox_tree import ReportCheckboxTree
        self.checkbox_tree = ReportCheckboxTree()
        self.checkbox_tree.selection_changed.connect(self._on_tree_selection_changed)
        layout.addWidget(self.checkbox_tree, stretch=1)

        return container

    def _create_preview_container(self) -> QWidget:
        """Create the right panel with A4 preview area."""
        container = QWidget()
        container.setObjectName("previewContainer")
        container.setMinimumWidth(400)
        container.setStyleSheet(f"QWidget#previewContainer {{ background-color: {COLORS['background']}; }}")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(8)

        # Header
        header = create_styled_label("Report Preview", "section")
        layout.addWidget(header)

        # Placeholder for preview widget (will be replaced with ReportPreviewWidget)
        from .report_preview_widget import ReportPreviewWidget
        self.preview_widget = ReportPreviewWidget(self.project_name)
        layout.addWidget(self.preview_widget, stretch=1)

        return container

    def _load_result_sets(self) -> None:
        """Load result sets into the dropdown based on analysis context."""
        result_sets = self.runtime.repos.result_set.get_by_project(self.project_id)
        logger.info(f"Reporting: Found {len(result_sets)} result sets for project {self.project_id}")

        # Filter result sets based on analysis context
        if self.analysis_context == 'Pushover':
            filtered_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) == 'Pushover']
            logger.info(f"Reporting: Filtered to {len(filtered_sets)} Pushover result sets")
        else:
            # NLTHA context - exclude Pushover result sets
            filtered_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) != 'Pushover']
            logger.info(f"Reporting: Filtered to {len(filtered_sets)} NLTHA result sets")

        self.result_set_combo.clear()
        for rs in filtered_sets:
            logger.info(f"Reporting: Adding result set '{rs.name}' (id={rs.id})")
            self.result_set_combo.addItem(rs.name, rs.id)

        if filtered_sets:
            self._selected_result_set_id = filtered_sets[0].id
            self._refresh_tree()
        else:
            logger.warning(f"Reporting: No {self.analysis_context} result sets found")

    def _on_result_set_changed(self, index: int) -> None:
        """Handle result set dropdown change."""
        if index < 0:
            return
        self._selected_result_set_id = self.result_set_combo.currentData()
        self._refresh_tree()

    def _refresh_tree(self) -> None:
        """Refresh the checkbox tree for the selected result set."""
        if self._selected_result_set_id is None:
            return
        self.checkbox_tree.populate_from_result_set(
            self._selected_result_set_id,
            self.runtime.session
        )
        self._update_preview()

    def _on_tree_selection_changed(self) -> None:
        """Handle checkbox tree selection changes."""
        self._update_preview()
        self.section_selection_changed.emit()

    def _update_preview(self) -> None:
        """Schedule a debounced preview update."""
        # Restart the timer on each call - only triggers after user stops clicking
        self._update_timer.start()

    def _do_update_preview(self) -> None:
        """Actually update the preview (called after debounce delay)."""
        if self._selected_result_set_id is None:
            return

        sections = self.checkbox_tree.get_selected_sections(self._selected_result_set_id, self.analysis_context)

        # Fetch datasets for each section (with caching)
        for section in sections:
            if section.category == "Global":
                cache_key = ("Global", section.result_type, section.direction, section.result_set_id)

                # Check local cache first
                if cache_key in self._cached_sections:
                    section.dataset = self._cached_sections[cache_key]
                else:
                    # Fetch and cache
                    dataset = self.result_service.get_standard_dataset(
                        section.result_type,
                        section.direction,
                        section.result_set_id
                    )
                    self._cached_sections[cache_key] = dataset
                    section.dataset = dataset

            elif section.category == "Element":
                cache_key = ("Element", section.result_type, section.result_set_id)

                if cache_key in self._cached_sections:
                    section.element_data = self._cached_sections[cache_key]
                else:
                    # Fetch element rotation data based on type
                    if section.result_type == "BeamRotations":
                        element_data = self._fetch_beam_rotation_data(section.result_set_id)
                    elif section.result_type == "ColumnRotations":
                        element_data = self._fetch_column_rotation_data(section.result_set_id)
                    else:
                        element_data = None
                    self._cached_sections[cache_key] = element_data
                    section.element_data = element_data

            elif section.category == "Joint":
                cache_key = ("Joint", section.result_type, section.result_set_id)

                if cache_key in self._cached_sections:
                    section.joint_data = self._cached_sections[cache_key]
                else:
                    # Fetch joint data based on type
                    if section.result_type == "SoilPressures_Min":
                        joint_data = self._fetch_soil_pressure_data(section.result_set_id)
                    else:
                        joint_data = None
                    self._cached_sections[cache_key] = joint_data
                    section.joint_data = joint_data

        self.preview_widget.set_sections(sections)

    def _fetch_beam_rotation_data(self, result_set_id: int) -> Optional[dict]:
        """Fetch beam rotation data for reporting.

        Returns dict with:
        - 'all_data': DataFrame with all beam rotations (for table - wide format)
        - 'top_10': DataFrame with top 10 by absolute average (for table)
        - 'load_cases': List of load case column names
        - 'stories': List of story names in display order (bottom to top)
        - 'plot_data_max': List of (story, rotation) tuples for Max step type
        - 'plot_data_min': List of (story, rotation) tuples for Min step type
        """
        import pandas as pd
        from sqlalchemy import or_
        from database.models import BeamRotation, LoadCase, Story, Element, ResultCategory

        # Build base query
        base_query = (
            self.runtime.session.query(BeamRotation, LoadCase, Story, Element)
            .join(LoadCase, BeamRotation.load_case_id == LoadCase.id)
            .join(Story, BeamRotation.story_id == Story.id)
            .join(Element, BeamRotation.element_id == Element.id)
        )

        # Apply context-appropriate filtering
        if self.analysis_context == 'Pushover':
            # Pushover: Use outerjoin to include records without result_category
            records = (
                base_query
                .outerjoin(ResultCategory, BeamRotation.result_category_id == ResultCategory.id)
                .filter(
                    Story.project_id == self.project_id,
                    or_(
                        ResultCategory.result_set_id == result_set_id,
                        ResultCategory.result_set_id.is_(None),
                    ),
                )
                .order_by(Story.sort_order, Element.name, LoadCase.name)
                .all()
            )
        else:
            # NLTHA: Use strict filtering to avoid including unrelated data
            records = (
                base_query
                .join(ResultCategory, BeamRotation.result_category_id == ResultCategory.id)
                .filter(
                    Story.project_id == self.project_id,
                    ResultCategory.result_set_id == result_set_id,
                )
                .order_by(Story.sort_order, Element.name, LoadCase.name)
                .all()
            )

        if not records:
            return None

        # Build wide-format data for table AND collect plot data (Max/Min separately)
        load_cases = sorted({lc.name for _, lc, _, _ in records})
        data_dict = {}
        plot_data_max = []  # (story_name, story_order, rotation_value)
        plot_data_min = []

        for rotation, load_case, story, element in records:
            # Get step_type to separate Max and Min
            step_type = getattr(rotation, 'step_type', None)
            rotation_value = rotation.r3_plastic * 100.0

            # Collect plot data based on step_type
            if step_type == "Max":
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value))
            elif step_type == "Min":
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value))
            else:
                # Legacy data without step_type - include in both
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value))
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value))

            # Build wide-format table data (use step_type as part of key to avoid overwriting)
            key = (story.name, element.name, rotation.generated_hinge or "", rotation.rel_dist or 0.0, step_type or "")
            entry = data_dict.setdefault(
                key,
                {
                    "Story": story.name,
                    "StoryOrder": story.sort_order or 0,
                    "Frame/Wall": element.name,
                    "Hinge": rotation.hinge or "",
                },
            )
            entry[load_case.name] = rotation_value

        df = pd.DataFrame(list(data_dict.values()))
        if df.empty:
            return None

        # Identify load case columns
        meta_cols = ["Story", "StoryOrder", "Frame/Wall", "Hinge"]
        load_case_cols = [c for c in df.columns if c not in meta_cols]

        if not load_case_cols:
            return None

        # Add summary columns (skip Avg for Pushover - not meaningful)
        numeric_df = df[load_case_cols].apply(pd.to_numeric, errors='coerce')
        if self.analysis_context != 'Pushover':
            df["Avg"] = numeric_df.mean(axis=1)
        df["Max"] = numeric_df.max(axis=1)
        df["Min"] = numeric_df.min(axis=1)

        # Calculate absolute average for sorting
        df["_abs_avg"] = numeric_df.abs().mean(axis=1)

        # Get top 10 by absolute average
        top_10_df = df.nlargest(10, "_abs_avg").copy()

        # Drop helper column
        df = df.drop(columns=["_abs_avg"])
        top_10_df = top_10_df.drop(columns=["_abs_avg"])

        # Get stories in display order (bottom to top for plot)
        stories_df = df[['Story', 'StoryOrder']].drop_duplicates().sort_values('StoryOrder')
        story_names = list(reversed(stories_df['Story'].tolist()))  # Reverse for bottom-to-top

        return {
            "all_data": df,
            "top_10": top_10_df,
            "load_cases": load_case_cols,
            "stories": story_names,
            "plot_data_max": plot_data_max,
            "plot_data_min": plot_data_min,
        }

    def _fetch_column_rotation_data(self, result_set_id: int) -> Optional[dict]:
        """Fetch column rotation data for reporting.

        Returns dict with:
        - 'all_data': DataFrame with all column rotations (for table - wide format)
        - 'top_10': DataFrame with top 10 by absolute average (for table)
        - 'load_cases': List of load case column names
        - 'stories': List of story names in display order (bottom to top)
        - 'plot_data_max': List of (story, rotation) tuples for Max step type
        - 'plot_data_min': List of (story, rotation) tuples for Min step type
        """
        import pandas as pd
        from sqlalchemy import or_
        from database.models import ColumnRotation, LoadCase, Story, Element, ResultCategory

        # Build base query
        base_query = (
            self.runtime.session.query(ColumnRotation, LoadCase, Story, Element)
            .join(LoadCase, ColumnRotation.load_case_id == LoadCase.id)
            .join(Story, ColumnRotation.story_id == Story.id)
            .join(Element, ColumnRotation.element_id == Element.id)
        )

        # Apply context-appropriate filtering
        if self.analysis_context == 'Pushover':
            # Pushover: Use outerjoin to include records without result_category
            records = (
                base_query
                .outerjoin(ResultCategory, ColumnRotation.result_category_id == ResultCategory.id)
                .filter(
                    Story.project_id == self.project_id,
                    or_(
                        ResultCategory.result_set_id == result_set_id,
                        ResultCategory.result_set_id.is_(None),
                    ),
                )
                .order_by(Story.sort_order, Element.name, LoadCase.name)
                .all()
            )
        else:
            # NLTHA: Use strict filtering to avoid including unrelated data
            records = (
                base_query
                .join(ResultCategory, ColumnRotation.result_category_id == ResultCategory.id)
                .filter(
                    Story.project_id == self.project_id,
                    ResultCategory.result_set_id == result_set_id,
                )
                .order_by(Story.sort_order, Element.name, LoadCase.name)
                .all()
            )

        if not records:
            return None

        # Build wide-format data for table AND collect plot data (Max/Min separately)
        load_cases = sorted({lc.name for _, lc, _, _ in records})
        data_dict = {}
        plot_data_max = []  # (story_name, story_order, rotation_value)
        plot_data_min = []

        for rotation, load_case, story, element in records:
            # Column rotations use max_rotation/min_rotation fields for NLTHA envelope data
            direction = rotation.direction or "R3"  # R2 or R3

            # For NLTHA envelope data, use max_rotation/min_rotation
            # For pushover/single case, use rotation field
            if rotation.max_rotation is not None:
                rotation_value_max = rotation.max_rotation * 100.0
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value_max))
            if rotation.min_rotation is not None:
                rotation_value_min = rotation.min_rotation * 100.0
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value_min))

            # If neither max nor min, use rotation field for both
            if rotation.max_rotation is None and rotation.min_rotation is None and rotation.rotation is not None:
                rotation_value = rotation.rotation * 100.0
                plot_data_max.append((story.name, story.sort_order or 0, rotation_value))
                plot_data_min.append((story.name, story.sort_order or 0, rotation_value))

            # Build wide-format table data
            # Use max_rotation for table display (absolute max)
            table_value = None
            if rotation.max_rotation is not None and rotation.min_rotation is not None:
                # Use the one with larger absolute value
                if abs(rotation.max_rotation) >= abs(rotation.min_rotation):
                    table_value = rotation.max_rotation * 100.0
                else:
                    table_value = rotation.min_rotation * 100.0
            elif rotation.max_rotation is not None:
                table_value = rotation.max_rotation * 100.0
            elif rotation.min_rotation is not None:
                table_value = rotation.min_rotation * 100.0
            elif rotation.rotation is not None:
                table_value = rotation.rotation * 100.0

            if table_value is not None:
                key = (story.name, element.name, direction)
                entry = data_dict.setdefault(
                    key,
                    {
                        "Story": story.name,
                        "StoryOrder": story.sort_order or 0,
                        "Column": element.name,
                        "Dir": direction,
                    },
                )
                entry[load_case.name] = table_value

        df = pd.DataFrame(list(data_dict.values()))
        if df.empty:
            return None

        # Identify load case columns
        meta_cols = ["Story", "StoryOrder", "Column", "Dir"]
        load_case_cols = [c for c in df.columns if c not in meta_cols]

        if not load_case_cols:
            return None

        # Add summary columns (skip Avg for Pushover - not meaningful)
        numeric_df = df[load_case_cols].apply(pd.to_numeric, errors='coerce')
        if self.analysis_context != 'Pushover':
            df["Avg"] = numeric_df.mean(axis=1)
        df["Max"] = numeric_df.max(axis=1)
        df["Min"] = numeric_df.min(axis=1)

        # Calculate absolute average for sorting
        df["_abs_avg"] = numeric_df.abs().mean(axis=1)

        # Get top 10 by absolute average
        top_10_df = df.nlargest(10, "_abs_avg").copy()

        # Drop helper column
        df = df.drop(columns=["_abs_avg"])
        top_10_df = top_10_df.drop(columns=["_abs_avg"])

        # Get stories in display order (bottom to top for plot)
        stories_df = df[['Story', 'StoryOrder']].drop_duplicates().sort_values('StoryOrder')
        story_names = list(reversed(stories_df['Story'].tolist()))  # Reverse for bottom-to-top

        return {
            "all_data": df,
            "top_10": top_10_df,
            "load_cases": load_case_cols,
            "stories": story_names,
            "plot_data_max": plot_data_max,
            "plot_data_min": plot_data_min,
        }

    def _fetch_soil_pressure_data(self, result_set_id: int) -> Optional[dict]:
        """Fetch soil pressure data for reporting.

        Returns dict with:
        - 'all_data': DataFrame with all soil pressures (wide format with load cases as columns)
        - 'top_10': DataFrame with top 10 by absolute average (highest critical values)
        - 'load_cases': List of load case column names
        - 'plot_data': List of (load_case_index, pressure_value) for scatter plot
        """
        import pandas as pd
        import numpy as np

        # Use the result service to get joint dataset
        is_pushover = self.analysis_context == 'Pushover'
        dataset = self.result_service.get_joint_dataset("SoilPressures_Min", result_set_id, is_pushover=is_pushover)

        if dataset is None or dataset.data is None or dataset.data.empty:
            return None

        df = dataset.data.copy()
        load_case_cols = list(dataset.load_case_columns)

        if not load_case_cols:
            return None

        # The DataFrame has columns: Shell Object, Unique Name, [load case columns], Avg, Max, Min
        # We need to prepare data for:
        # 1. Table with top 10 highest avg pressures
        # 2. Scatter plot showing all pressures per load case

        # Calculate absolute average for sorting (soil pressures are negative, so we use abs)
        numeric_df = df[load_case_cols].apply(pd.to_numeric, errors='coerce')

        # Add Avg, Max, Min if not already present (skip Avg for Pushover)
        if "Avg" not in df.columns and self.analysis_context != 'Pushover':
            df["Avg"] = numeric_df.abs().mean(axis=1)
        if "Max" not in df.columns:
            df["Max"] = numeric_df.abs().max(axis=1)
        if "Min" not in df.columns:
            df["Min"] = numeric_df.abs().min(axis=1)

        # Calculate absolute average for sorting
        df["_abs_avg"] = numeric_df.abs().mean(axis=1)

        # Get top 10 by absolute average (highest pressure values = most critical)
        top_10_df = df.nlargest(10, "_abs_avg").copy()

        # Drop helper column
        df = df.drop(columns=["_abs_avg"])
        top_10_df = top_10_df.drop(columns=["_abs_avg"])

        # Prepare scatter plot data: (load_case_index, pressure_value)
        # Use absolute values for plot (soil pressures are negative)
        plot_data = []
        for lc_idx, lc in enumerate(load_case_cols):
            if lc in numeric_df.columns:
                values = numeric_df[lc].dropna().abs().values
                for v in values:
                    plot_data.append((lc_idx, v))

        return {
            "all_data": df,
            "top_10": top_10_df,
            "load_cases": load_case_cols,
            "plot_data": plot_data,
        }

    def _on_select_all(self) -> None:
        """Select all items in the checkbox tree."""
        self.checkbox_tree.select_all()

    def _on_clear_selection(self) -> None:
        """Clear all selections in the checkbox tree."""
        self.checkbox_tree.clear_selection()

    def _on_print_clicked(self) -> None:
        """Open print dialog."""
        from .pdf_generator import PDFGenerator

        sections = self._get_sections_with_data()
        if not sections:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "No Sections Selected",
                "Please select at least one section to print."
            )
            return

        generator = PDFGenerator(self.project_name)
        generator.show_print_dialog(sections, self)

    def _on_export_clicked(self) -> None:
        """Export to PDF file."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        from datetime import datetime

        sections = self._get_sections_with_data()
        if not sections:
            QMessageBox.warning(
                self,
                "No Sections Selected",
                "Please select at least one section to export."
            )
            return

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"{self.project_name}_Report_{timestamp}.pdf"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report to PDF",
            default_name,
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        from .pdf_generator import PDFGenerator
        generator = PDFGenerator(self.project_name)

        try:
            generator.generate(sections, file_path)
            QMessageBox.information(
                self,
                "Export Complete",
                f"Report exported successfully to:\n{file_path}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Failed",
                f"Failed to export report:\n{str(e)}"
            )

    def _get_sections_with_data(self) -> list[ReportSection]:
        """Get selected sections with their datasets loaded."""
        if self._selected_result_set_id is None:
            return []

        sections = self.checkbox_tree.get_selected_sections(self._selected_result_set_id, self.analysis_context)

        # Load datasets for each section
        for section in sections:
            if section.category == "Global":
                dataset = self.result_service.get_standard_dataset(
                    section.result_type,
                    section.direction,
                    section.result_set_id
                )
                section.dataset = dataset
            elif section.category == "Element":
                # Fetch element rotation data based on type
                if section.result_type == "BeamRotations":
                    element_data = self._fetch_beam_rotation_data(section.result_set_id)
                elif section.result_type == "ColumnRotations":
                    element_data = self._fetch_column_rotation_data(section.result_set_id)
                else:
                    element_data = None
                section.element_data = element_data

            elif section.category == "Joint":
                # Fetch joint data based on type
                if section.result_type == "SoilPressures_Min":
                    joint_data = self._fetch_soil_pressure_data(section.result_set_id)
                else:
                    joint_data = None
                section.joint_data = joint_data

        # Filter out sections without data
        def has_data(s):
            if s.category == "Global":
                return hasattr(s, 'dataset') and s.dataset is not None
            elif s.category == "Element":
                return hasattr(s, 'element_data') and s.element_data is not None
            elif s.category == "Joint":
                return hasattr(s, 'joint_data') and s.joint_data is not None
            return False

        return [s for s in sections if has_data(s)]

    def set_result_set(self, result_set_id: int) -> None:
        """Set the active result set programmatically."""
        index = self.result_set_combo.findData(result_set_id)
        if index >= 0:
            self.result_set_combo.setCurrentIndex(index)
