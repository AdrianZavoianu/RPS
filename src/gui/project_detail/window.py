"""Project detail window - shows results browser and data visualization."""

import logging

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
    QTableWidget,
    QDialog,
    QLabel,
)
from PyQt6.QtCore import Qt

from gui.results_tree_browser import ResultsTreeBrowser
from gui.maxmin_drifts_widget import MaxMinDriftsWidget
from gui.all_rotations_widget import AllRotationsWidget
from gui.soil_pressure_plot_widget import SoilPressurePlotWidget
from gui.comparison_all_rotations_widget import ComparisonAllRotationsWidget
from gui.comparison_joint_scatter_widget import ComparisonJointScatterWidget
from gui.result_views import StandardResultView
from gui.result_views.comparison_view import ComparisonResultView
from gui.result_views.pushover_curve_view import PushoverCurveView
from gui.ui_helpers import create_styled_button, create_styled_label
from gui.window_utils import enable_dark_title_bar
from gui.styles import COLORS
from gui.icon_utils import get_colored_icon_pixmap, create_settings_icon
from gui.settings_popup import SettingsPopup
from gui.settings_manager import settings
from services.project_runtime import ProjectRuntime
from gui.controllers.result_view_controller import ResultViewController
from gui.controllers.project_detail_controller import ProjectDetailController
from config.analysis_types import AnalysisType

from . import event_handlers
from . import view_loaders

