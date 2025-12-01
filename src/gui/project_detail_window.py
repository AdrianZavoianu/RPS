"""Project detail window - shows results browser and data visualization."""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QDialog,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pandas as pd

from .results_tree_browser import ResultsTreeBrowser
from .maxmin_drifts_widget import MaxMinDriftsWidget
from .all_rotations_widget import AllRotationsWidget
from .soil_pressure_plot_widget import SoilPressurePlotWidget
from .comparison_all_rotations_widget import ComparisonAllRotationsWidget
from .comparison_joint_scatter_widget import ComparisonJointScatterWidget
from .result_views import StandardResultView
from .result_views.comparison_view import ComparisonResultView
from .result_views.pushover_curve_view import PushoverCurveView
from .ui_helpers import create_styled_button, create_styled_label
from .window_utils import enable_dark_title_bar
from .styles import COLORS
from services.project_runtime import ProjectRuntime
from utils.color_utils import get_gradient_color
from config.result_config import RESULT_CONFIGS, format_result_type_with_unit


class ProjectDetailWindow(QMainWindow):
    """Project detail window with results browser, table, and plots."""

    def __init__(self, runtime: ProjectRuntime, parent=None):
        super().__init__(parent)
        self.runtime = runtime
        self.context = runtime.context
        self.session = runtime.session

        # Repositories (shared via runtime helper)
        self.project_repo = runtime.repos.project
        self.result_set_repo = runtime.repos.result_set
        self.cache_repo = runtime.repos.cache
        self.story_repo = runtime.repos.story
        self.load_case_repo = runtime.repos.load_case
        self.abs_maxmin_repo = runtime.repos.abs_maxmin
        self.element_repo = runtime.repos.element
        self.element_cache_repo = runtime.repos.element_cache
        self.joint_cache_repo = runtime.repos.joint_cache

        self.project = runtime.project
        self.project_id = self.project.id
        self.project_name = self.project.name
        self.result_service = runtime.result_service

        # Current selection
        self.current_result_type = None  # 'Drifts', 'Accelerations', 'Forces', 'WallShears'
        self.current_result_set_id = None
        self.current_direction = 'X'  # Default to X direction
        self.current_element_id = 0  # 0 = global results, >0 = specific element

        # Active context (NLTHA or Pushover)
        self.active_context = "NLTHA"  # Default to NLTHA

        # Cache for pushover load case mappings (result_set_id -> mapping dict)
        self._pushover_mappings = {}

        self.setup_ui()
        self.load_project_data()
        enable_dark_title_bar(self)

    def showEvent(self, event):
        """Ensure the window opens maximized for better workspace visibility."""
        super().showEvent(event)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle(f"RPS - {self.project_name}")
        self.setMinimumSize(1400, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header bar
        header = self._create_header()
        layout.addWidget(header)

        # Main content splitter (browser | table + plots)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left: Results browser
        self.browser = ResultsTreeBrowser(self.project_id)
        self.browser.selection_changed.connect(self.on_browser_selection_changed)
        self.browser.comparison_selected.connect(self.on_comparison_selected)
        self.browser.comparison_element_selected.connect(self.on_comparison_element_selected)
        splitter.addWidget(self.browser)

        # Right: Content area (table + plots)
        content_widget = self._create_content_area()
        splitter.addWidget(content_widget)

        # Set splitter proportions (browser 200px, rest for content)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([200, 1200])  # Browser 200px default

        layout.addWidget(splitter)

        # Status bar
        self.statusBar().showMessage(f"Project: {self.project_name}")

    def _create_header(self) -> QWidget:
        """Create header bar with contextual tabs and controls."""
        header = QWidget()
        header.setObjectName("projectHeader")
        header.setFixedHeight(64)
        header.setStyleSheet(f"""
            QWidget#projectHeader {{
                background-color: {COLORS['card']};
                border-bottom: 1px solid {COLORS['border']};
                min-height: 64px;
                max-height: 64px;
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Project name (left side, distinctive)
        title = create_styled_label(f"▸ {self.project_name}", "header")
        layout.addWidget(title)

        # Stretch to push all buttons to the right
        layout.addStretch()

        # Tab buttons (NLTHA / Pushover)
        self.nltha_tab = self._create_tab_button("NLTHA", active=True)
        self.pushover_tab = self._create_tab_button("Pushover", active=False)
        self.nltha_tab.clicked.connect(lambda: self._switch_context("NLTHA"))
        self.pushover_tab.clicked.connect(lambda: self._switch_context("Pushover"))

        layout.addWidget(self.nltha_tab)
        layout.addWidget(self.pushover_tab)

        # Separator
        layout.addSpacing(12)
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(separator)
        layout.addSpacing(12)

        # NLTHA-specific buttons
        self.nltha_buttons = []

        load_data_btn = create_styled_button("Load NLTHA Data", "primary", "sm")
        load_data_btn.setToolTip("Import NLTHA data from folder")
        load_data_btn.clicked.connect(self.load_data_from_folder)
        layout.addWidget(load_data_btn)
        self.nltha_buttons.append(load_data_btn)

        create_comparison_btn = create_styled_button("Create Comparison", "primary", "sm")
        create_comparison_btn.setToolTip("Create a new comparison set")
        create_comparison_btn.clicked.connect(self.create_comparison_set)
        layout.addWidget(create_comparison_btn)
        self.nltha_buttons.append(create_comparison_btn)

        nltha_export_btn = create_styled_button("Export Results", "secondary", "sm")
        nltha_export_btn.setToolTip("Export NLTHA results to file")
        nltha_export_btn.clicked.connect(self.export_results)
        layout.addWidget(nltha_export_btn)
        self.nltha_buttons.append(nltha_export_btn)

        # Pushover-specific buttons
        self.pushover_buttons = []

        load_pushover_btn = create_styled_button("Load Pushover Curves", "primary", "sm")
        load_pushover_btn.setToolTip("Import pushover capacity curves")
        load_pushover_btn.clicked.connect(self.load_pushover_curves)
        layout.addWidget(load_pushover_btn)
        load_pushover_btn.hide()  # Hidden initially
        self.pushover_buttons.append(load_pushover_btn)

        load_results_btn = create_styled_button("Load Results", "primary", "sm")
        load_results_btn.setToolTip("Import pushover global results (drifts, displacements, forces)")
        load_results_btn.clicked.connect(self.load_pushover_results)
        layout.addWidget(load_results_btn)
        load_results_btn.hide()  # Hidden initially
        self.pushover_buttons.append(load_results_btn)

        pushover_export_btn = create_styled_button("Export Results", "secondary", "sm")
        pushover_export_btn.setToolTip("Export pushover results to file")
        pushover_export_btn.clicked.connect(self.export_results)
        layout.addWidget(pushover_export_btn)
        pushover_export_btn.hide()  # Hidden initially
        self.pushover_buttons.append(pushover_export_btn)

        # Separator before common buttons
        layout.addSpacing(12)
        separator2 = QWidget()
        separator2.setFixedWidth(1)
        separator2.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(separator2)
        layout.addSpacing(12)

        # Common buttons (always visible)
        export_project_btn = create_styled_button("Export Project", "secondary", "sm")
        export_project_btn.setToolTip("Export complete project to Excel")
        export_project_btn.clicked.connect(self.export_project_excel)
        layout.addWidget(export_project_btn)

        close_btn = create_styled_button("Close", "ghost", "sm")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return header

    def _create_tab_button(self, text: str, active: bool = False) -> QPushButton:
        """Create a tab button with custom styling."""
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setFixedHeight(40)
        btn.setMinimumWidth(100)

        # Custom tab styling
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['muted'] if not active else COLORS['accent']};
                border: none;
                border-bottom: 2px solid {'transparent' if not active else COLORS['accent']};
                padding: 8px 16px;
                font-size: 14px;
                font-weight: {'normal' if not active else 'bold'};
            }}
            QPushButton:hover {{
                color: {COLORS['text']};
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QPushButton:checked {{
                color: {COLORS['accent']};
                border-bottom: 2px solid {COLORS['accent']};
                font-weight: bold;
            }}
        """)

        return btn

    def _switch_context(self, context: str):
        """Switch between NLTHA and Pushover contexts."""
        print(f"[DEBUG] _switch_context called: '{self.active_context}' -> '{context}'")

        if self.active_context == context:
            print(f"[DEBUG] Context already '{context}', no change")
            return  # Already active

        self.active_context = context
        print(f"[DEBUG] Context switched to '{context}'")

        # Update tab button states
        if context == "NLTHA":
            self.nltha_tab.setChecked(True)
            self.pushover_tab.setChecked(False)
            # Show NLTHA buttons, hide Pushover buttons
            for btn in self.nltha_buttons:
                btn.show()
            for btn in self.pushover_buttons:
                btn.hide()
        else:  # Pushover
            self.nltha_tab.setChecked(False)
            self.pushover_tab.setChecked(True)
            # Show Pushover buttons, hide NLTHA buttons
            for btn in self.nltha_buttons:
                btn.hide()
            for btn in self.pushover_buttons:
                btn.show()

        # Update tab button styling
        self._update_tab_styling()

        # Optionally filter browser tree by context (future enhancement)
        # self.browser.filter_by_context(context)

    def _update_tab_styling(self):
        """Update tab button styling based on active state."""
        for tab_btn in [self.nltha_tab, self.pushover_tab]:
            is_active = tab_btn.isChecked()
            tab_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['accent'] if is_active else COLORS['muted']};
                    border: none;
                    border-bottom: 2px solid {COLORS['accent'] if is_active else 'transparent'};
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: {'bold' if is_active else 'normal'};
                }}
                QPushButton:hover {{
                    color: {COLORS['text']};
                    background-color: rgba(255, 255, 255, 0.05);
                }}
                QPushButton:checked {{
                    color: {COLORS['accent']};
                    border-bottom: 2px solid {COLORS['accent']};
                    font-weight: bold;
                }}
            """)

    def _create_content_area(self) -> QWidget:
        """Create content area with table and plots."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 8, 16, 8)  # More left/right margin so borders are visible
        layout.setSpacing(8)

        # Content header with result type title
        content_header = QWidget()
        content_header.setFixedHeight(48)
        content_header_layout = QHBoxLayout(content_header)
        content_header_layout.setContentsMargins(8, 4, 8, 4)
        content_header_layout.setSpacing(12)

        self.content_title = create_styled_label("Select a result type", "subheader")
        content_header_layout.addWidget(self.content_title)

        content_header_layout.addStretch()

        layout.addWidget(content_header, stretch=0)

        # Standard result view (table + plot)
        self.standard_view = StandardResultView()
        self.standard_view.clear()
        layout.addWidget(self.standard_view, stretch=1)

        # Comparison result view (initially hidden)
        self.comparison_view = ComparisonResultView()
        self.comparison_view.hide()
        layout.addWidget(self.comparison_view, stretch=1)

        # Max/Min Drifts widget (initially hidden)
        self.maxmin_widget = MaxMinDriftsWidget()
        self.maxmin_widget.hide()
        layout.addWidget(self.maxmin_widget)

        # All Rotations widget (initially hidden)
        self.all_rotations_widget = AllRotationsWidget()
        self.all_rotations_widget.hide()
        layout.addWidget(self.all_rotations_widget)

        # Comparison All Rotations widget (initially hidden)
        self.comparison_all_rotations_widget = ComparisonAllRotationsWidget()
        self.comparison_all_rotations_widget.hide()
        layout.addWidget(self.comparison_all_rotations_widget)

        # Comparison Joint Scatter widget (initially hidden) - for soil pressures and vertical displacements
        self.comparison_joint_scatter_widget = ComparisonJointScatterWidget()
        self.comparison_joint_scatter_widget.hide()
        layout.addWidget(self.comparison_joint_scatter_widget)

        # Soil Pressure Plot widget (initially hidden)
        self.soil_pressure_plot_widget = SoilPressurePlotWidget()
        self.soil_pressure_plot_widget.hide()
        layout.addWidget(self.soil_pressure_plot_widget)

        # Beam Rotations table widget (initially hidden)
        self.beam_rotations_table = QTableWidget()
        self.beam_rotations_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['background']};
                border: 1px solid {COLORS['border']};
                border-radius: 6px;
                gridline-color: {COLORS['border']};
                color: {COLORS['text']};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['accent']};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {COLORS['border']};
                font-weight: 600;
                text-align: center;
            }}
            QHeaderView::section:hover {{
                background-color: #1f2937;
                color: #67e8f9;
            }}
        """)
        # Hide vertical header and configure horizontal header
        self.beam_rotations_table.verticalHeader().setVisible(False)
        self.beam_rotations_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beam_rotations_table.hide()
        layout.addWidget(self.beam_rotations_table)

        # Pushover Curve View widget (initially hidden)
        self.pushover_curve_view = PushoverCurveView()
        self.pushover_curve_view.hide()
        layout.addWidget(self.pushover_curve_view)

        return widget

    def create_comparison_set(self):
        """Open dialog to create a new comparison set."""
        from .comparison_set_dialog import ComparisonSetDialog
        from database.repository import ComparisonSetRepository
        from PyQt6.QtWidgets import QMessageBox

        # Get all result sets for the project
        result_sets = self.result_set_repo.get_by_project(self.project_id)

        if len(result_sets) < 2:
            QMessageBox.warning(
                self,
                "Insufficient Result Sets",
                "You need at least 2 result sets to create a comparison.\n\n"
                "Please import more result sets first."
            )
            return

        # Open dialog with blur overlay
        from gui.ui_helpers import show_dialog_with_blur
        dialog = ComparisonSetDialog(self.project_id, result_sets, self.session, self)
        if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
            data = dialog.get_comparison_data()

            # Check for duplicate name
            comparison_repo = ComparisonSetRepository(self.session)
            if comparison_repo.check_duplicate(self.project_id, data['name']):
                QMessageBox.warning(
                    self,
                    "Duplicate Name",
                    f"A comparison set named '{data['name']}' already exists.\n"
                    "Please choose a different name."
                )
                return

            # Create comparison set in database
            try:
                comparison_set = comparison_repo.create(
                    project_id=self.project_id,
                    name=data['name'],
                    result_set_ids=data['result_set_ids'],
                    result_types=data['result_types'],
                    description=data['description']
                )

                QMessageBox.information(
                    self,
                    "Comparison Set Created",
                    f"Comparison set '{data['name']}' has been created successfully!\n\n"
                    "Reload the project data to see it in the browser."
                )

                # Reload project data to show new comparison set
                self.load_project_data()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create comparison set:\n{str(e)}"
                )

    def _get_available_result_types(self, result_sets):
        """Check which result types have data for each result set.

        Returns:
            Dict mapping result_set_id to set of available result types
        """
        from database.models import GlobalResultsCache, ElementResultsCache, JointResultsCache

        available_types = {}

        for result_set in result_sets:
            types_for_set = set()

            # Check GlobalResultsCache for global result types
            global_types = (
                self.session.query(GlobalResultsCache.result_type)
                .filter(GlobalResultsCache.result_set_id == result_set.id)
                .distinct()
                .all()
            )
            for (result_type,) in global_types:
                types_for_set.add(result_type)

            # Check ElementResultsCache for element result types
            element_types = (
                self.session.query(ElementResultsCache.result_type)
                .filter(ElementResultsCache.result_set_id == result_set.id)
                .distinct()
                .all()
            )
            for (result_type,) in element_types:
                # Extract base type (e.g., "WallShears_V2" → "WallShears")
                base_type = result_type.split('_')[0]
                types_for_set.add(base_type)

            # Check JointResultsCache for joint result types (soil pressures, etc.)
            joint_types = (
                self.session.query(JointResultsCache.result_type)
                .filter(JointResultsCache.result_set_id == result_set.id)
                .distinct()
                .all()
            )
            for (result_type,) in joint_types:
                types_for_set.add(result_type)
                # Add base type (e.g., JointDisplacements_Ux -> JointDisplacements) so
                # sections that gate on the base name still render when only directional
                # variants are present (pushover joints).
                base_type = result_type.split('_')[0]
                types_for_set.add(base_type)

            available_types[result_set.id] = types_for_set

        return available_types

    def load_project_data(self):
        """Load project data and populate browser."""
        from database.repository import ComparisonSetRepository, PushoverCaseRepository

        self.session.expire_all()
        self.result_service.invalidate_all()
        try:
            # Get result sets
            result_sets = self.result_set_repo.get_by_project(self.project_id)

            # Set default result set for export functionality (use first result set)
            if result_sets and not self.current_result_set_id:
                self.current_result_set_id = result_sets[0].id

            # Get stories
            stories = self.story_repo.get_by_project(self.project_id)

            # Get elements (walls, columns, beams, etc.)
            elements = self.element_repo.get_by_project(self.project_id)

            # Get comparison sets
            comparison_set_repo = ComparisonSetRepository(self.session)
            comparison_sets = comparison_set_repo.get_by_project(self.project_id)

            # Get pushover cases grouped by result set and create load case mappings
            pushover_repo = PushoverCaseRepository(self.session)
            pushover_cases = {}
            print(f"[DEBUG] Checking {len(result_sets)} result sets for pushover analysis type")
            for rs in result_sets:
                analysis_type = getattr(rs, 'analysis_type', None)
                print(f"[DEBUG] Result set {rs.id} ({rs.name}): analysis_type={analysis_type}")
                if analysis_type == 'Pushover':
                    cases = pushover_repo.get_by_result_set(rs.id)
                    print(f"[DEBUG] Found {len(cases) if cases else 0} pushover cases for result set {rs.id}")
                    if cases:
                        pushover_cases[rs.id] = cases
                        # Create mapping for this result set based on actual load cases
                        self._create_pushover_mapping(rs.id)

            # Check which result types have data for each result set
            available_result_types = self._get_available_result_types(result_sets)

            # Populate browser
            self.browser.populate_tree(result_sets, stories, elements, available_result_types, comparison_sets, pushover_cases)

            self.statusBar().showMessage(
                f"Loaded project: {self.project_name} "
                f"({len(stories)} stories, {len(result_sets)} result sets, {len(comparison_sets)} comparisons, {len(elements)} elements)"
            )
        except Exception as e:
            self.statusBar().showMessage(f"Error loading project data: {str(e)}")

    def _create_pushover_mapping(self, result_set_id: int):
        """
        Create and cache the shorthand mapping for a pushover result set.
        Maps full load case names to shorthand (e.g., "Push-Mod-X+Ecc+" -> "Px1").
        """
        from utils.pushover_utils import create_pushover_shorthand_mapping
        import re

        print(f"[DEBUG] _create_pushover_mapping called for result_set_id={result_set_id}")

        # Query all distinct load cases for this result set from cache
        load_cases_with_suffix = self.cache_repo.get_distinct_load_cases(self.project_id, result_set_id)
        print(f"[DEBUG] Retrieved {len(load_cases_with_suffix)} load cases from cache")
        if load_cases_with_suffix:
            print(f"[DEBUG] First 3 load cases: {load_cases_with_suffix[:3]}")

        if load_cases_with_suffix:
            # Strip direction suffixes (_UX, _UY, _VX, _VY, etc.) from cache keys
            # Cache stores: "Push-Mod-X+Ecc+_UX" but dataset has: "Push-Mod-X+Ecc+"
            load_cases = []
            seen = set()
            for case_name in load_cases_with_suffix:
                # Remove suffix like _UX, _UY, _VX, _VY, etc.
                base_name = re.sub(r'_(UX|UY|UZ|VX|VY|VZ)$', '', case_name)
                if base_name not in seen:
                    load_cases.append(base_name)
                    seen.add(base_name)

            print(f"[DEBUG] Stripped suffixes: {len(load_cases_with_suffix)} -> {len(load_cases)} unique load cases")
            print(f"[DEBUG] Sample before: {load_cases_with_suffix[0]} -> after: {load_cases[0]}")

            # Create mapping for all load cases (both X and Y directions)
            mapping = create_pushover_shorthand_mapping(load_cases, direction=None)

            # Add underscore variants to handle both hyphen and underscore formats
            # Global results use hyphens (Push-Mod-X+Ecc+), element results use underscores (Push_Mod_X+Ecc+)
            # BUT: Only replace word separators, NOT +/- signs before/after Ecc
            extended_mapping = dict(mapping)
            for full_name, shorthand in list(mapping.items()):
                # Replace hyphens with underscores EXCEPT when adjacent to Ecc
                # Pattern: Push-Mod-X-Ecc- should become Push_Mod_X-Ecc- (not Push_Mod_X_Ecc_)
                # Use regex: replace - that is NOT preceded by Ecc and NOT followed by Ecc
                underscore_variant = re.sub(r'(?<!Ecc)-(?!Ecc)', '_', full_name)
                if underscore_variant != full_name:
                    extended_mapping[underscore_variant] = shorthand
                    print(f"[DEBUG] Added underscore variant: '{full_name}' -> '{underscore_variant}' = '{shorthand}'")

            self._pushover_mappings[result_set_id] = extended_mapping
            print(f"[DEBUG] Created pushover mapping for result set {result_set_id}: {len(mapping)} base + {len(extended_mapping) - len(mapping)} underscore variants = {len(extended_mapping)} total")
            print(f"[DEBUG] Sample entries (first 2 hyphen, first 2 underscore):")
            items = list(extended_mapping.items())
            hyphen_items = [item for item in items if '-' in item[0]][:2]
            underscore_items = [item for item in items if '_' in item[0]][:2]
            print(f"[DEBUG]   Hyphen: {hyphen_items}")
            print(f"[DEBUG]   Underscore: {underscore_items}")
        else:
            print(f"[DEBUG] No load cases found for result set {result_set_id} - no mapping created")

    def _get_pushover_mapping(self, result_set_id: int) -> dict:
        """Get the cached pushover mapping for a result set."""
        mapping = self._pushover_mappings.get(result_set_id, {})
        print(f"[DEBUG] _get_pushover_mapping({result_set_id}): returning {len(mapping)} entries")
        print(f"[DEBUG] Current cache state: {[(k, len(v)) for k, v in self._pushover_mappings.items()]}")
        # Return a COPY to prevent external modifications from affecting the cache
        return dict(mapping)

    def _hide_all_views(self):
        """Hide all content views - call this before showing a specific view."""
        self.standard_view.hide()
        self.comparison_view.hide()
        self.maxmin_widget.hide()
        self.all_rotations_widget.hide()
        self.comparison_all_rotations_widget.hide()
        self.comparison_joint_scatter_widget.hide()
        self.beam_rotations_table.hide()
        self.soil_pressure_plot_widget.hide()
        self.pushover_curve_view.hide()

    def on_browser_selection_changed(self, result_set_id: int, category: str, result_type: str, direction: str, element_id: int = 0):
        """Handle browser selection changes.

        Args:
            result_set_id: ID of the selected result set
            category: Category name (e.g., "Envelopes", "Pushover")
            result_type: Result type (e.g., "Drifts", "Accelerations", "WallShears", "Curves")
            direction: Direction ('X', 'Y', 'V22', 'V33', case name for pushover)
            element_id: Element ID for element-specific results (0 for global results, -1 for all elements)
        """
        print(f"[DEBUG] on_browser_selection_changed: category={category}, result_type={result_type}, result_set_id={result_set_id}")

        # Automatically switch context based on result set's analysis type
        # Check if this result set is a pushover result set
        result_set = self.result_set_repo.get_by_id(result_set_id) if result_set_id else None
        if result_set:
            analysis_type = getattr(result_set, 'analysis_type', None)
            print(f"[DEBUG] Result set {result_set_id} analysis_type: {analysis_type}")

            if analysis_type == "Pushover":
                print(f"[DEBUG] Result set is Pushover, auto-switching to Pushover context")
                self._switch_context("Pushover")
            else:
                print(f"[DEBUG] Result set is not Pushover, auto-switching to NLTHA context")
                self._switch_context("NLTHA")
        elif category == "Pushover":
            # Fallback: if no result_set_id but category is Pushover
            print(f"[DEBUG] No result set but category is Pushover, switching to Pushover context")
            self._switch_context("Pushover")
        else:
            print(f"[DEBUG] Defaulting to NLTHA context")
            self._switch_context("NLTHA")

        self.current_result_set_id = result_set_id
        self.current_result_type = result_type
        self.current_direction = direction
        self.current_element_id = element_id

        # Special handling for pushover curves
        if category == "Pushover" and result_type == "Curves":
            case_name = direction  # Direction field contains the case name
            self.load_pushover_curve(case_name)
            return

        # Special handling for all pushover curves
        if category == "Pushover" and result_type == "AllCurves":
            curve_direction = direction  # Direction field contains X or Y
            self.load_all_pushover_curves(curve_direction)
            return

        if result_type and result_set_id:
            if result_type == "AllQuadRotations":
                # All rotations scatter plot view (both Max and Min)
                self._hide_all_views()
                self.all_rotations_widget.show()
                self.load_all_rotations(result_set_id)
            elif result_type == "AllColumnRotations":
                # All column rotations scatter plot view (both Max and Min)
                self._hide_all_views()
                self.all_rotations_widget.show()
                self.load_all_column_rotations(result_set_id)
            elif result_type == "AllBeamRotations":
                # All beam rotations scatter plot view (both Max and Min)
                self._hide_all_views()
                self.all_rotations_widget.show()
                self.load_all_beam_rotations(result_set_id)
            elif result_type == "BeamRotationsTable":
                # Beam rotations wide-format table view (all beams, all load cases)
                self._hide_all_views()
                self.beam_rotations_table.show()
                self.load_beam_rotations_table(result_set_id)
            elif result_type.startswith("MaxMin") and element_id > 0:
                # Element-specific max/min results (pier shears max/min)
                self._hide_all_views()
                self.maxmin_widget.show()
                base_type = self._extract_base_result_type(result_type)
                self.load_element_maxmin_dataset(element_id, result_set_id, base_type)
            elif result_type.startswith("MaxMin"):
                # Global max/min results (story drifts, forces, etc.)
                self._hide_all_views()
                self.maxmin_widget.show()
                base_type = self._extract_base_result_type(result_type)
                self.load_maxmin_dataset(result_set_id, base_type)
            elif result_type == "AllSoilPressures":
                # All soil pressures bar chart view
                self._hide_all_views()
                self.soil_pressure_plot_widget.show()
                self.load_all_soil_pressures(result_set_id)
            elif result_type == "SoilPressuresTable":
                # Soil pressures wide-format table view (all elements, all load cases)
                self._hide_all_views()
                self.beam_rotations_table.show()
                self.load_soil_pressures_table(result_set_id)
            elif result_type == "AllVerticalDisplacements":
                # All vertical displacements scatter plot view
                self._hide_all_views()
                self.soil_pressure_plot_widget.show()
                self.load_all_vertical_displacements(result_set_id)
            elif result_type == "VerticalDisplacementsTable":
                # Vertical displacements wide-format table view (all joints, all load cases)
                self._hide_all_views()
                self.beam_rotations_table.show()
                self.load_vertical_displacements_table(result_set_id)
            elif element_id > 0:
                # Element-specific directional results (pier shears V2/V3, etc.)
                self._hide_all_views()
                self.standard_view.show()
                self.load_element_dataset(element_id, result_type, direction, result_set_id)
            else:
                # Global directional results (story drifts X/Y, forces, etc.)
                self._hide_all_views()
                self.standard_view.show()
                self.load_standard_dataset(result_type, direction, result_set_id)
        else:
            self.content_title.setText("Select a result type")
            self._hide_all_views()
            self.standard_view.show()
            self.standard_view.clear()

    def on_comparison_selected(self, comparison_set_id: int, result_type: str, direction: str):
        """Handle comparison set selection.

        Args:
            comparison_set_id: ID of the selected comparison set
            result_type: Result type (e.g., "Drifts", "Forces", "QuadRotations")
            direction: Direction ("X", "Y", or "All" for all rotations view)
        """
        from database.repository import ComparisonSetRepository

        try:
            # Get comparison set from database
            comparison_set_repo = ComparisonSetRepository(self.session)
            comparison_set = comparison_set_repo.get_by_id(comparison_set_id)

            if not comparison_set:
                self.statusBar().showMessage("Error: Comparison set not found")
                return

            # Check if this is "All Rotations" view
            if direction == "All" and result_type == "QuadRotations":
                self.load_comparison_all_rotations(comparison_set)
                return

            # Check if this is "All Joints" view (soil pressures, vertical displacements)
            if direction == "AllJoints" and result_type in ["SoilPressures", "VerticalDisplacements"]:
                self.load_comparison_joint_scatter(comparison_set, result_type)
                return

            # Load comparison dataset
            dataset = self.result_service.get_comparison_dataset(
                result_type=result_type,
                direction=direction,
                result_set_ids=comparison_set.result_set_ids,
                metric='Avg'
            )

            if not dataset:
                self.content_title.setText(f"> Comparison: {result_type} {direction}")
                self.statusBar().showMessage("No comparison data available")
                # Hide all views
                self._hide_all_views()
                return

            # Show comparison view
            self._hide_all_views()
            self.comparison_view.show()

            # Load data into comparison view
            self.comparison_view.set_dataset(dataset)

            # Build readable title with result set names and units
            result_set_names = [series.result_set_name for series in dataset.series if series.has_data]
            result_type_with_unit = format_result_type_with_unit(result_type, direction)

            if len(result_set_names) >= 2:
                comparison_title = f"{result_type_with_unit} - {' vs '.join(result_set_names)} Comparison"
            else:
                comparison_title = f"{result_type_with_unit} Comparison"

            self.content_title.setText(f"> {comparison_title}")

            # Show status with warnings if any
            warning_msg = f" ({len(dataset.warnings)} warnings)" if dataset.warnings else ""
            self.statusBar().showMessage(
                f"Loaded comparison for {len(dataset.series)} result sets{warning_msg}"
            )

        except Exception as exc:
            self.statusBar().showMessage(f"Error loading comparison: {str(exc)}")
            import traceback
            traceback.print_exc()

    def on_comparison_element_selected(self, comparison_set_id: int, result_type: str, element_id: int, direction: str):
        """Handle comparison element selection.

        Args:
            comparison_set_id: ID of the selected comparison set
            result_type: Result type (e.g., "WallShears", "QuadRotations")
            element_id: ID of the element to compare
            direction: Direction (e.g., "V2", "V3") or None
        """
        from database.repository import ComparisonSetRepository, ElementRepository

        try:
            # Get comparison set from database
            comparison_set_repo = ComparisonSetRepository(self.session)
            comparison_set = comparison_set_repo.get_by_id(comparison_set_id)

            if not comparison_set:
                self.statusBar().showMessage("Error: Comparison set not found")
                return

            # Get element info
            element_repo = ElementRepository(self.session)
            element = element_repo.get_by_id(element_id)

            if not element:
                self.statusBar().showMessage("Error: Element not found")
                return

            # Load comparison dataset for this element
            dataset = self.result_service.get_comparison_dataset(
                result_type=result_type,
                direction=direction,
                result_set_ids=comparison_set.result_set_ids,
                metric='Avg',
                element_id=element_id
            )

            if not dataset:
                self.content_title.setText(f"> Comparison: {element.name} - {result_type}")
                self.statusBar().showMessage("No comparison data available")
                # Hide all views
                self._hide_all_views()
                return

            # Show comparison view
            self._hide_all_views()
            self.comparison_view.show()

            # Load data into comparison view
            self.comparison_view.set_dataset(dataset)

            # Build readable title with result set names and units
            result_set_names = [series.result_set_name for series in dataset.series if series.has_data]
            result_type_with_unit = format_result_type_with_unit(result_type, direction)

            if len(result_set_names) >= 2:
                comparison_title = f"{element.name} - {result_type_with_unit} - {' vs '.join(result_set_names)} Comparison"
            else:
                comparison_title = f"{element.name} - {result_type_with_unit} Comparison"

            self.content_title.setText(f"> {comparison_title}")

            # Show status with warnings if any
            warning_msg = f" ({len(dataset.warnings)} warnings)" if dataset.warnings else ""
            self.statusBar().showMessage(
                f"Loaded comparison for {len(dataset.series)} result sets{warning_msg}"
            )

        except Exception as exc:
            self.statusBar().showMessage(f"Error loading element comparison: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_standard_dataset(self, result_type: str, direction: str, result_set_id: int) -> None:
        """Load and display directional results for the selected type."""
        try:
            dataset = self.result_service.get_standard_dataset(result_type, direction, result_set_id)

            if not dataset:
                self.standard_view.clear()
                self.statusBar().showMessage(
                    f"No data available for {result_type} ({direction})"
                )
                return

            # Use cached pushover mapping if available
            shorthand_mapping = None
            if self.active_context == "Pushover":
                shorthand_mapping = self._get_pushover_mapping(result_set_id)
                print(f"[DEBUG] load_standard_dataset: context={self.active_context}, result_set_id={result_set_id}")
                print(f"[DEBUG] Mapping retrieved: {len(shorthand_mapping) if shorthand_mapping else 0} entries")
                if shorthand_mapping:
                    print(f"[DEBUG] Sample mapping: {list(shorthand_mapping.items())[:2]}")
                print(f"[DEBUG] Dataset load cases: {dataset.load_case_columns[:3] if len(dataset.load_case_columns) > 3 else dataset.load_case_columns}")

            self.content_title.setText(f"> {dataset.meta.display_name}")
            self.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

            story_count = len(dataset.data.index)
            self.statusBar().showMessage(
                f"Loaded {story_count} stories for {dataset.meta.display_name}"
            )

        except Exception as exc:  # pragma: no cover - UI feedback
            self.standard_view.clear()
            self.statusBar().showMessage(f"Error loading results: {str(exc)}")
            import traceback

            traceback.print_exc()

    def load_element_dataset(self, element_id: int, result_type: str, direction: str, result_set_id: int) -> None:
        """Load and display element-specific results (pier shears, etc.)."""
        try:
            print(f"[DEBUG] load_element_dataset called:")
            print(f"  - element_id={element_id}, result_type={result_type}, direction={direction}, result_set_id={result_set_id}")
            print(f"  - active_context={self.active_context}")

            dataset = self.result_service.get_element_dataset(element_id, result_type, direction, result_set_id)

            if not dataset:
                self.standard_view.clear()
                self.statusBar().showMessage(
                    f"No data available for element results"
                )
                return

            # Use cached pushover mapping if available
            shorthand_mapping = None
            if self.active_context == "Pushover":
                print(f"[DEBUG] Active context is Pushover, getting mapping for result_set_id={result_set_id}")
                shorthand_mapping = self._get_pushover_mapping(result_set_id)
                print(f"[DEBUG] Retrieved mapping: {len(shorthand_mapping) if shorthand_mapping else 0} entries")
                if shorthand_mapping:
                    print(f"[DEBUG] Sample mapping: {list(shorthand_mapping.items())[:2]}")
            else:
                print(f"[DEBUG] Active context is '{self.active_context}' (not Pushover), no mapping applied")

            self.content_title.setText(f"> {dataset.meta.display_name}")
            print(f"[DEBUG] Passing mapping to standard_view: {shorthand_mapping is not None}")
            self.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

            story_count = len(dataset.data.index)
            self.statusBar().showMessage(
                f"Loaded {story_count} stories for {dataset.meta.display_name}"
            )

        except Exception as exc:
            self.standard_view.clear()
            self.statusBar().showMessage(f"Error loading element results: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_joint_dataset(self, result_type: str, result_set_id: int) -> None:
        """Load and display joint-level results (soil pressures, etc.)."""
        try:
            print(f"[DEBUG] load_joint_dataset called:")
            print(f"  - result_type={result_type}, result_set_id={result_set_id}")
            print(f"  - active_context={self.active_context}")

            dataset = self.result_service.get_joint_dataset(result_type, result_set_id)

            if not dataset:
                self.standard_view.clear()
                self.statusBar().showMessage(
                    f"No data available for joint results"
                )
                return

            # Use cached pushover mapping if available
            shorthand_mapping = None
            if self.active_context == "Pushover":
                print(f"[DEBUG] Active context is Pushover, getting mapping for result_set_id={result_set_id}")
                shorthand_mapping = self._get_pushover_mapping(result_set_id)
                print(f"[DEBUG] Retrieved mapping: {len(shorthand_mapping) if shorthand_mapping else 0} entries")
            else:
                print(f"[DEBUG] Active context is '{self.active_context}' (not Pushover), no mapping applied")

            self.content_title.setText(f"> {dataset.meta.display_name}")
            print(f"[DEBUG] Passing mapping to standard_view: {shorthand_mapping is not None}")
            self.standard_view.set_dataset(dataset, shorthand_mapping=shorthand_mapping)

            element_count = len(dataset.data.index)
            self.statusBar().showMessage(
                f"Loaded {element_count} foundation elements for {dataset.meta.display_name}"
            )

        except Exception as exc:
            self.standard_view.clear()
            self.statusBar().showMessage(f"Error loading joint results: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_maxmin_dataset(self, result_set_id: int, base_result_type: str = "Drifts"):
        """Load and display absolute Max/Min drift results from database.

        Args:
            result_set_id: ID of the result set to filter by
        """
        try:
            dataset = self.result_service.get_maxmin_dataset(result_set_id, base_result_type)

            if not dataset or dataset.data.empty:
                self.maxmin_widget.clear_data()
                self.content_title.setText("> Max/Min Results")
                self.statusBar().showMessage("No absolute max/min data available")
                return

            self.maxmin_widget.load_dataset(dataset)
            self.content_title.setText(f"> {dataset.meta.display_name}")

            story_count = len(dataset.data.index)
            self.statusBar().showMessage(
                f"Loaded {dataset.meta.display_name} for {story_count} stories"
            )

        except Exception as exc:
            self.maxmin_widget.clear_data()
            self.statusBar().showMessage(f"Error loading Max/Min results: {str(exc)}")
            import traceback

            traceback.print_exc()

    def load_element_maxmin_dataset(self, element_id: int, result_set_id: int, base_result_type: str = "WallShears"):
        """Load and display element-specific Max/Min results (pier shears).

        Args:
            element_id: ID of the element (pier/wall)
            result_set_id: ID of the result set to filter by
            base_result_type: Base result type (e.g., 'WallShears', 'ColumnRotations')
        """
        try:
            dataset = self.result_service.get_element_maxmin_dataset(element_id, result_set_id, base_result_type)

            if not dataset or dataset.data.empty:
                self.maxmin_widget.clear_data()
                self.content_title.setText("> Element Max/Min Results")
                self.statusBar().showMessage("No element max/min data available")
                return

            self.maxmin_widget.load_dataset(dataset)
            self.content_title.setText(f"> {dataset.meta.display_name}")

            story_count = len(dataset.data.index)
            self.statusBar().showMessage(
                f"Loaded {dataset.meta.display_name} for {story_count} stories"
            )

        except Exception as exc:
            self.maxmin_widget.clear_data()
            self.statusBar().showMessage(f"Error loading element Max/Min results: {str(exc)}")
            import traceback

            traceback.print_exc()

    def load_all_rotations(self, result_set_id: int):
        """Load and display all quad rotations across all elements as scatter plot (both Max and Min).

        Args:
            result_set_id: ID of the result set to filter by
        """
        try:
            # Fetch both Max and Min data
            df_max = self.result_service.get_all_quad_rotations_dataset(result_set_id, "Max")
            df_min = self.result_service.get_all_quad_rotations_dataset(result_set_id, "Min")

            if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
                self.all_rotations_widget.clear_data()
                self.content_title.setText("> All Quad Rotations")
                self.statusBar().showMessage("No quad rotation data available")
                return

            self.all_rotations_widget.set_x_label("Quad Rotation (%)")
            self.all_rotations_widget.load_dataset(df_max, df_min)
            self.content_title.setText("> All Quad Rotations")

            # Count total points
            num_points_max = len(df_max) if df_max is not None and not df_max.empty else 0
            num_points_min = len(df_min) if df_min is not None and not df_min.empty else 0
            total_points = num_points_max + num_points_min

            # Get unique elements and stories from whichever dataset is available
            df_ref = df_max if df_max is not None and not df_max.empty else df_min
            num_elements = df_ref['Element'].nunique() if df_ref is not None else 0
            num_stories = df_ref['Story'].nunique() if df_ref is not None else 0

            self.statusBar().showMessage(
                f"Loaded {total_points} rotation data points ({num_points_max} max, {num_points_min} min) "
                f"across {num_elements} elements and {num_stories} stories"
            )

        except Exception as exc:
            self.all_rotations_widget.clear_data()
            self.statusBar().showMessage(f"Error loading all rotations: {str(exc)}")
            import traceback

            traceback.print_exc()

    def load_all_column_rotations(self, result_set_id: int):
        """Load and display all column rotations across all columns as scatter plot (both Max and Min).

        Args:
            result_set_id: ID of the result set to filter by
        """
        try:
            # Fetch both Max and Min data
            df_max = self.result_service.get_all_column_rotations_dataset(result_set_id, "Max")
            df_min = self.result_service.get_all_column_rotations_dataset(result_set_id, "Min")

            if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
                self.all_rotations_widget.clear_data()
                self.content_title.setText("> All Column Rotations")
                self.statusBar().showMessage("No column rotation data available")
                return

            self.all_rotations_widget.set_x_label("Column Rotation (%)")
            self.all_rotations_widget.load_dataset(df_max, df_min)
            self.content_title.setText("> All Column Rotations")

            # Count total points
            num_points_max = len(df_max) if df_max is not None and not df_max.empty else 0
            num_points_min = len(df_min) if df_min is not None and not df_min.empty else 0
            total_points = num_points_max + num_points_min

            # Get unique elements and stories from whichever dataset is available
            df_ref = df_max if df_max is not None and not df_max.empty else df_min
            num_elements = df_ref['Element'].nunique() if df_ref is not None else 0
            num_stories = df_ref['Story'].nunique() if df_ref is not None else 0

            self.statusBar().showMessage(
                f"Loaded {total_points} rotation data points ({num_points_max} max, {num_points_min} min) "
                f"across {num_elements} columns and {num_stories} stories"
            )

        except Exception as exc:
            self.all_rotations_widget.clear_data()
            self.statusBar().showMessage(f"Error loading all column rotations: {str(exc)}")
            import traceback

            traceback.print_exc()

    def load_all_beam_rotations(self, result_set_id: int):
        """Load and display all beam rotations across all beams as scatter plot (both Max and Min).

        Args:
            result_set_id: ID of the result set to filter by
        """
        try:
            # Fetch both Max and Min data
            df_max = self.result_service.get_all_beam_rotations_dataset(result_set_id, "Max")
            df_min = self.result_service.get_all_beam_rotations_dataset(result_set_id, "Min")

            if (df_max is None or df_max.empty) and (df_min is None or df_min.empty):
                self.all_rotations_widget.clear_data()
                self.content_title.setText("> All Beam Rotations")
                self.statusBar().showMessage("No beam rotation data available")
                return

            self.all_rotations_widget.set_x_label("R3 Plastic Rotation (%)")
            self.all_rotations_widget.load_dataset(df_max, df_min)
            self.content_title.setText("> All Beam Rotations")

            # Count total points
            num_points_max = len(df_max) if df_max is not None and not df_max.empty else 0
            num_points_min = len(df_min) if df_min is not None and not df_min.empty else 0
            total_points = num_points_max + num_points_min

            # Get unique elements and stories from whichever dataset is available
            df_ref = df_max if df_max is not None and not df_max.empty else df_min
            num_elements = df_ref['Element'].nunique() if df_ref is not None else 0
            num_stories = df_ref['Story'].nunique() if df_ref is not None else 0

            self.statusBar().showMessage(
                f"Loaded {total_points} rotation data points ({num_points_max} max, {num_points_min} min) "
                f"across {num_elements} beams and {num_stories} stories"
            )

        except Exception as exc:
            self.all_rotations_widget.clear_data()
            self.statusBar().showMessage(f"Error loading all beam rotations: {str(exc)}")
            import traceback

            traceback.print_exc()

    def load_comparison_all_rotations(self, comparison_set):
        """Load and display all quad rotations comparison across multiple result sets.

        Args:
            comparison_set: ComparisonSet model instance
        """
        try:
            # Hide other views and show comparison all rotations widget
            self._hide_all_views()
            self.comparison_all_rotations_widget.show()

            # Fetch data for each result set in the comparison
            datasets = []
            result_set_repo = ResultSetRepository(self.session)

            for result_set_id in comparison_set.result_set_ids:
                result_set = result_set_repo.get_by_id(result_set_id)
                if not result_set:
                    continue

                # Get all rotations data (combine Max and Min into single dataset)
                df_max = self.result_service.get_all_quad_rotations_dataset(result_set_id, "Max")
                df_min = self.result_service.get_all_quad_rotations_dataset(result_set_id, "Min")

                # Combine Max and Min data
                if df_max is not None and not df_max.empty and df_min is not None and not df_min.empty:
                    df_combined = pd.concat([df_max, df_min], ignore_index=True)
                elif df_max is not None and not df_max.empty:
                    df_combined = df_max
                elif df_min is not None and not df_min.empty:
                    df_combined = df_min
                else:
                    df_combined = None

                if df_combined is not None and not df_combined.empty:
                    datasets.append((result_set.name, df_combined))

            if not datasets:
                self.comparison_all_rotations_widget.clear_data()
                self.content_title.setText("> All Rotations Comparison")
                self.statusBar().showMessage("No quad rotation data available for comparison")
                return

            # Load data into widget
            self.comparison_all_rotations_widget.set_x_label("Quad Rotation (%)")
            self.comparison_all_rotations_widget.load_comparison_datasets(datasets)

            # Build title with result set names
            result_set_names = [name for name, _ in datasets]
            comparison_title = f"All Quad Rotations - {' vs '.join(result_set_names)} Comparison"
            self.content_title.setText(f"> {comparison_title}")

            # Count total points
            total_points = sum(len(df) for _, df in datasets)
            self.statusBar().showMessage(
                f"Loaded {total_points} rotation data points across {len(datasets)} result sets"
            )

        except Exception as exc:
            self.comparison_all_rotations_widget.clear_data()
            self.statusBar().showMessage(f"Error loading comparison all rotations: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_comparison_joint_scatter(self, comparison_set, result_type: str):
        """Load and display joint results comparison scatter plot across multiple result sets.

        Args:
            comparison_set: ComparisonSet model instance
            result_type: Type of joint result ('SoilPressures' or 'VerticalDisplacements')
        """
        try:
            # Hide other views and show comparison joint scatter widget
            self._hide_all_views()
            self.comparison_joint_scatter_widget.show()

            # Import comparison builder
            from processing.result_service.comparison_builder import build_all_joints_comparison
            from config.result_config import RESULT_CONFIGS

            # Get result type with suffix for cache lookup
            result_type_cache = f"{result_type}_Min"
            config = RESULT_CONFIGS.get(result_type_cache)

            if not config:
                self.statusBar().showMessage(f"Unknown result type: {result_type}")
                return

            # Build datasets using comparison builder
            result_set_repo = ResultSetRepository(self.session)
            datasets = build_all_joints_comparison(
                result_type=result_type_cache,
                result_set_ids=comparison_set.result_set_ids,
                config=config,
                get_dataset_func=lambda rt, rs_id: self.result_service.get_joint_dataset(rt, rs_id),
                result_set_repo=result_set_repo
            )

            if not datasets:
                self.comparison_joint_scatter_widget.clear_data()
                self.content_title.setText(f"> {result_type} Comparison")
                self.statusBar().showMessage(f"No {result_type} data available for comparison")
                return

            # Load data into widget
            self.comparison_joint_scatter_widget.load_comparison_datasets(datasets, result_type)

            # Build title with result set names
            result_set_names = [name for name, _, _ in datasets]
            comparison_title = f"All {result_type} - {' vs '.join(result_set_names)} Comparison"
            self.content_title.setText(f"> {comparison_title}")

            # Count total points and load cases
            total_points = sum(len(df) * len(lc) for _, df, lc in datasets)
            num_load_cases = len(datasets[0][2]) if datasets else 0
            self.statusBar().showMessage(
                f"Loaded {total_points} data points across {len(datasets)} result sets and {num_load_cases} load cases"
            )

        except Exception as exc:
            self.comparison_joint_scatter_widget.clear_data()
            self.statusBar().showMessage(f"Error loading comparison joint scatter: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_beam_rotations_table(self, result_set_id: int):
        """Load and display beam rotations table in wide format (all beams, all load cases).

        Args:
            result_set_id: ID of the result set
        """
        try:
            print(f"[DEBUG] load_beam_rotations_table called with result_set_id={result_set_id}, active_context={self.active_context}")

            # Get beam rotation data in wide format
            df = self.result_service.get_beam_rotations_table_dataset(result_set_id)

            if df is None or df.empty:
                self.beam_rotations_table.clear()
                self.content_title.setText("> Beam Rotations - R3 Plastic")
                self.beam_rotations_table.setRowCount(1)
                self.beam_rotations_table.setColumnCount(1)
                self.beam_rotations_table.setHorizontalHeaderLabels(['Message'])
                message_item = QTableWidgetItem("No beam rotation data available")
                self.beam_rotations_table.setItem(0, 0, message_item)
                self.statusBar().showMessage("No beam rotation data available")
                return

            # Clear and setup table
            self.beam_rotations_table.clear()
            self.content_title.setText("> Beam Rotations - R3 Plastic (%)")

            # Set table dimensions
            num_rows = len(df)
            num_cols = len(df.columns)
            self.beam_rotations_table.setRowCount(num_rows)
            self.beam_rotations_table.setColumnCount(num_cols)

            # Set column headers with pushover mapping if applicable
            column_names = df.columns.tolist()
            print(f"[DEBUG] Column names: {column_names[:5]}...")  # Show first 5

            try:
                if self.active_context == "Pushover":
                    shorthand_mapping = self._get_pushover_mapping(result_set_id)
                    if shorthand_mapping:
                        display_names = [shorthand_mapping.get(name, name) for name in column_names]
                        self.beam_rotations_table.setHorizontalHeaderLabels(display_names)
                        print(f"[DEBUG] Applied pushover mapping to beam rotations headers")
                    else:
                        self.beam_rotations_table.setHorizontalHeaderLabels(column_names)
                        print(f"[DEBUG] No mapping available, using original headers")
                else:
                    self.beam_rotations_table.setHorizontalHeaderLabels(column_names)
                    print(f"[DEBUG] Non-pushover context, using original headers")
            except Exception as mapping_exc:
                print(f"[ERROR] Failed to apply mapping: {mapping_exc}")
                # Fallback to original headers
                self.beam_rotations_table.setHorizontalHeaderLabels(column_names)

            # Identify load case columns and summary columns
            fixed_cols = ['Story', 'Frame/Wall', 'Unique Name', 'Hinge', 'Generated Hinge', 'Rel Dist']
            summary_cols = ['Avg', 'Max', 'Min']
            load_case_cols = [col for col in df.columns if col not in fixed_cols and col not in summary_cols]

            # Get color scheme from config
            config = RESULT_CONFIGS.get('BeamRotations_R3Plastic')
            color_scheme = config.color_scheme if config else 'blue_orange'

            # Calculate min/max values for gradient colors from all numeric columns
            numeric_cols = load_case_cols + summary_cols
            all_numeric_values = []
            for col in numeric_cols:
                if col in df.columns:
                    all_numeric_values.extend(df[col].dropna().tolist())

            min_val = min(all_numeric_values) if all_numeric_values else 0
            max_val = max(all_numeric_values) if all_numeric_values else 0

            # Populate table
            for row_idx, (_, row) in enumerate(df.iterrows()):
                for col_idx, col_name in enumerate(df.columns):
                    value = row[col_name]

                    # Format value based on column type
                    if col_name in fixed_cols:
                        # Fixed columns - display as is
                        if col_name == 'Rel Dist':
                            item_text = f"{value:.2f}" if value is not None else ""
                        else:
                            item_text = str(value) if value is not None else ""
                    elif col_name in load_case_cols or col_name in summary_cols:
                        # Numeric columns - format as percentage with 2 decimal places
                        if value is not None and not pd.isna(value):
                            item_text = f"{value:.2f}%"
                        else:
                            item_text = ""
                    else:
                        item_text = str(value) if value is not None else ""

                    item = QTableWidgetItem(item_text)

                    # Center align all items
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Apply gradient colors to numeric columns
                    if col_name in load_case_cols or col_name in summary_cols:
                        if value is not None and not pd.isna(value):
                            color = get_gradient_color(value, min_val, max_val, color_scheme)
                            item.setForeground(color)
                            item._original_color = QColor(color)
                        else:
                            # Empty cells get default color
                            default_color = QColor("#9ca3af")
                            item.setForeground(default_color)
                            item._original_color = QColor(default_color)
                    else:
                        # Fixed columns get default color
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        item._original_color = QColor(default_color)

                    self.beam_rotations_table.setItem(row_idx, col_idx, item)

            # Resize columns to content
            self.beam_rotations_table.resizeColumnsToContents()

            # Count unique beams
            num_beams = df['Frame/Wall'].nunique() if 'Frame/Wall' in df.columns else 0
            num_stories = df['Story'].nunique() if 'Story' in df.columns else 0

            self.statusBar().showMessage(
                f"Loaded beam rotations table: {num_rows} hinge locations across {num_beams} beams and {num_stories} stories"
            )

        except Exception as exc:
            self.beam_rotations_table.clear()
            self.statusBar().showMessage(f"Error loading beam rotations table: {str(exc)}")
            import traceback

            traceback.print_exc()

    def load_all_soil_pressures(self, result_set_id: int):
        """Load and display all soil pressures as bar chart.

        Args:
            result_set_id: ID of the result set to filter by
        """
        try:
            # Fetch soil pressure data
            dataset = self.result_service.get_joint_dataset("SoilPressures_Min", result_set_id)

            if not dataset or dataset.data.empty:
                self.soil_pressure_plot_widget.clear_data()
                self.content_title.setText("> Soil Pressures (Min)")
                self.statusBar().showMessage("No soil pressure data available")
                return

            df = dataset.data
            load_cases = dataset.load_case_columns

            # Load into the bar chart widget
            self.soil_pressure_plot_widget.load_dataset(df, load_cases)
            self.content_title.setText("> Soil Pressures (Min) - Distribution by Load Case")

            num_elements = len(df)
            num_load_cases = len(load_cases)

            self.statusBar().showMessage(
                f"Loaded soil pressure distribution: {num_elements} foundation elements across {num_load_cases} load cases"
            )

        except Exception as exc:
            self.soil_pressure_plot_widget.clear_data()
            self.statusBar().showMessage(f"Error loading soil pressures: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_soil_pressures_table(self, result_set_id: int):
        """Load and display soil pressures table in wide format (all elements, all load cases).

        Args:
            result_set_id: ID of the result set
        """
        try:
            print(f"[DEBUG] load_soil_pressures_table called with result_set_id={result_set_id}, active_context={self.active_context}")

            # Get soil pressure data in wide format
            dataset = self.result_service.get_joint_dataset("SoilPressures_Min", result_set_id)

            if not dataset or dataset.data.empty:
                self.beam_rotations_table.clear()
                self.content_title.setText("> Soil Pressures (Min)")
                self.beam_rotations_table.setRowCount(1)
                self.beam_rotations_table.setColumnCount(1)
                self.beam_rotations_table.setHorizontalHeaderLabels(['Message'])
                message_item = QTableWidgetItem("No soil pressure data available")
                self.beam_rotations_table.setItem(0, 0, message_item)
                self.statusBar().showMessage("No soil pressure data available")
                return

            df = dataset.data

            # Clear and setup table
            self.beam_rotations_table.clear()
            self.content_title.setText(f"> {dataset.meta.display_name}")

            # Set table dimensions
            num_rows = len(df)
            num_cols = len(df.columns)
            self.beam_rotations_table.setRowCount(num_rows)
            self.beam_rotations_table.setColumnCount(num_cols)

            # Set column headers with pushover mapping if applicable
            column_names = df.columns.tolist()

            try:
                if self.active_context == "Pushover":
                    shorthand_mapping = self._get_pushover_mapping(result_set_id)
                    if shorthand_mapping:
                        display_names = [shorthand_mapping.get(name, name) for name in column_names]
                        self.beam_rotations_table.setHorizontalHeaderLabels(display_names)
                        print(f"[DEBUG] Applied pushover mapping to soil pressures headers")
                    else:
                        self.beam_rotations_table.setHorizontalHeaderLabels(column_names)
                else:
                    self.beam_rotations_table.setHorizontalHeaderLabels(column_names)
            except Exception as mapping_exc:
                print(f"[ERROR] Failed to apply mapping in soil pressures: {mapping_exc}")
                self.beam_rotations_table.setHorizontalHeaderLabels(column_names)

            # Identify fixed, load case, and summary columns
            fixed_cols = ['Shell Object', 'Unique Name']
            load_case_cols = dataset.load_case_columns
            summary_cols = dataset.summary_columns

            # Get color scheme from config
            config = dataset.config
            color_scheme = config.color_scheme

            # Calculate min/max values for gradient colors (only from load case columns)
            all_numeric_values = []
            for col in load_case_cols:
                if col in df.columns:
                    all_numeric_values.extend(df[col].dropna().tolist())

            if all_numeric_values:
                global_min = min(all_numeric_values)
                global_max = max(all_numeric_values)
            else:
                global_min = global_max = 0

            # Populate table
            for row_idx, (_, row) in enumerate(df.iterrows()):
                for col_idx, col_name in enumerate(df.columns):
                    value = row[col_name]

                    # Format value based on column type
                    if (col_name in load_case_cols or col_name in summary_cols) and pd.notna(value):
                        # Numeric column - format with decimal places
                        formatted_value = f"{value:.{config.decimal_places}f}"
                    else:
                        # Fixed column (Shell Object, Unique Name)
                        formatted_value = str(value) if pd.notna(value) else ""

                    item = QTableWidgetItem(formatted_value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Apply gradient colors to load case columns
                    if col_name in load_case_cols and pd.notna(value):
                        if global_max != global_min:
                            from utils.color_utils import get_gradient_color
                            color = get_gradient_color(value, global_min, global_max, color_scheme)
                            item.setForeground(color)
                            item._original_color = QColor(color)
                        else:
                            default_color = QColor("#9ca3af")
                            item.setForeground(default_color)
                            item._original_color = QColor(default_color)
                    elif col_name in summary_cols and pd.notna(value):
                        # Summary columns get a distinct color (lighter gray)
                        summary_color = QColor("#a3a3a3")
                        item.setForeground(summary_color)
                        item._original_color = QColor(summary_color)
                    else:
                        # Fixed columns get default color
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        item._original_color = QColor(default_color)

                    self.beam_rotations_table.setItem(row_idx, col_idx, item)

            # Resize columns to content
            self.beam_rotations_table.resizeColumnsToContents()

            # Count unique elements
            num_elements = len(df)
            num_load_cases = len(load_case_cols)

            self.statusBar().showMessage(
                f"Loaded soil pressures table: {num_elements} foundation elements across {num_load_cases} load cases"
            )

        except Exception as exc:
            self.beam_rotations_table.clear()
            self.statusBar().showMessage(f"Error loading soil pressures table: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_all_vertical_displacements(self, result_set_id: int):
        """Load and display all vertical displacements as scatter plot.

        Args:
            result_set_id: ID of the result set to filter by
        """
        try:
            # Fetch vertical displacement data
            dataset = self.result_service.get_joint_dataset("VerticalDisplacements_Min", result_set_id)

            if not dataset or dataset.data.empty:
                self.soil_pressure_plot_widget.clear_data()
                self.content_title.setText("> Vertical Displacements (Min)")
                self.statusBar().showMessage("No vertical displacement data available")
                return

            df = dataset.data
            load_cases = dataset.load_case_columns

            # Load into the scatter plot widget (reusing soil pressure widget)
            self.soil_pressure_plot_widget.load_dataset(df, load_cases)
            self.content_title.setText("> Vertical Displacements (Min) - Distribution by Load Case")

            num_joints = len(df)
            num_load_cases = len(load_cases)

            self.statusBar().showMessage(
                f"Loaded vertical displacement distribution: {num_joints} foundation joints across {num_load_cases} load cases"
            )

        except Exception as exc:
            self.soil_pressure_plot_widget.clear_data()
            self.statusBar().showMessage(f"Error loading vertical displacements: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_vertical_displacements_table(self, result_set_id: int):
        """Load and display vertical displacements table in wide format (all joints, all load cases).

        Args:
            result_set_id: ID of the result set
        """
        try:
            print(f"[DEBUG] load_vertical_displacements_table called with result_set_id={result_set_id}, active_context={self.active_context}")

            # Get vertical displacement data in wide format
            dataset = self.result_service.get_joint_dataset("VerticalDisplacements_Min", result_set_id)

            if not dataset or dataset.data.empty:
                self.beam_rotations_table.clear()
                self.content_title.setText("> Vertical Displacements (Min)")
                self.beam_rotations_table.setRowCount(1)
                self.beam_rotations_table.setColumnCount(1)
                self.beam_rotations_table.setHorizontalHeaderLabels(['Message'])
                message_item = QTableWidgetItem("No vertical displacement data available")
                self.beam_rotations_table.setItem(0, 0, message_item)
                self.statusBar().showMessage("No vertical displacement data available")
                return

            df = dataset.data

            # Clear and setup table
            self.beam_rotations_table.clear()
            self.content_title.setText(f"> {dataset.meta.display_name}")

            # Set table dimensions
            num_rows = len(df)
            num_cols = len(df.columns)
            self.beam_rotations_table.setRowCount(num_rows)
            self.beam_rotations_table.setColumnCount(num_cols)

            # Set column headers with pushover mapping if applicable
            column_names = df.columns.tolist()

            try:
                if self.active_context == "Pushover":
                    shorthand_mapping = self._get_pushover_mapping(result_set_id)
                    if shorthand_mapping:
                        display_names = [shorthand_mapping.get(name, name) for name in column_names]
                        self.beam_rotations_table.setHorizontalHeaderLabels(display_names)
                        print(f"[DEBUG] Applied pushover mapping to vertical displacements headers")
                    else:
                        self.beam_rotations_table.setHorizontalHeaderLabels(column_names)
                else:
                    self.beam_rotations_table.setHorizontalHeaderLabels(column_names)
            except Exception as mapping_exc:
                print(f"[ERROR] Failed to apply mapping in vertical displacements: {mapping_exc}")
                self.beam_rotations_table.setHorizontalHeaderLabels(column_names)

            # Identify fixed, load case, and summary columns
            fixed_cols = ['Shell Object', 'Unique Name']
            load_case_cols = dataset.load_case_columns
            summary_cols = dataset.summary_columns

            # Get color scheme from config
            config = dataset.config
            color_scheme = config.color_scheme

            # Calculate min/max values for gradient colors (only from load case columns)
            all_numeric_values = []
            for col in load_case_cols:
                if col in df.columns:
                    all_numeric_values.extend(df[col].dropna().tolist())

            if all_numeric_values:
                global_min = min(all_numeric_values)
                global_max = max(all_numeric_values)
            else:
                global_min = global_max = 0

            # Populate table
            for row_idx, (_, row) in enumerate(df.iterrows()):
                for col_idx, col_name in enumerate(df.columns):
                    value = row[col_name]

                    # Format value based on column type
                    if (col_name in load_case_cols or col_name in summary_cols) and pd.notna(value):
                        # Numeric column - format with decimal places
                        formatted_value = f"{value:.{config.decimal_places}f}"
                    else:
                        # Fixed column (Shell Object, Unique Name)
                        formatted_value = str(value) if pd.notna(value) else ""

                    item = QTableWidgetItem(formatted_value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    # Apply gradient colors to load case columns
                    if col_name in load_case_cols and pd.notna(value):
                        if global_max != global_min:
                            from utils.color_utils import get_gradient_color
                            color = get_gradient_color(value, global_min, global_max, color_scheme)
                            item.setForeground(color)
                            item._original_color = QColor(color)
                        else:
                            default_color = QColor("#9ca3af")
                            item.setForeground(default_color)
                            item._original_color = QColor(default_color)
                    elif col_name in summary_cols and pd.notna(value):
                        # Summary columns get a distinct color (lighter gray)
                        summary_color = QColor("#a3a3a3")
                        item.setForeground(summary_color)
                        item._original_color = QColor(summary_color)
                    else:
                        # Fixed columns get default color
                        default_color = QColor("#d1d5db")
                        item.setForeground(default_color)
                        item._original_color = QColor(default_color)

                    self.beam_rotations_table.setItem(row_idx, col_idx, item)

            # Resize columns to content
            self.beam_rotations_table.resizeColumnsToContents()

            # Count unique joints
            num_joints = len(df)
            num_load_cases = len(load_case_cols)

            self.statusBar().showMessage(
                f"Loaded vertical displacements table: {num_joints} foundation joints across {num_load_cases} load cases"
            )

        except Exception as exc:
            self.beam_rotations_table.clear()
            self.statusBar().showMessage(f"Error loading vertical displacements table: {str(exc)}")
            import traceback
            traceback.print_exc()

    def load_data_from_folder(self):
        """Load data from folder into current project."""
        from PyQt6.QtWidgets import QMessageBox
        from .folder_import_dialog import FolderImportDialog
        from gui.ui_helpers import show_dialog_with_blur

        # Create a modified dialog that uses the current project
        dialog = FolderImportDialog(self, context=self.context)

        if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
            # Data was imported, refresh the view
            self.session.expire_all()
            self.load_project_data()

            # Reload current result if selected
            if self.current_result_type and self.current_result_set_id:
                if self.current_result_type.startswith("MaxMin"):
                    base_type = self._extract_base_result_type(self.current_result_type)
                    self.result_service.invalidate_maxmin_dataset(self.current_result_set_id, base_type)
                    self.load_maxmin_dataset(self.current_result_set_id, base_type)
                elif self.current_element_id > 0:
                    self.result_service.invalidate_element_dataset(
                        self.current_element_id,
                        self.current_result_type,
                        self.current_direction,
                        self.current_result_set_id,
                    )
                    self.load_element_dataset(
                        self.current_element_id,
                        self.current_result_type,
                        self.current_direction,
                        self.current_result_set_id,
                    )
                else:
                    self.result_service.invalidate_standard_dataset(
                        self.current_result_type,
                        self.current_direction,
                        self.current_result_set_id,
                    )
                    self.load_standard_dataset(
                        self.current_result_type,
                        self.current_direction,
                        self.current_result_set_id,
                    )

            QMessageBox.information(
                self,
                "Load Complete",
                f"Successfully loaded data into project: {self.project_name}\n\n"
                f"The results browser has been refreshed."
            )

            self.statusBar().showMessage("Data loaded successfully", 5000)

    def load_pushover_curves(self):
        """Load pushover curves from Excel file."""
        from PyQt6.QtWidgets import QMessageBox
        from .pushover_import_dialog import PushoverImportDialog
        from gui.ui_helpers import show_dialog_with_blur

        # Create pushover import dialog
        dialog = PushoverImportDialog(
            project_id=self.project.id,
            project_name=self.project_name,
            session=self.session,
            parent=self
        )

        # Connect import completion to refresh
        dialog.import_completed.connect(lambda stats: self._on_pushover_import_completed(stats))

        if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
            self.statusBar().showMessage("Pushover curves import successful")

    def _on_pushover_import_completed(self, stats: dict):
        """Handle pushover import completion."""
        # Refresh the project data to show new result set
        self.session.expire_all()
        self.load_project_data()
        self.statusBar().showMessage(
            f"Imported {stats['curves_imported']} pushover curves into {stats['result_set_name']}"
        )

    def load_pushover_results(self):
        """Load pushover global results (drifts, displacements, forces) from folder."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from gui.pushover_global_import_dialog import PushoverGlobalImportDialog
        from gui.ui_helpers import show_dialog_with_blur

        # Show folder dialog to select directory with pushover global results
        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Pushover Global Results",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder_path:
            return  # User cancelled

        try:
            # Create import dialog
            dialog = PushoverGlobalImportDialog(
                project_id=self.project.id,
                project_name=self.project_name,
                folder_path=folder_path,
                session=self.session,
                parent=self
            )

            # Connect import completion to refresh
            dialog.import_completed.connect(lambda stats: self._on_pushover_global_import_completed(stats))

            if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
                self.statusBar().showMessage("Pushover global results import successful")

        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to open pushover global import dialog:\n\n{str(e)}"
            )
            import traceback
            traceback.print_exc()

    def _on_pushover_global_import_completed(self, stats: dict):
        """Handle pushover global results import completion."""
        # Refresh the project data to show new result set
        self.session.expire_all()
        self.load_project_data()
        self.statusBar().showMessage(
            f"Imported pushover global results: {stats.get('result_types_imported', 0)} result types"
        )

    def load_pushover_curve(self, case_name: str):
        """Load and display a pushover curve."""
        from database.repository import PushoverCaseRepository

        try:
            # Hide all other views and show pushover curve view
            self._hide_all_views()
            self.pushover_curve_view.show()

            # Get pushover case
            pushover_repo = PushoverCaseRepository(self.session)
            case = pushover_repo.get_by_name(
                self.project_id,
                self.current_result_set_id,
                case_name
            )

            if not case:
                self.statusBar().showMessage(f"Pushover case '{case_name}' not found")
                return

            # Get curve data points
            curve_points = pushover_repo.get_curve_data(case.id)

            if not curve_points:
                self.statusBar().showMessage(f"No data points found for '{case_name}'")
                return

            # Extract data for display
            step_numbers = [pt.step_number for pt in curve_points]
            displacements = [pt.displacement for pt in curve_points]
            base_shears = [pt.base_shear for pt in curve_points]

            # Display the curve
            self.pushover_curve_view.display_curve(
                case_name=case_name,
                step_numbers=step_numbers,
                displacements=displacements,
                base_shears=base_shears
            )

            # Update title
            self.content_title.setText(f"Pushover Curve: {case_name}")

            self.statusBar().showMessage(
                f"Loaded pushover curve: {case_name} ({len(curve_points)} points)"
            )

        except Exception as e:
            self.statusBar().showMessage(f"Error loading pushover curve: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_all_pushover_curves(self, direction: str):
        """Load and display all pushover curves for a given direction."""
        from database.repository import PushoverCaseRepository

        try:
            # Hide all other views and show pushover curve view
            self._hide_all_views()
            self.pushover_curve_view.show()

            # Get pushover case repository
            pushover_repo = PushoverCaseRepository(self.session)

            # Get all cases for this result set
            all_cases = pushover_repo.get_by_result_set(self.current_result_set_id)

            # Filter by direction
            direction_cases = [c for c in all_cases if c.direction == direction]

            if not direction_cases:
                self.statusBar().showMessage(f"No {direction} direction curves found")
                return

            # Load curve data for each case
            curves_data = []
            for case in direction_cases:
                curve_points = pushover_repo.get_curve_data(case.id)

                if curve_points:
                    curves_data.append({
                        'case_name': case.name,
                        'displacements': [pt.displacement for pt in curve_points],
                        'base_shears': [pt.base_shear for pt in curve_points]
                    })

            if not curves_data:
                self.statusBar().showMessage(f"No curve data found for {direction} direction")
                return

            # Display all curves
            self.pushover_curve_view.display_all_curves(curves_data)

            # Update title
            self.content_title.setText(f"All Pushover Curves - {direction} Direction")

            self.statusBar().showMessage(
                f"Loaded {len(curves_data)} pushover curves for {direction} direction"
            )

        except Exception as e:
            self.statusBar().showMessage(f"Error loading all pushover curves: {str(e)}")
            import traceback
            traceback.print_exc()

    def export_results(self):
        """Export results to file - contextual based on active mode (NLTHA or Pushover)."""
        # Check if we're in Pushover context
        if self.active_context == "Pushover":
            self.export_pushover_results()
        else:
            # NLTHA context - show comprehensive export dialog
            self.export_nltha_results()

    def export_nltha_results(self):
        """Export NLTHA results - shows comprehensive export dialog."""
        from gui.export_dialog import ComprehensiveExportDialog

        # If no result set is selected, use the first available one
        result_set_id = self.current_result_set_id
        if not result_set_id:
            result_sets = self.result_set_repo.get_by_project(self.project_id)
            if result_sets:
                result_set_id = result_sets[0].id
            else:
                self.statusBar().showMessage("No result sets available in this project", 3000)
                return

        # Show comprehensive export dialog
        from gui.ui_helpers import show_dialog_with_blur
        dialog = ComprehensiveExportDialog(
            context=self.context,
            result_service=self.result_service,
            current_result_set_id=result_set_id,
            project_name=self.project_name,
            parent=self
        )

        if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
            self.statusBar().showMessage("Export completed successfully!", 3000)

    def export_pushover_results(self):
        """Export pushover curves to Excel file."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from pathlib import Path
        from services.export_service import ExportService
        from datetime import datetime

        # Get current result set ID
        result_set_id = self.current_result_set_id
        if not result_set_id:
            # Try to find a pushover result set
            result_sets = self.result_set_repo.get_by_project(self.project_id)
            pushover_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) == 'Pushover']
            if pushover_sets:
                result_set_id = pushover_sets[0].id
            else:
                QMessageBox.warning(
                    self,
                    "No Pushover Data",
                    "No pushover result sets found in this project.\n\n"
                    "Please import pushover curves first."
                )
                return

        # Get result set name for filename
        result_set = self.result_set_repo.get_by_id(result_set_id)
        if not result_set:
            self.statusBar().showMessage("Result set not found", 3000)
            return

        # Generate default filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{self.project_name}_Pushover_Curves_{timestamp}.xlsx"

        # Show file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Pushover Curves",
            default_filename,
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return  # User cancelled

        # Export using ExportService
        try:
            export_service = ExportService(self.context, self.result_service)
            export_service.export_pushover_curves(
                result_set_id=result_set_id,
                output_path=Path(file_path),
                progress_callback=lambda msg, curr, total: self.statusBar().showMessage(msg, 2000)
            )

            QMessageBox.information(
                self,
                "Export Complete",
                f"Pushover curves exported successfully!\n\nFile: {file_path}"
            )

            self.statusBar().showMessage("Pushover curves exported successfully!", 3000)

        except ValueError as e:
            QMessageBox.warning(
                self,
                "Export Failed",
                f"Could not export pushover curves:\n\n{str(e)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred during export:\n\n{str(e)}"
            )

    def export_project_excel(self):
        """Export complete project to Excel workbook."""
        from gui.export_dialog import ExportProjectExcelDialog

        dialog = ExportProjectExcelDialog(
            context=self.context,
            result_service=self.result_service,
            project_name=self.project_name,
            parent=self
        )

        if dialog.exec():
            self.statusBar().showMessage("Project exported to Excel successfully!", 3000)

    def closeEvent(self, event):
        """Handle window close event - clean up all resources."""
        import gc
        import time

        project_name = getattr(self, "project_name", "Unknown")
        print(f"\n[DEBUG] ========== Closing project window: {project_name} ==========")

        try:
            # Store db_path before clearing context
            db_path = self.context.db_path if getattr(self, "context", None) else None

            # 1. Rollback any pending transactions and close session
            if getattr(self, "session", None):
                try:
                    print(f"[DEBUG] Rolling back and closing session...")
                    self.session.rollback()
                    self.session.close()
                    print(f"[DEBUG] Session closed successfully")
                except Exception as e:
                    print(f"[ERROR] Error closing session: {e}")
                finally:
                    self.session = None

            # 2. Dispose runtime resources
            if getattr(self, "runtime", None):
                try:
                    print(f"[DEBUG] Disposing runtime...")
                    self.runtime.dispose()
                    print(f"[DEBUG] Runtime disposed successfully")
                except Exception as e:
                    print(f"[ERROR] Error disposing runtime: {e}")
                finally:
                    self.runtime = None

            # 3. Clear context reference
            if getattr(self, "context", None):
                self.context = None

            # 4. Force garbage collection to release any remaining references
            print(f"[DEBUG] Running garbage collection...")
            gc.collect()

            # 5. Small delay to ensure all references are released
            time.sleep(0.1)

            # 6. Dispose of the database engine to fully release connections
            if db_path:
                print(f"[DEBUG] Disposing database engine...")
                from database.base import dispose_project_engine
                dispose_project_engine(db_path)

            print(f"[DEBUG] ========== Project window closed successfully: {project_name} ==========\n")

            # Notify parent to remove from tracking (if parent is MainWindow)
            if hasattr(self.parent(), '_project_windows'):
                parent_name = getattr(self, 'project_name', None)
                if parent_name and parent_name in self.parent()._project_windows:
                    print(f"[DEBUG] Removing {parent_name} from parent tracking...")
                    self.parent()._project_windows.pop(parent_name, None)

        except Exception as e:
            import traceback
            print(f"[ERROR] Error during project window cleanup: {e}")
            traceback.print_exc()
        finally:
            # Always accept the close event
            event.accept()

    @staticmethod
    def _extract_base_result_type(result_type: str) -> str:
        """Return the base result type name from a MaxMin identifier."""
        if not result_type.startswith("MaxMin"):
            return result_type or "Drifts"
        base = result_type.replace("MaxMin", "", 1)
        return base or "Drifts"
