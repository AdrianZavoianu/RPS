"""Project detail window - shows results browser and data visualization."""

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QComboBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon

from database.base import get_session
from database.repository import (
    ProjectRepository,
    ResultSetRepository,
    CacheRepository,
    StoryRepository,
)
from .results_tree_browser import ResultsTreeBrowser
from .results_table_widget import ResultsTableWidget
from .results_plot_widget import ResultsPlotWidget
from .ui_helpers import create_styled_button, create_styled_label
from .window_utils import enable_dark_title_bar


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

        # Current selection
        self.current_result_type = None  # 'Drifts', 'Accelerations', 'Forces'
        self.current_result_set_id = None

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
        header.setFixedHeight(56)  # Fixed height for stability
        header.setStyleSheet("""
            QWidget#projectHeader {
                background-color: #161b22;
                border-bottom: 1px solid #2c313a;
                min-height: 56px;
                max-height: 56px;
            }
        """)

        layout = QHBoxLayout(header)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(12)

        # Project name
        title = create_styled_label(f"📊 {self.project_name}", "header")
        layout.addWidget(title)

        layout.addStretch()

        # Load Data button
        load_data_btn = create_styled_button("Load Data", "primary", "sm")
        load_data_btn.clicked.connect(self.load_data_from_folder)
        layout.addWidget(load_data_btn)

        # Export button
        export_btn = create_styled_button("Export Results", "secondary", "sm")
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

        # Content header with result type selector
        content_header = QWidget()
        content_header.setFixedHeight(40)  # Fixed height to prevent shifts
        content_header_layout = QHBoxLayout(content_header)
        content_header_layout.setContentsMargins(8, 4, 8, 4)
        content_header_layout.setSpacing(12)

        self.content_title = create_styled_label("Select a result type", "subheader")
        content_header_layout.addWidget(self.content_title)

        content_header_layout.addStretch()

        # View mode toggle (table/plot)
        view_label = QLabel("View:")
        view_label.setStyleSheet("color: #7f8b9a; font-size: 13px;")
        content_header_layout.addWidget(view_label)

        self.view_mode_combo = QComboBox()
        self.view_mode_combo.addItems(["Table + Plot", "Table Only", "Plot Only"])
        self.view_mode_combo.currentTextChanged.connect(self.on_view_mode_changed)
        self.view_mode_combo.setFixedHeight(32)
        self.view_mode_combo.setStyleSheet("""
            QComboBox {
                background-color: #161b22;
                border: 1px solid #2c313a;
                border-radius: 4px;
                padding: 4px 8px;
                color: #d1d5db;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #4a7d89;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        content_header_layout.addWidget(self.view_mode_combo)

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

        # Table takes minimum needed space, plot takes all remaining
        self.content_splitter.setStretchFactor(0, 0)  # Table: don't stretch
        self.content_splitter.setStretchFactor(1, 1)  # Plot: take all remaining space

        layout.addWidget(self.content_splitter)

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

    def on_browser_selection_changed(self, selection_type: str, result_type: str = None):
        """Handle browser selection changes."""
        self.current_result_type = result_type

        if result_type:
            self.content_title.setText(f"📈 {result_type}")
            self.load_results(result_type)
        else:
            self.content_title.setText("Select a result type")
            self.table_widget.clear_data()
            self.plot_widget.clear_plots()

    def load_results(self, result_type: str):
        """Load and display results for the selected type."""
        try:
            # Get cache data for display
            cache_entries = self.cache_repo.get_cache_for_display(
                project_id=self.project_id,
                result_type=result_type,
                result_set_id=self.current_result_set_id,
            )

            if not cache_entries:
                self.statusBar().showMessage(f"No data available for {result_type}")
                self.table_widget.clear_data()
                self.plot_widget.clear_plots()
                return

            # Convert cache to table format
            import pandas as pd

            # Build DataFrame from cache
            story_names = []
            data_dicts = []

            for entry in cache_entries:
                story_names.append(entry.story.name if hasattr(entry, 'story') else f"Story {entry.story_id}")
                data_dicts.append(entry.results_matrix)

            # Create DataFrame
            df = pd.DataFrame(data_dicts)

            # Filter for X direction only and clean column names
            if result_type == "Drifts":
                # Keep only columns ending with _X
                x_columns = [col for col in df.columns if col.endswith('_X')]
                df = df[x_columns]

                # Extract only the load case name (last part after last underscore before _X)
                # Example: "160Wil_DES_Global_TH01_X" -> "TH01"
                cleaned_columns = []
                for col in df.columns:
                    # Remove _X suffix first
                    col_without_x = col.replace('_X', '')
                    # Get the last part after splitting by underscore
                    parts = col_without_x.split('_')
                    load_case_name = parts[-1] if parts else col_without_x
                    cleaned_columns.append(load_case_name)

                df.columns = cleaned_columns

                # Calculate statistics (Avg, Max, Min) from numeric columns
                numeric_data = df.apply(pd.to_numeric, errors='coerce')
                df['Avg'] = numeric_data.mean(axis=1)
                df['Max'] = numeric_data.max(axis=1)
                df['Min'] = numeric_data.min(axis=1)

            # Insert Story column at the beginning
            df.insert(0, 'Story', story_names)

            # Reverse order so lower stories appear at bottom
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

    def on_view_mode_changed(self, mode: str):
        """Handle view mode changes."""
        if mode == "Table + Plot":
            self.table_widget.show()
            self.plot_widget.show()
        elif mode == "Table Only":
            self.table_widget.show()
            self.plot_widget.hide()
        elif mode == "Plot Only":
            self.table_widget.hide()
            self.plot_widget.show()

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
            if self.current_result_type:
                self.load_results(self.current_result_type)

            QMessageBox.information(
                self,
                "Load Complete",
                f"Successfully loaded data into project: {self.project_name}\n\n"
                f"The results browser has been refreshed."
            )

            self.statusBar().showMessage("Data loaded successfully", 5000)

    def export_results(self):
        """Export current results to Excel."""
        # TODO: Implement export functionality
        self.statusBar().showMessage("Export functionality coming soon...")

    def closeEvent(self, event):
        """Handle window close event."""
        if self.session:
            self.session.close()
        event.accept()