logger = logging.getLogger(__name__)


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

        # Selection + context controller
        self.controller = ProjectDetailController(project_id=self.project_id, cache_repo=self.cache_repo)
        self.view_controller = ResultViewController(self.project_id, self.cache_repo, self.controller)

        self.setup_ui()
        self.load_project_data()
        enable_dark_title_bar(self)

        # Connect to settings changes for layout borders
        settings.settings_changed.connect(self._on_settings_changed)
        self._apply_layout_borders()

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
        self._header_widget = self._create_header()
        layout.addWidget(self._header_widget)

        # Spacing below header (stored for border mode adjustment)
        self._header_spacer = QWidget()
        self._header_spacer.setFixedHeight(8)
        layout.addWidget(self._header_spacer)

        # Main content splitter (browser | table + plots)
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._main_splitter.setObjectName("mainSplitter")
        splitter = self._main_splitter
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)  # Minimal handle - just a hint
        splitter.setStyleSheet("""
            QSplitter#mainSplitter::handle {
                background-color: transparent;
                border: none;
            }
            QSplitter#mainSplitter::handle:hover {
                background-color: rgba(74, 125, 137, 0.2);
            }
        """)

        # Left: Results browser
        self.browser = ResultsTreeBrowser(self.project_id)
        self.browser.selection_changed.connect(self.on_browser_selection_changed)
        self.browser.comparison_selected.connect(self.on_comparison_selected)
        self.browser.comparison_element_selected.connect(self.on_comparison_element_selected)
        splitter.addWidget(self.browser)

        # Right: Content area (table + plots)
        self._content_widget = self._create_content_area()
        splitter.addWidget(self._content_widget)

        # Set splitter proportions (browser 220px, rest for content)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 5)
        splitter.setSizes([220, 1180])  # Browser 220px default for full text visibility

        layout.addWidget(splitter)

        # Hide status bar for cleaner UI
        self.statusBar().hide()

    def _create_header(self) -> QWidget:
        """Create header bar with contextual tabs and controls."""
        header = QWidget()
        header.setObjectName("projectHeader")
        header.setFixedHeight(36)
        header.setStyleSheet(f"""
            QWidget#projectHeader {{
                background-color: {COLORS['background']};
                border: none;
                min-height: 36px;
                max-height: 36px;
            }}
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(6)

        # RPS icon (colored with lighter accent for prominence)
        icon_label = QLabel()
        icon_pixmap = get_colored_icon_pixmap("RPS_icon", "#5a9daa", size=32)
        icon_label.setPixmap(icon_pixmap)
        icon_label.setFixedSize(32, 32)
        layout.addWidget(icon_label)

        # Project name (left side, distinctive) - largest in hierarchy
        title = create_styled_label(self.project_name, "header")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(title)

        # Stretch to push all buttons to the right
        layout.addStretch()

        # Tab buttons (NLTHA / Pushover) - simple underlined style
        self.nltha_tab = self._create_tab_button("NLTHA", active=True)
        self.pushover_tab = self._create_tab_button("Pushover", active=False)
        self.nltha_tab.clicked.connect(lambda: self._switch_context("NLTHA"))
        self.pushover_tab.clicked.connect(lambda: self._switch_context("Pushover"))

        layout.addWidget(self.nltha_tab)
        layout.addWidget(self.pushover_tab)

        # Visual separator for contextual actions
        separator1 = self._create_separator()
        layout.addWidget(separator1)

        # NLTHA-specific buttons (contextual)
        self.nltha_buttons = []

        load_data_btn = self._create_text_link_button("Load NLTHA Data")
        load_data_btn.setToolTip("Import NLTHA data from folder")
        load_data_btn.clicked.connect(self.load_data_from_folder)
        layout.addWidget(load_data_btn)
        self.nltha_buttons.append(load_data_btn)

        create_comparison_btn = self._create_text_link_button("Create Comparison")
        create_comparison_btn.setToolTip("Create a new comparison set")
        create_comparison_btn.clicked.connect(self.create_comparison_set)
        layout.addWidget(create_comparison_btn)
        self.nltha_buttons.append(create_comparison_btn)

        nltha_export_btn = self._create_text_link_button("Export Results")
        nltha_export_btn.setToolTip("Export NLTHA results to file")
        nltha_export_btn.clicked.connect(self.export_results)
        layout.addWidget(nltha_export_btn)
        self.nltha_buttons.append(nltha_export_btn)

        # Pushover-specific buttons (contextual)
        self.pushover_buttons = []

        load_pushover_btn = self._create_text_link_button("Load Pushover Curves")
        load_pushover_btn.setToolTip("Import pushover capacity curves")
        load_pushover_btn.clicked.connect(self.load_pushover_curves)
        layout.addWidget(load_pushover_btn)
        load_pushover_btn.hide()  # Hidden initially
        self.pushover_buttons.append(load_pushover_btn)

        load_results_btn = self._create_text_link_button("Load Results")
        load_results_btn.setToolTip("Import pushover global results (drifts, displacements, forces)")
        load_results_btn.clicked.connect(self.load_pushover_results)
        layout.addWidget(load_results_btn)
        load_results_btn.hide()  # Hidden initially
        self.pushover_buttons.append(load_results_btn)

        pushover_export_btn = self._create_text_link_button("Export Results")
        pushover_export_btn.setToolTip("Export pushover results to file")
        pushover_export_btn.clicked.connect(self.export_results)
        layout.addWidget(pushover_export_btn)
        pushover_export_btn.hide()  # Hidden initially
        self.pushover_buttons.append(pushover_export_btn)

        # Visual separator for general actions
        separator2 = self._create_separator()
        layout.addWidget(separator2)

        # Common buttons (always visible - general actions)
        export_project_btn = self._create_text_link_button("Export Project")
        export_project_btn.setToolTip("Export complete project to Excel")
        export_project_btn.clicked.connect(self.export_project_excel)
        layout.addWidget(export_project_btn)

        settings_btn = QPushButton()
        settings_btn.setIcon(create_settings_icon(18, COLORS['muted']))
        settings_btn.setFixedSize(28, 28)
        settings_btn.setToolTip("Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['hover']};
            }}
        """)
        settings_btn.clicked.connect(self._show_settings_popup)
        layout.addWidget(settings_btn)
        self._settings_btn = settings_btn

        return header

    def _create_tab_button(self, text: str, active: bool = False) -> QPushButton:
        """Create a tab button with web-style navigation."""
        btn = QPushButton(text)
        btn.setCheckable(True)
        btn.setChecked(active)
        btn.setFixedHeight(32)
        btn.setMinimumWidth(80)

        # Web-style tab navigation - prominent with accent color for selected
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['muted'] if not active else COLORS['accent']};
                border: none;
                border-bottom: 2px solid {'transparent' if not active else COLORS['accent']};
                border-radius: 0px;
                padding: 4px 16px;
                font-size: 15px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                color: {COLORS['text'] if not active else COLORS['accent']};
                background-color: transparent;
            }}
            QPushButton:checked {{
                color: {COLORS['accent']};
                border-bottom: 2px solid {COLORS['accent']};
                border-radius: 0px;
                font-weight: 500;
            }}
        """)

        return btn
    
    def _create_text_link_button(self, text: str) -> QPushButton:
        """Create a text-link style button with web navigation vibe."""
        btn = QPushButton(text)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text']};
                border: none;
                padding: 4px 10px;
                font-size: 15px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
                background-color: transparent;
            }}
            QPushButton:pressed {{
                color: {COLORS['accent']};
                background-color: transparent;
            }}
        """)
        return btn
    
    def _create_separator(self) -> QWidget:
        """Create a vertical separator for visual grouping."""
        separator = QWidget()
        separator.setFixedWidth(1)
        separator.setFixedHeight(20)
        separator.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['border']};
            }}
        """)
        return separator

    def _switch_context(self, context: str):
        """Switch between NLTHA and Pushover contexts."""
        current_ctx = self.controller.get_active_context().value
        logger.debug("_switch_context called: '%s' -> '%s'", current_ctx, context)

        if self.controller.get_active_context().value == context:
            logger.debug("Context already '%s', no change", context)
            return  # Already active

        self.controller.set_active_context(context)
        logger.debug("Context switched to '%s'", context)

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

    def _update_tab_styling(self):
        """Update tab button styling based on active state."""
        for tab_btn in [self.nltha_tab, self.pushover_tab]:
            is_active = tab_btn.isChecked()
            tab_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS['muted'] if not is_active else COLORS['accent']};
                    border: none;
                    border-bottom: 2px solid {'transparent' if not is_active else COLORS['accent']};
                    border-radius: 0px;
                    padding: 4px 16px;
                    font-size: 15px;
                    font-weight: 500;
                    letter-spacing: 0.3px;
                }}
                QPushButton:hover {{
                    color: {COLORS['text'] if not is_active else COLORS['accent']};
                    background-color: transparent;
                }}
                QPushButton:checked {{
                    color: {COLORS['accent']};
                    border-bottom: 2px solid {COLORS['accent']};
                    border-radius: 0px;
                    font-weight: 500;
                }}
            """)

    def _create_content_area(self) -> QWidget:
        """Create content area with table and plots."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        # Content header with result type title
        content_header = QWidget()
        content_header.setFixedHeight(32)
        content_header_layout = QHBoxLayout(content_header)
        content_header_layout.setContentsMargins(4, 2, 4, 2)
        content_header_layout.setSpacing(8)

        # Content title - prominent main section title
        self.content_title = create_styled_label("Select a result type", "header")
        self.content_title.setStyleSheet("font-size: 18px; font-weight: 600;")
        content_header_layout.addWidget(self.content_title)

        content_header_layout.addStretch()

        layout.addWidget(content_header, stretch=0)
        layout.addSpacing(8)  # Spacing below main section title

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

        # Comparison Joint Scatter widget (initially hidden)
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
                border: none;
                gridline-color: #1e2329;
                color: {COLORS['text']};
            }}
            QTableWidget::item {{
                padding: 4px 8px;
                border: none;
            }}
            QHeaderView {{
                background-color: {COLORS['card']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['accent']};
                padding: 4px 4px;
                border: none;
                border-right: 1px solid #1e2329;
                border-bottom: 1px solid #1e2329;
                font-weight: 600;
                text-align: center;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
            QHeaderView::section:hover {{
                background-color: #1f2937;
                color: #67e8f9;
            }}
        """)
        self.beam_rotations_table.verticalHeader().setVisible(False)
        self.beam_rotations_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.beam_rotations_table.hide()
        layout.addWidget(self.beam_rotations_table)

        # Pushover Curve View widget (initially hidden)
        self.pushover_curve_view = PushoverCurveView()
        self.pushover_curve_view.hide()
        layout.addWidget(self.pushover_curve_view)

        return widget

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

    # -------------------------------------------------------------------------
    # Event handlers - delegate to event_handlers module
    # -------------------------------------------------------------------------

    def on_browser_selection_changed(self, result_set_id: int, category: str, result_type: str, direction: str, element_id: int = 0):
        """Handle browser selection changes."""
        event_handlers.on_browser_selection_changed(
            self, result_set_id, category, result_type, direction, element_id
        )

    def on_comparison_selected(self, comparison_set_id: int, result_type: str, direction: str):
        """Handle comparison set selection."""
        event_handlers.on_comparison_selected(self, comparison_set_id, result_type, direction)

    def on_comparison_element_selected(self, comparison_set_id: int, result_type: str, element_id: int, direction: str):
        """Handle comparison element selection."""
        event_handlers.on_comparison_element_selected(
            self, comparison_set_id, result_type, element_id, direction
        )

    # -------------------------------------------------------------------------
    # View loaders - delegate to view_loaders module
    # -------------------------------------------------------------------------

    def load_standard_dataset(self, result_type: str, direction: str, result_set_id: int) -> None:
        """Load and display directional results for the selected type."""
        view_loaders.load_standard_dataset(self, result_type, direction, result_set_id)

    def load_element_dataset(self, element_id: int, result_type: str, direction: str, result_set_id: int) -> None:
        """Load and display element-specific results."""
        view_loaders.load_element_dataset(self, element_id, result_type, direction, result_set_id)

    def load_joint_dataset(self, result_type: str, result_set_id: int) -> None:
        """Load and display joint-level results."""
        view_loaders.load_joint_dataset(self, result_type, result_set_id)

    def load_maxmin_dataset(self, result_set_id: int, base_result_type: str = "Drifts"):
        """Load and display absolute Max/Min drift results."""
        view_loaders.load_maxmin_dataset(self, result_set_id, base_result_type)

    def load_element_maxmin_dataset(self, element_id: int, result_set_id: int, base_result_type: str = "WallShears"):
        """Load and display element-specific Max/Min results."""
        view_loaders.load_element_maxmin_dataset(self, element_id, result_set_id, base_result_type)

    def load_all_rotations(self, result_set_id: int):
        """Load and display all quad rotations."""
        view_loaders.load_all_rotations(self, result_set_id)

    def load_all_column_rotations(self, result_set_id: int):
        """Load and display all column rotations."""
        view_loaders.load_all_column_rotations(self, result_set_id)

    def load_all_beam_rotations(self, result_set_id: int):
        """Load and display all beam rotations."""
        view_loaders.load_all_beam_rotations(self, result_set_id)

    def load_beam_rotations_table(self, result_set_id: int):
        """Load and display beam rotations table."""
        view_loaders.load_beam_rotations_table(self, result_set_id)

    def load_all_soil_pressures(self, result_set_id: int):
        """Load and display all soil pressures as bar chart."""
        view_loaders.load_all_soil_pressures(self, result_set_id)

    def load_soil_pressures_table(self, result_set_id: int):
        """Load and display soil pressures table."""
        view_loaders.load_soil_pressures_table(self, result_set_id)

    def load_all_vertical_displacements(self, result_set_id: int):
        """Load and display all vertical displacements."""
        view_loaders.load_all_vertical_displacements(self, result_set_id)

    def load_vertical_displacements_table(self, result_set_id: int):
        """Load and display vertical displacements table."""
        view_loaders.load_vertical_displacements_table(self, result_set_id)

    def load_pushover_curve(self, case_name: str):
        """Load and display a pushover curve."""
        view_loaders.load_pushover_curve(self, case_name)

    def load_all_pushover_curves(self, direction: str):
        """Load and display all pushover curves for a given direction."""
        view_loaders.load_all_pushover_curves(self, direction)

    def load_comparison_all_rotations(self, comparison_set):
        """Load and display all quad rotations comparison."""
        view_loaders.load_comparison_all_rotations(self, comparison_set)

    def load_comparison_joint_scatter(self, comparison_set, result_type: str):
        """Load and display joint results comparison scatter plot."""
        view_loaders.load_comparison_joint_scatter(self, comparison_set, result_type)

    # -------------------------------------------------------------------------
    # Project data management
    # -------------------------------------------------------------------------

    def create_comparison_set(self):
        """Open dialog to create a new comparison set."""
        from gui.comparison_set_dialog import ComparisonSetDialog
        from database.repository import ComparisonSetRepository
        from PyQt6.QtWidgets import QMessageBox

        result_sets = self.result_set_repo.get_by_project(self.project_id)

        if len(result_sets) < 2:
            QMessageBox.warning(
                self,
                "Insufficient Result Sets",
                "You need at least 2 result sets to create a comparison.\n\n"
                "Please import more result sets first."
            )
            return

        from gui.ui_helpers import show_dialog_with_blur
        dialog = ComparisonSetDialog(self.project_id, result_sets, self.session, self)
        if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
            data = dialog.get_comparison_data()

            comparison_repo = ComparisonSetRepository(self.session)
            if comparison_repo.check_duplicate(self.project_id, data['name']):
                QMessageBox.warning(
                    self,
                    "Duplicate Name",
                    f"A comparison set named '{data['name']}' already exists.\n"
                    "Please choose a different name."
                )
                return

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

                self.load_project_data()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create comparison set:\n{str(e)}"
                )

    def _get_available_result_types(self, result_sets):
        """Check which result types have data for each result set."""
        from database.models import GlobalResultsCache, ElementResultsCache, JointResultsCache

        available_types = {}

        for result_set in result_sets:
            types_for_set = set()

            global_types = (
                self.session.query(GlobalResultsCache.result_type)
                .filter(GlobalResultsCache.result_set_id == result_set.id)
                .distinct()
                .all()
            )
            for (result_type,) in global_types:
                types_for_set.add(result_type)

            element_types = (
                self.session.query(ElementResultsCache.result_type)
                .filter(ElementResultsCache.result_set_id == result_set.id)
                .distinct()
                .all()
            )
            for (result_type,) in element_types:
                base_type = result_type.split('_')[0]
                types_for_set.add(base_type)

            joint_types = (
                self.session.query(JointResultsCache.result_type)
                .filter(JointResultsCache.result_set_id == result_set.id)
                .distinct()
                .all()
            )
            for (result_type,) in joint_types:
                types_for_set.add(result_type)
                base_type = result_type.split('_')[0]
                types_for_set.add(base_type)

            available_types[result_set.id] = types_for_set

        return available_types

    def load_project_data(self):
        """Load project data and populate browser."""
        from database.repository import ComparisonSetRepository, PushoverCaseRepository

        self.session.expire_all()
        self.result_service.invalidate_all()
        self.controller.reset_pushover_mapping()
        try:
            result_sets = self.result_set_repo.get_by_project(self.project_id)

            if result_sets and not self.controller.selection.result_set_id:
                self.controller.update_selection(result_set_id=result_sets[0].id)

            stories = self.story_repo.get_by_project(self.project_id)
            elements = self.element_repo.get_by_project(self.project_id)

            comparison_set_repo = ComparisonSetRepository(self.session)
            comparison_sets = comparison_set_repo.get_by_project(self.project_id)

            pushover_repo = PushoverCaseRepository(self.session)
            pushover_cases = {}
            logger.debug("Checking %s result sets for pushover analysis type", len(result_sets))
            for rs in result_sets:
                analysis_type = getattr(rs, 'analysis_type', None)
                logger.debug("Result set %s (%s): analysis_type=%s", rs.id, rs.name, analysis_type)
                if analysis_type == 'Pushover':
                    cases = pushover_repo.get_by_result_set(rs.id)
                    logger.debug("Found %s pushover cases for result set %s", len(cases) if cases else 0, rs.id)
                    if cases:
                        pushover_cases[rs.id] = cases
                        self.controller.get_pushover_mapping(rs.id)

            available_result_types = self._get_available_result_types(result_sets)

            self.browser.populate_tree(result_sets, stories, elements, available_result_types, comparison_sets, pushover_cases)

            logger.info(
                "Loaded project: %s (%d stories, %d result sets, %d comparisons, %d elements)",
                self.project_name, len(stories), len(result_sets), len(comparison_sets), len(elements)
            )
        except Exception as e:
            logger.error("Error loading project data: %s", str(e))

    # -------------------------------------------------------------------------
    # Import dialogs
    # -------------------------------------------------------------------------

    def load_data_from_folder(self):
        """Load data from folder into current project."""
        from PyQt6.QtWidgets import QMessageBox
        from gui.folder_import_dialog import FolderImportDialog
        from gui.ui_helpers import show_dialog_with_blur

        dialog = FolderImportDialog(self, context=self.context)

        if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
            self.session.expire_all()
            result_set_id = getattr(dialog, "last_result_set_id", None)
            if result_set_id:
                self.result_service.invalidate_result_set(result_set_id)
            else:
                self.result_service.invalidate_all()
            self.load_project_data()

            sel = self.controller.selection
            if sel.result_type and sel.result_set_id:
                if sel.result_type.startswith("MaxMin"):
                    base_type = self._extract_base_result_type(sel.result_type)
                    self.result_service.invalidate_maxmin_dataset(sel.result_set_id, base_type)
                    self.load_maxmin_dataset(sel.result_set_id, base_type)
                elif sel.element_id > 0:
                    self.result_service.invalidate_element_dataset(
                        sel.element_id, sel.result_type, sel.direction, sel.result_set_id
                    )
                    self.load_element_dataset(sel.element_id, sel.result_type, sel.direction, sel.result_set_id)
                else:
                    self.result_service.invalidate_standard_dataset(sel.result_type, sel.direction, sel.result_set_id)
                    self.load_standard_dataset(sel.result_type, sel.direction, sel.result_set_id)

            QMessageBox.information(
                self,
                "Load Complete",
                f"Successfully loaded data into project: {self.project_name}\n\n"
                f"The results browser has been refreshed."
            )

    def load_pushover_curves(self):
        """Load pushover curves from Excel file."""
        from PyQt6.QtWidgets import QMessageBox
        from gui.pushover_import_dialog import PushoverImportDialog
        from gui.ui_helpers import show_dialog_with_blur

        dialog = PushoverImportDialog(
            project_id=self.project.id,
            project_name=self.project_name,
            session=self.session,
            parent=self
        )

        dialog.import_completed.connect(lambda stats: self._on_pushover_import_completed(stats))

        show_dialog_with_blur(dialog, self)

    def _on_pushover_import_completed(self, stats: dict):
        """Handle pushover import completion."""
        self.session.expire_all()
        result_set_id = stats.get("result_set_id")
        if result_set_id:
            self.result_service.invalidate_result_set(result_set_id)
        else:
            self.result_service.invalidate_all()
        self.load_project_data()
        logger.info("Imported %d pushover curves into %s", stats['curves_imported'], stats['result_set_name'])

    def load_pushover_results(self):
        """Load pushover global results from folder."""
        from PyQt6.QtWidgets import QFileDialog, QMessageBox
        from gui.pushover_global_import_dialog import PushoverGlobalImportDialog
        from gui.ui_helpers import show_dialog_with_blur

        folder_path = QFileDialog.getExistingDirectory(
            self,
            "Select Folder with Pushover Global Results",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if not folder_path:
            return

        try:
            dialog = PushoverGlobalImportDialog(
                project_id=self.project.id,
                project_name=self.project_name,
                folder_path=folder_path,
                session=self.session,
                parent=self
            )

            dialog.import_completed.connect(lambda stats: self._on_pushover_global_import_completed(stats))

            show_dialog_with_blur(dialog, self)

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
        self.session.expire_all()
        result_set_id = stats.get("result_set_id")
        if result_set_id:
            self.result_service.invalidate_result_set(result_set_id)
        else:
            self.result_service.invalidate_all()
        self.load_project_data()
        logger.info("Imported pushover global results: %d result types", stats.get('result_types_imported', 0))

    # -------------------------------------------------------------------------
    # Export methods
    # -------------------------------------------------------------------------

    def export_results(self):
        """Export results to file - contextual based on active mode."""
        if self.controller.get_active_context() == AnalysisType.PUSHOVER:
            self.export_pushover_results()
        else:
            self.export_nltha_results()

    def export_nltha_results(self):
        """Export NLTHA results."""
        from gui.export_dialog import ComprehensiveExportDialog

        result_set_id = self.controller.selection.result_set_id
        if not result_set_id:
            result_sets = self.result_set_repo.get_by_project(self.project_id)
            if result_sets:
                result_set_id = result_sets[0].id
                self.controller.update_selection(result_set_id=result_set_id)
            else:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "No Data", "No result sets available in this project")
                return

        from gui.ui_helpers import show_dialog_with_blur
        dialog = ComprehensiveExportDialog(
            context=self.context,
            result_service=self.result_service,
            current_result_set_id=result_set_id,
            project_name=self.project_name,
            analysis_context='NLTHA',
            parent=self
        )

        show_dialog_with_blur(dialog, self)

    def export_pushover_results(self):
        """Export pushover results."""
        from gui.export_dialog import ComprehensiveExportDialog
        from PyQt6.QtWidgets import QMessageBox

        result_set_id = self.controller.selection.result_set_id
        if not result_set_id:
            result_sets = self.result_set_repo.get_by_project(self.project_id)
            pushover_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', None) == 'Pushover']
            if pushover_sets:
                result_set_id = pushover_sets[0].id
                self.controller.update_selection(result_set_id=result_set_id)
            else:
                QMessageBox.warning(
                    self,
                    "No Pushover Data",
                    "No pushover result sets found in this project.\n\n"
                    "Please import pushover curves or global results first."
                )
                return

        from gui.ui_helpers import show_dialog_with_blur
        dialog = ComprehensiveExportDialog(
            context=self.context,
            result_service=self.result_service,
            current_result_set_id=result_set_id,
            project_name=self.project_name,
            analysis_context='Pushover',
            parent=self
        )

        show_dialog_with_blur(dialog, self)

    def export_project_excel(self):
        """Export complete project to Excel workbook."""
        from gui.export_dialog import ExportProjectExcelDialog

        dialog = ExportProjectExcelDialog(
            context=self.context,
            result_service=self.result_service,
            project_name=self.project_name,
            parent=self
        )

        dialog.exec()

    def _show_settings_popup(self):
        """Show the settings popup below the settings button."""
        popup = SettingsPopup(self)
        popup.show_below(self._settings_btn)

    def _on_settings_changed(self, key: str, value):
        """Handle global settings changes."""
        if key == "layout_borders_enabled":
            self._apply_layout_borders()

    def _apply_layout_borders(self):
        """Apply or remove layout borders based on settings."""
        border_color = COLORS['border']
        if settings.layout_borders_enabled:
            # Remove spacer below header
            self._header_spacer.setFixedHeight(0)

            # Header: bottom border with padding
            self._header_widget.setStyleSheet(f"""
                QWidget#projectHeader {{
                    background-color: {COLORS['background']};
                    border: none;
                    border-bottom: 1px solid {border_color};
                    padding-top: 4px;
                    padding-bottom: 4px;
                    min-height: 44px;
                    max-height: 44px;
                }}
            """)
            self._header_widget.setFixedHeight(44)

            # Use splitter handle as vertical separator (1px to match header border)
            self._main_splitter.setHandleWidth(1)
            self._main_splitter.setStyleSheet(f"""
                QSplitter#mainSplitter::handle {{
                    background-color: {border_color};
                    max-width: 1px;
                    min-width: 1px;
                }}
                QSplitter#mainSplitter::handle:hover {{
                    background-color: {COLORS['accent']};
                }}
            """)

            # Increase left margin on content area for spacing from border
            self._content_widget.layout().setContentsMargins(12, 4, 6, 4)
        else:
            # Restore spacer below header
            self._header_spacer.setFixedHeight(8)

            # Remove borders - restore original height
            self._header_widget.setStyleSheet(f"""
                QWidget#projectHeader {{
                    background-color: {COLORS['background']};
                    border: none;
                    min-height: 36px;
                    max-height: 36px;
                }}
            """)
            self._header_widget.setFixedHeight(36)

            # Restore transparent splitter handle
            self._main_splitter.setHandleWidth(1)
            self._main_splitter.setStyleSheet("""
                QSplitter#mainSplitter::handle {
                    background-color: transparent;
                    border: none;
                }
                QSplitter#mainSplitter::handle:hover {
                    background-color: rgba(74, 125, 137, 0.2);
                }
            """)

            # Restore original content margins
            self._content_widget.layout().setContentsMargins(6, 4, 6, 4)

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------

    def closeEvent(self, event):
        """Handle window close event - clean up all resources."""
        try:
            self._cleanup_resources()
            self._remove_from_parent_tracking()
        finally:
            event.accept()

    def _cleanup_resources(self) -> None:
        """Release DB/session/runtime resources on window close."""
        import gc
        import time

        project_name = getattr(self, "project_name", "Unknown")
        logger.debug("Closing project window: %s", project_name)

        db_path = self.context.db_path if getattr(self, "context", None) else None

        if getattr(self, "session", None):
            try:
                logger.debug("Rolling back and closing session...")
                self.session.rollback()
                self.session.close()
                logger.debug("Session closed successfully")
            except Exception as exc:
                logger.exception("Error closing session: %s", exc)
            finally:
                self.session = None

        if getattr(self, "runtime", None):
            try:
                logger.debug("Disposing runtime...")
                self.runtime.dispose()
                logger.debug("Runtime disposed successfully")
            except Exception as exc:
                logger.exception("Error disposing runtime: %s", exc)
            finally:
                self.runtime = None

        if getattr(self, "context", None):
            self.context = None

        logger.debug("Running garbage collection...")
        gc.collect()

        time.sleep(0.1)

        if db_path:
            logger.debug("Disposing database engine...")
            from database.base import dispose_project_engine
            dispose_project_engine(db_path)

        logger.debug("Project window closed successfully: %s", project_name)

    def _remove_from_parent_tracking(self) -> None:
        """Remove this window from parent tracking if present."""
        parent = self.parent()
        if not hasattr(parent, "_project_windows"):
            return
        parent_name = getattr(self, "project_name", None)
        if parent_name and parent_name in parent._project_windows:
            logger.debug("Removing %s from parent tracking...", parent_name)
            parent._project_windows.pop(parent_name, None)

    @staticmethod
    def _extract_base_result_type(result_type: str) -> str:
        """Return the base result type name from a MaxMin identifier."""
        if not result_type.startswith("MaxMin"):
            return result_type or "Drifts"
        base = result_type.replace("MaxMin", "", 1)
        return base or "Drifts"
