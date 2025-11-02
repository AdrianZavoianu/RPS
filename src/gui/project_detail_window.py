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
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
import pandas as pd

from database.repository import (
    ProjectRepository,
    ResultSetRepository,
    CacheRepository,
    StoryRepository,
    LoadCaseRepository,
    AbsoluteMaxMinDriftRepository,
    ElementRepository,
    ElementCacheRepository,
)
from processing.result_service import ResultDataService
from .results_tree_browser import ResultsTreeBrowser
from .maxmin_drifts_widget import MaxMinDriftsWidget
from .all_rotations_widget import AllRotationsWidget
from .result_views import StandardResultView
from .ui_helpers import create_styled_button, create_styled_label
from .window_utils import enable_dark_title_bar
from .styles import COLORS
from services.project_service import ProjectContext
from utils.color_utils import get_gradient_color
from config.result_config import RESULT_CONFIGS


class ProjectDetailWindow(QMainWindow):
    """Project detail window with results browser, table, and plots."""

    def __init__(self, context: ProjectContext, parent=None):
        super().__init__(parent)
        self.context = context
        self.session = context.session()

        # Repositories
        self.project_repo = ProjectRepository(self.session)
        self.result_set_repo = ResultSetRepository(self.session)
        self.cache_repo = CacheRepository(self.session)
        self.story_repo = StoryRepository(self.session)
        self.load_case_repo = LoadCaseRepository(self.session)
        self.abs_maxmin_repo = AbsoluteMaxMinDriftRepository(self.session)
        self.element_repo = ElementRepository(self.session)
        self.element_cache_repo = ElementCacheRepository(self.session)

        project = self.project_repo.get_by_name(context.name)
        if not project:
            raise ValueError(f"Project '{context.name}' is not initialized in its database.")

        self.project = project
        self.project_id = project.id
        self.project_name = project.name

        self.result_service = ResultDataService(
            project_id=self.project_id,
            cache_repo=self.cache_repo,
            story_repo=self.story_repo,
            load_case_repo=self.load_case_repo,
            abs_maxmin_repo=self.abs_maxmin_repo,
            element_cache_repo=self.element_cache_repo,
            element_repo=self.element_repo,
            session=self.session,
        )

        # Current selection
        self.current_result_type = None  # 'Drifts', 'Accelerations', 'Forces', 'WallShears'
        self.current_result_set_id = None
        self.current_direction = 'X'  # Default to X direction
        self.current_element_id = 0  # 0 = global results, >0 = specific element

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
        """Create header bar with project info and controls."""
        header = QWidget()
        header.setObjectName("projectHeader")
        header.setFixedHeight(64)  # Fixed height for stability
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

        # Project name
        title = create_styled_label(f"▸ {self.project_name}", "header")
        layout.addWidget(title)

        layout.addStretch()

        # Reload Data button
        reload_btn = create_styled_button("⟳ Reload", "secondary", "sm")
        reload_btn.setToolTip("Reload current result set data")
        reload_btn.clicked.connect(self.reload_current_data)
        layout.addWidget(reload_btn)

        # Load Data button
        load_data_btn = create_styled_button("Load Data", "primary", "sm")
        load_data_btn.setToolTip("Import new data from folder")
        load_data_btn.clicked.connect(self.load_data_from_folder)
        layout.addWidget(load_data_btn)

        # Export button
        export_btn = create_styled_button("Export Results", "secondary", "sm")
        export_btn.setToolTip("Export results to file")
        export_btn.clicked.connect(self.export_results)
        layout.addWidget(export_btn)

        # Close button
        close_btn = create_styled_button("Close", "ghost", "sm")
        close_btn.clicked.connect(self.close)
        layout.addWidget(close_btn)

        return header

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

        # Max/Min Drifts widget (initially hidden)
        self.maxmin_widget = MaxMinDriftsWidget()
        self.maxmin_widget.hide()
        layout.addWidget(self.maxmin_widget)

        # All Rotations widget (initially hidden)
        self.all_rotations_widget = AllRotationsWidget()
        self.all_rotations_widget.hide()
        layout.addWidget(self.all_rotations_widget)

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

        return widget

    def _get_available_result_types(self, result_sets):
        """Check which result types have data for each result set.

        Returns:
            Dict mapping result_set_id to set of available result types
        """
        from database.models import GlobalResultsCache, ElementResultsCache

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

            available_types[result_set.id] = types_for_set

        return available_types

    def load_project_data(self):
        """Load project data and populate browser."""
        self.session.expire_all()
        self.result_service.invalidate_all()
        try:
            # Get result sets
            result_sets = self.result_set_repo.get_by_project(self.project_id)

            # Get stories
            stories = self.story_repo.get_by_project(self.project_id)

            # Get elements (walls, columns, beams, etc.)
            elements = self.element_repo.get_by_project(self.project_id)

            # Check which result types have data for each result set
            available_result_types = self._get_available_result_types(result_sets)

            # Populate browser
            self.browser.populate_tree(result_sets, stories, elements, available_result_types)

            self.statusBar().showMessage(
                f"Loaded project: {self.project_name} "
                f"({len(stories)} stories, {len(result_sets)} result sets, {len(elements)} elements)"
            )
        except Exception as e:
            self.statusBar().showMessage(f"Error loading project data: {str(e)}")

    def on_browser_selection_changed(self, result_set_id: int, category: str, result_type: str, direction: str, element_id: int = 0):
        """Handle browser selection changes.

        Args:
            result_set_id: ID of the selected result set
            category: Category name (e.g., "Envelopes")
            result_type: Result type (e.g., "Drifts", "Accelerations", "WallShears")
            direction: Direction ('X', 'Y', 'V22', 'V33', empty for MaxMin)
            element_id: Element ID for element-specific results (0 for global results, -1 for all elements)
        """
        self.current_result_set_id = result_set_id
        self.current_result_type = result_type
        self.current_direction = direction
        self.current_element_id = element_id

        if result_type and result_set_id:
            if result_type == "AllQuadRotations":
                # All rotations scatter plot view (both Max and Min)
                self.standard_view.hide()
                self.maxmin_widget.hide()
                self.all_rotations_widget.show()
                self.beam_rotations_table.hide()
                self.load_all_rotations(result_set_id)
            elif result_type == "AllColumnRotations":
                # All column rotations scatter plot view (both Max and Min)
                self.standard_view.hide()
                self.maxmin_widget.hide()
                self.all_rotations_widget.show()
                self.beam_rotations_table.hide()
                self.load_all_column_rotations(result_set_id)
            elif result_type == "AllBeamRotations":
                # All beam rotations scatter plot view (both Max and Min)
                self.standard_view.hide()
                self.maxmin_widget.hide()
                self.all_rotations_widget.show()
                self.beam_rotations_table.hide()
                self.load_all_beam_rotations(result_set_id)
            elif result_type == "BeamRotationsTable":
                # Beam rotations wide-format table view (all beams, all load cases)
                self.standard_view.hide()
                self.maxmin_widget.hide()
                self.all_rotations_widget.hide()
                self.beam_rotations_table.show()
                self.load_beam_rotations_table(result_set_id)
            elif result_type.startswith("MaxMin") and element_id > 0:
                # Element-specific max/min results (pier shears max/min)
                self.standard_view.hide()
                self.all_rotations_widget.hide()
                self.beam_rotations_table.hide()
                self.maxmin_widget.show()
                base_type = self._extract_base_result_type(result_type)
                self.load_element_maxmin_dataset(element_id, result_set_id, base_type)
            elif result_type.startswith("MaxMin"):
                # Global max/min results (story drifts, forces, etc.)
                self.standard_view.hide()
                self.all_rotations_widget.hide()
                self.beam_rotations_table.hide()
                self.maxmin_widget.show()
                base_type = self._extract_base_result_type(result_type)
                self.load_maxmin_dataset(result_set_id, base_type)
            elif element_id > 0:
                # Element-specific directional results (pier shears V2/V3, etc.)
                self.maxmin_widget.hide()
                self.all_rotations_widget.hide()
                self.beam_rotations_table.hide()
                self.standard_view.show()
                self.load_element_dataset(element_id, result_type, direction, result_set_id)
            else:
                # Global directional results (story drifts X/Y, forces, etc.)
                self.maxmin_widget.hide()
                self.all_rotations_widget.hide()
                self.beam_rotations_table.hide()
                self.standard_view.show()
                self.load_standard_dataset(result_type, direction, result_set_id)
        else:
            self.content_title.setText("Select a result type")
            self.maxmin_widget.hide()
            self.all_rotations_widget.hide()
            self.beam_rotations_table.hide()
            self.standard_view.show()
            self.standard_view.clear()

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

            self.content_title.setText(f"> {dataset.meta.display_name}")
            self.standard_view.set_dataset(dataset)

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
            dataset = self.result_service.get_element_dataset(element_id, result_type, direction, result_set_id)

            if not dataset:
                self.standard_view.clear()
                self.statusBar().showMessage(
                    f"No data available for element results"
                )
                return

            self.content_title.setText(f"> {dataset.meta.display_name}")
            self.standard_view.set_dataset(dataset)

            story_count = len(dataset.data.index)
            self.statusBar().showMessage(
                f"Loaded {story_count} stories for {dataset.meta.display_name}"
            )

        except Exception as exc:
            self.standard_view.clear()
            self.statusBar().showMessage(f"Error loading element results: {str(exc)}")
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

            self.all_rotations_widget.set_title("All Quad Rotations Distribution")
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

            self.all_rotations_widget.set_title("All Column Rotations Distribution")
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

            self.all_rotations_widget.set_title("All Beam R3 Plastic Rotations Distribution")
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

    def load_beam_rotations_table(self, result_set_id: int):
        """Load and display beam rotations table in wide format (all beams, all load cases).

        Args:
            result_set_id: ID of the result set
        """
        try:
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

            # Set column headers
            self.beam_rotations_table.setHorizontalHeaderLabels(df.columns.tolist())

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

    def load_data_from_folder(self):
        """Load data from folder into current project."""
        from PyQt6.QtWidgets import QMessageBox
        from .folder_import_dialog import FolderImportDialog

        # Create a modified dialog that uses the current project
        dialog = FolderImportDialog(self, context=self.context)

        if dialog.exec():
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

    def reload_current_data(self):
        """Reload the currently displayed result data."""
        if not self.current_result_type or not self.current_result_set_id:
            self.statusBar().showMessage("No result selected to reload")
            return

        try:
            # Check if it's element max/min
            if self.current_result_type.startswith("MaxMin") and self.current_element_id > 0:
                base_type = self._extract_base_result_type(self.current_result_type)
                self.load_element_maxmin_dataset(self.current_element_id, self.current_result_set_id, base_type)
                self.statusBar().showMessage(f"Element Max/Min {base_type} data reloaded", 3000)
            elif self.current_result_type.startswith("MaxMin"):
                # Global max/min
                base_type = self._extract_base_result_type(self.current_result_type)
                self.result_service.invalidate_maxmin_dataset(self.current_result_set_id, base_type)
                self.load_maxmin_dataset(self.current_result_set_id, base_type)
                self.statusBar().showMessage(f"Max/Min {base_type.lower()} data reloaded", 3000)
            elif self.current_element_id > 0:
                # Element-specific result type
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
                direction_suffix = f" ({self.current_direction})" if self.current_direction else ""
                self.statusBar().showMessage(
                    f"Element {self.current_result_type}{direction_suffix} data reloaded", 3000
                )
            else:
                # Regular global result type
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
                direction_suffix = f" ({self.current_direction})" if self.current_direction else ""
                self.statusBar().showMessage(
                    f"{self.current_result_type}{direction_suffix} data reloaded", 3000
                )

        except Exception as e:
            self.statusBar().showMessage(f"Error reloading data: {str(e)}")
            import traceback
            traceback.print_exc()

    def export_results(self):
        """Export current results to Excel."""
        # TODO: Implement export functionality
        self.statusBar().showMessage("Export functionality coming soon...")

    def closeEvent(self, event):
        """Handle window close event."""
        if self.session:
            self.session.close()
        event.accept()

    @staticmethod
    def _extract_base_result_type(result_type: str) -> str:
        """Return the base result type name from a MaxMin identifier."""
        if not result_type.startswith("MaxMin"):
            return result_type or "Drifts"
        base = result_type.replace("MaxMin", "", 1)
        return base or "Drifts"
