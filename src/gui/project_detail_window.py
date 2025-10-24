"""Project detail window - shows results browser and data visualization."""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QPushButton,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from database.base import get_session
from database.repository import (
    ProjectRepository,
    ResultSetRepository,
    CacheRepository,
    StoryRepository,
    LoadCaseRepository,
    AbsoluteMaxMinDriftRepository,
)
from processing.result_transformers import get_transformer
from .results_tree_browser import ResultsTreeBrowser
from .results_table_widget import ResultsTableWidget
from .results_plot_widget import ResultsPlotWidget
from .maxmin_drifts_widget import MaxMinDriftsWidget
from .ui_helpers import create_styled_button, create_styled_label
from .window_utils import enable_dark_title_bar
from .styles import COLORS


class ProjectDetailWindow(QMainWindow):
    """Project detail window with results browser, table, and plots."""

    def __init__(self, project_id: int, project_name: str, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.project_name = project_name
        self.session = get_session()

        # Repositories
        self.project_repo = ProjectRepository(self.session)
        self.result_set_repo = ResultSetRepository(self.session)
        self.cache_repo = CacheRepository(self.session)
        self.story_repo = StoryRepository(self.session)
        self.load_case_repo = LoadCaseRepository(self.session)
        self.abs_maxmin_repo = AbsoluteMaxMinDriftRepository(self.session)

        # Current selection
        self.current_result_type = None  # 'Drifts', 'Accelerations', 'Forces'
        self.current_result_set_id = None
        self.current_direction = 'X'  # Default to X direction

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

        # Content splitter (table | plots) - HORIZONTAL layout
        self.content_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setHandleWidth(8)  # Reduced gap between table and plot (was 16)
        self.content_splitter.setStyleSheet("""
            QSplitter {
                padding: 0px;
                margin: 0px;
            }
            QSplitter::handle {
                background-color: transparent;
                margin: 0px 4px;
            }
        """)

        # Table widget (compact, on left) - will size to content
        self.table_widget = ResultsTableWidget()
        self.content_splitter.addWidget(self.table_widget)

        # Plot widget (takes remaining space, on right)
        self.plot_widget = ResultsPlotWidget()
        self.content_splitter.addWidget(self.plot_widget)

        # Connect table load case selection to plot highlighting (multi-select)
        self.table_widget.selection_changed.connect(self.plot_widget.highlight_load_cases)

        # Connect hover signals for temporary highlighting
        self.table_widget.load_case_hovered.connect(self.plot_widget.hover_load_case)
        self.table_widget.hover_cleared.connect(self.plot_widget.clear_hover)

        # Table takes minimum needed space, plot takes all remaining
        self.content_splitter.setStretchFactor(0, 0)  # Table: don't stretch
        self.content_splitter.setStretchFactor(1, 1)  # Plot: take all remaining space

        layout.addWidget(self.content_splitter)

        # Max/Min Drifts widget (initially hidden)
        self.maxmin_widget = MaxMinDriftsWidget()
        self.maxmin_widget.hide()
        layout.addWidget(self.maxmin_widget)

        return widget

    def load_project_data(self):
        """Load project data and populate browser."""
        try:
            # Get result sets
            result_sets = self.result_set_repo.get_by_project(self.project_id)

            # Get stories
            stories = self.story_repo.get_by_project(self.project_id)

            # Populate browser
            self.browser.populate_tree(result_sets, stories)

            self.statusBar().showMessage(
                f"Loaded project: {self.project_name} "
                f"({len(stories)} stories, {len(result_sets)} result sets)"
            )
        except Exception as e:
            self.statusBar().showMessage(f"Error loading project data: {str(e)}")

    def on_browser_selection_changed(self, result_set_id: int, category: str, result_type: str, direction: str):
        """Handle browser selection changes.

        Args:
            result_set_id: ID of the selected result set
            category: Category name (e.g., "Envelopes")
            result_type: Result type (e.g., "Drifts", "Accelerations", "MaxMinDrifts")
            direction: Direction ('X' or 'Y', empty for MaxMinDrifts)
        """
        self.current_result_set_id = result_set_id
        self.current_result_type = result_type
        self.current_direction = direction

        if result_type and result_set_id:
            # Check if this is MaxMinDrifts
            if result_type == "MaxMinDrifts":
                self.content_title.setText("› Max/Min Drifts")
                # Hide regular table/plot, show MaxMin widget
                self.content_splitter.hide()
                self.maxmin_widget.show()
                self.load_maxmin_results(result_set_id)
            else:
                # Regular result type with direction
                # Hide MaxMin widget, show regular table/plot
                self.maxmin_widget.hide()
                self.content_splitter.show()

                # Map result type to display name
                display_name = result_type
                if result_type == "Drifts":
                    display_name = f"Interstorey Drifts - {direction} Direction"
                elif result_type == "Accelerations":
                    display_name = f"Accelerations - {direction} Direction"
                elif result_type == "Forces":
                    display_name = f"Shears - {direction} Direction"
                elif result_type == "Displacements":
                    display_name = f"Displacements - {direction} Direction"

                self.content_title.setText(f"› {display_name}")

                # Combine result type and direction for config lookup
                result_type_key = f"{result_type}_{direction}"
                self.load_results(result_type_key, result_set_id)
        else:
            self.content_title.setText("Select a result type")
            self.maxmin_widget.hide()
            self.content_splitter.show()
            self.table_widget.clear_data()
            self.plot_widget.clear_plots()

    def load_results(self, result_type: str, result_set_id: int):
        """Load and display results for the selected type.

        Args:
            result_type: Type of results to load (e.g., "Drifts_X", "Drifts_Y", "Accelerations_X")
            result_set_id: ID of the result set to filter by
        """
        try:
            # Extract base result type for cache query (remove _X or _Y suffix)
            base_result_type = result_type.replace('_X', '').replace('_Y', '')

            # Get cache data for display using base type
            cache_entries = self.cache_repo.get_cache_for_display(
                project_id=self.project_id,
                result_type=base_result_type,
                result_set_id=result_set_id,
            )

            if not cache_entries:
                self.statusBar().showMessage(f"No data available for {result_type}")
                self.table_widget.clear_data()
                self.plot_widget.clear_plots()
                return

            # Convert cache to table format
            import pandas as pd

            # Build DataFrame from cache
            # cache_entries is a list of tuples: (GlobalResultsCache, Story)
            story_names = []
            data_dicts = []

            for cache_entry, story in cache_entries:
                story_names.append(story.name)  # Use actual story name from database
                data_dicts.append(cache_entry.results_matrix)

            # Create DataFrame
            df = pd.DataFrame(data_dicts)

            # Transform data using result-type-specific transformer (with direction)
            transformer = get_transformer(result_type)
            df = transformer.transform(df)

            # Insert Story column at the beginning
            df.insert(0, 'Story', story_names)

            # TEMPORARY FIX: Reverse DataFrame for existing data with old sort_order
            # TODO: Remove this reversal after re-importing data with corrected sort_order
            # This ensures lower floors appear at bottom of plot (Y=0), upper floors at top
            df = df.iloc[::-1].reset_index(drop=True)

            # Update table
            self.table_widget.load_data(df, result_type)

            # Update plots
            self.plot_widget.load_data(df, result_type)

            self.statusBar().showMessage(
                f"Loaded {len(cache_entries)} stories for {result_type}"
            )

        except Exception as e:
            self.statusBar().showMessage(f"Error loading results: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_maxmin_results(self, result_set_id: int):
        """Load and display absolute Max/Min drift results from database.

        Args:
            result_set_id: ID of the result set to filter by
        """
        try:
            import pandas as pd

            # Get absolute max/min drifts from database
            abs_drifts = self.abs_maxmin_repo.get_by_result_set(
                project_id=self.project_id,
                result_set_id=result_set_id
            )

            if not abs_drifts:
                self.statusBar().showMessage("No absolute max/min drift data available")
                self.maxmin_widget.clear_data()
                return

            # Get stories for ordering
            stories = self.story_repo.get_by_project(self.project_id)
            story_dict = {s.id: s for s in stories}

            # Organize data by story and load case
            # We need to create a structure that matches the widget's expectations:
            # DataFrame with columns: Story, Max_LC1_X, Min_LC1_X, Max_LC2_X, ...

            data_by_story = {}

            for drift in abs_drifts:
                story_id = drift.story_id
                if story_id not in data_by_story:
                    data_by_story[story_id] = {'Story': story_dict[story_id].name}

                # Get load case name
                load_case = self.load_case_repo.get_by_id(drift.load_case_id)

                # Store BOTH original Max and Min values (not just the absolute max)
                # This ensures we display the actual data from the analysis
                col_max = f"Max_{load_case.name}_{drift.direction}"
                col_min = f"Min_{load_case.name}_{drift.direction}"

                # Convert to percentage and store original values
                data_by_story[story_id][col_max] = drift.original_max * 100.0
                data_by_story[story_id][col_min] = drift.original_min * 100.0

            # Convert to DataFrame (sorted by sort_order ascending = bottom to top)
            df_list = []
            for story_id in sorted(data_by_story.keys(), key=lambda x: story_dict[x].sort_order or 0):
                df_list.append(data_by_story[story_id])

            df_maxmin = pd.DataFrame(df_list)

            # TEMPORARY FIX: Reverse DataFrame for existing data with old sort_order
            # TODO: Remove this reversal after re-importing data with corrected sort_order
            # This ensures lower floors appear at bottom of plot (Y=0), upper floors at top
            df_maxmin = df_maxmin.iloc[::-1].reset_index(drop=True)

            # Load into MaxMin widget
            self.maxmin_widget.load_data(df_maxmin, "MaxMinDrifts")

            self.statusBar().showMessage(
                f"Loaded absolute max/min drifts for {len(abs_drifts)} records"
            )

        except Exception as e:
            self.statusBar().showMessage(f"Error loading Max/Min results: {str(e)}")
            import traceback
            traceback.print_exc()

    def load_data_from_folder(self):
        """Load data from folder into current project."""
        from PyQt6.QtWidgets import QMessageBox
        from .folder_import_dialog import FolderImportDialog

        # Create a modified dialog that uses the current project
        dialog = FolderImportDialog(self)

        # Pre-fill project name with current project
        dialog.project_input.setText(self.project_name)
        dialog.project_input.setEnabled(False)  # Don't allow changing project name

        if dialog.exec():
            # Data was imported, refresh the view
            self.load_project_data()

            # Reload current result if selected
            if self.current_result_type and self.current_result_set_id:
                self.load_results(self.current_result_type, self.current_result_set_id)

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
            # Check if it's MaxMinDrifts
            if self.current_result_type == "MaxMinDrifts":
                self.load_maxmin_results(self.current_result_set_id)
                self.statusBar().showMessage("Max/Min drifts data reloaded", 3000)
            else:
                # Regular result type
                result_type_key = f"{self.current_result_type}_{self.current_direction}"
                self.load_results(result_type_key, self.current_result_set_id)
                self.statusBar().showMessage(f"{self.current_result_type} data reloaded", 3000)

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
