"""Main application window."""

from typing import Dict

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QScrollArea,
    QFrame,
    QSizePolicy,
    QStatusBar,
    QGridLayout,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QApplication,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMessageBox
from datetime import datetime
from pathlib import Path

from .import_dialog import ImportDialog
from .window_utils import enable_dark_title_bar
from .project_detail_window import ProjectDetailWindow
from .project_grid_widget import ProjectGridWidget
from .styles import COLORS
from services.project_service import (
    ensure_project_context,
    get_project_context,
    delete_project_context,
    result_set_exists,
    list_project_summaries,
)
from utils.env import is_dev_mode


class MainWindow(QMainWindow):
    """Main application window with menu, results browser, and visualization area."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Results Processing System")
        self.setMinimumSize(QSize(1200, 800))

        # Apply gray background to main window (match group box background)
        self.setStyleSheet(f"QMainWindow {{ background-color: {COLORS['card']}; }}")

        # Initialize UI components
        self._create_central_widget()
        self._create_status_bar()

        # Store current project
        self.current_project = None

        # Track open project detail windows {project_name: window}
        self._project_windows: Dict[str, ProjectDetailWindow] = {}

        # Apply object names for styling
        self.setObjectName("mainWindow")

        # Default to Projects page on launch
        self._show_projects()

    def showEvent(self, event):
        """Override showEvent to apply dark title bar after window is shown."""
        super().showEvent(event)
        # Enable dark title bar on Windows
        enable_dark_title_bar(self)

    def _create_central_widget(self):
        """Create central widget with header navigation and stacked pages."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._create_header(layout)
        self._create_content_area(layout)

    def _create_status_bar(self):
        """Create status bar."""
        self.statusBar().showMessage("Ready")

        # Add permanent widgets to status bar
        self.project_label = QLabel("No project loaded")
        self.statusBar().addPermanentWidget(self.project_label)

    def _create_header(self, container_layout: QVBoxLayout):
        """Create top header bar with logo and navigation."""
        header = QFrame()
        header.setObjectName("topHeader")
        header.setFrameShape(QFrame.Shape.NoFrame)
        header.setFixedHeight(88)  # Taller header for larger logo
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 6, 20, 6)
        header_layout.setSpacing(16)

        # Branded logo on the left
        logo_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "RPS_Logo.png"
        logo_label = QLabel()
        logo_label.setObjectName("headerLogo")
        logo_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        # Scale logo based on header height and keep aspect ratio (HiDPI safe)
        # Use a slightly smaller target than header inner height to avoid any clipping
        target_logo_height = 60
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            # Compute logical width from aspect ratio to avoid DPI cropping
            aspect = pixmap.width() / pixmap.height() if pixmap.height() else 1.0
            logical_width = int(target_logo_height * aspect)

            # HiDPI-aware scaling: scale in device pixels and set DPR on pixmap
            app = QApplication.instance()
            screen = app.primaryScreen() if app else None
            dpr = float(screen.devicePixelRatio()) if screen else 1.0

            target_h_px = max(1, int(target_logo_height * dpr))
            scaled = pixmap.scaledToHeight(
                target_h_px,
                Qt.TransformationMode.SmoothTransformation,
            )
            scaled.setDevicePixelRatio(dpr)

            logo_label.setPixmap(scaled)
            # Prevent stretching; size label to pixmap logical size and keep as minimum
            logo_label.setScaledContents(False)
            logo_label.setMinimumSize(int(scaled.width() / dpr), int(scaled.height() / dpr))
            logo_label.adjustSize()
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        else:
            logo_label.setText("RPS")
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            logo_label.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {COLORS['accent']};")
        header_layout.addWidget(logo_label)

        header_layout.addStretch()

        self.nav_buttons = {}
        nav_items = [
            ("Home", self._show_home),
            ("Projects", self._show_projects),
            ("Doc", self._show_docs),
        ]

        for title, handler in nav_items:
            button = QPushButton(title)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setAutoExclusive(True)
            button.clicked.connect(handler)
            header_layout.addWidget(button)
            self.nav_buttons[title] = button

        container_layout.addWidget(header, stretch=0)

    def _create_content_area(self, container_layout: QVBoxLayout):
        """Create stacked pages for navigation targets."""
        self.stack = QStackedWidget()
        self.home_page = self._build_home_page()
        self.projects_page = self._build_projects_page()
        self.docs_page = self._build_docs_page()

        self.stack.addWidget(self.home_page)
        self.stack.addWidget(self.projects_page)
        self.stack.addWidget(self.docs_page)

        container_layout.addWidget(self.stack, stretch=1)

        # Default to Projects page
        self._set_active_nav("Projects")
        self.stack.setCurrentWidget(self.projects_page)
        self._refresh_projects()

    def _build_home_page(self) -> QWidget:
        """Create the home/landing page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(24)

        headline = QLabel("Results Processing System")
        headline.setObjectName("pageHeadline")
        headline.setWordWrap(True)

        subheading = QLabel(
            "Process structural engineering output from ETABS/SAP2000 with a clean, web-inspired desktop experience."
        )
        subheading.setObjectName("pageSubheadline")
        subheading.setWordWrap(True)

        description = QLabel(
            "RPS imports multi-sheet Excel exports, persists them to a local SQLite database, "
            "and gives engineers a fast way to browse load cases, story metrics, and time-history plots. "
            "Use the importer to bring in fresh models, then explore projects from the Projects view."
        )
        description.setWordWrap(True)
        description.setObjectName("pageBodyText")

        # Import buttons
        import_layout = QHBoxLayout()
        import_layout.setSpacing(12)

        import_button = QPushButton("Import Single File")
        import_button.setObjectName("primaryAction")
        import_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        import_button.clicked.connect(self._on_import)
        import_layout.addWidget(import_button)

        folder_import_button = QPushButton("Import from Folder")
        folder_import_button.setObjectName("secondaryAction")
        folder_import_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        folder_import_button.clicked.connect(self._on_folder_import)
        import_layout.addWidget(folder_import_button)

        import_layout.addStretch()

        layout.addWidget(headline)
        layout.addWidget(subheading)
        layout.addWidget(description)
        layout.addLayout(import_layout)
        layout.addStretch()

        return page

    def _build_projects_page(self) -> QWidget:
        """Create projects page container."""
        page = QWidget()
        outer_layout = QVBoxLayout(page)
        outer_layout.setContentsMargins(24, 24, 24, 24)
        outer_layout.setSpacing(16)

        title = QLabel("My Projects")
        title.setObjectName("pageHeadline")
        outer_layout.addWidget(title)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        create_button = QPushButton("Create New Project")
        create_button.setObjectName("primaryAction")
        create_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        create_button.clicked.connect(self._on_create_project)
        controls.addWidget(create_button)

        import_project_button = QPushButton("Import Project")
        import_project_button.setObjectName("secondaryAction")
        import_project_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        import_project_button.setToolTip("Import complete project from Excel file")
        import_project_button.clicked.connect(self._on_import_project)
        controls.addWidget(import_project_button)

        controls.addStretch()
        outer_layout.addLayout(controls)

        self.projects_scroll = QScrollArea()
        self.projects_scroll.setWidgetResizable(True)
        self.project_grid = ProjectGridWidget(
            on_open=self._open_project_detail,
            on_delete=self._delete_project,
        )
        self.projects_scroll.setWidget(self.project_grid)
        outer_layout.addWidget(self.projects_scroll)

        self.summary_card = QFrame()
        self.summary_card.setObjectName("summaryCard")
        summary_layout = QHBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(24, 16, 24, 16)
        summary_layout.setSpacing(32)

        self.summary_labels = {
            "projects": self._create_summary_metric("Total Projects", "0"),
            "load_cases": self._create_summary_metric("Total Load Cases", "0"),
            "stories": self._create_summary_metric("Total Stories", "0"),
        }

        for metric in self.summary_labels.values():
            summary_layout.addLayout(metric)

        outer_layout.addWidget(self.summary_card)
        self.summary_card.setVisible(False)

        return page

    def _build_docs_page(self) -> QWidget:
        """Create documentation placeholder page."""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(48, 48, 48, 48)
        layout.setSpacing(16)

        title = QLabel("Documentation")
        title.setObjectName("pageHeadline")
        layout.addWidget(title)

        body = QLabel(
            "Refer to the internal knowledge base and PRD for implementation details. "
            "A dedicated documentation view will live here soon."
        )
        body.setObjectName("pageBodyText")
        body.setWordWrap(True)
        layout.addWidget(body)
        layout.addStretch()

        return page

    def _create_summary_metric(self, label: str, value: str) -> QVBoxLayout:
        """Helper to create a summary metric widget."""
        layout = QVBoxLayout()
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("summaryMetricValue")

        label_widget = QLabel(label)
        label_widget.setObjectName("summaryMetricLabel")

        layout.addWidget(value_label)
        layout.addWidget(label_widget)

        # Store references for updates
        layout.value_label = value_label  # type: ignore[attr-defined]
        layout.label_widget = label_widget  # type: ignore[attr-defined]

        return layout

    def _set_active_nav(self, name: str):
        """Toggle nav button state and set stacked widget page."""
        for title, button in self.nav_buttons.items():
            button.setChecked(title == name)

        if name == "Home":
            self.stack.setCurrentWidget(self.home_page)
        elif name == "Projects":
            self.stack.setCurrentWidget(self.projects_page)
            self._refresh_projects()
        elif name == "Doc":
            self.stack.setCurrentWidget(self.docs_page)

    def _show_home(self):
        """Navigate to home page."""
        self._set_active_nav("Home")

    def _show_projects(self):
        """Navigate to projects page."""
        self._set_active_nav("Projects")

    def _show_docs(self):
        """Navigate to docs page."""
        self._set_active_nav("Doc")

    def _refresh_projects(self):
        """Load projects from catalog and render cards."""
        project_rows = []
        totals = {"projects": 0, "load_cases": 0, "stories": 0}
        summaries = list_project_summaries()

        for summary in summaries:
            context = summary.context
            row = {
                "name": context.name,
                "description": context.description,
                "load_cases": summary.load_cases,
                "stories": summary.stories,
                "created_at": context.created_at,
                "_formatted_created": self._format_date(context.created_at),
            }
            project_rows.append(row)

            totals["projects"] += 1
            totals["load_cases"] += summary.load_cases
            totals["stories"] += summary.stories

        self.project_grid.set_projects(project_rows)

        if not project_rows:
            self._update_summary({"projects": 0, "load_cases": 0, "stories": 0})
            self.summary_card.setVisible(False)
            return

        self._update_summary(totals)
        self.summary_card.setVisible(True)

    def _open_project_detail(self, project_name: str):
        """Open project detail window."""
        # If window already exists, bring it to front
        if project_name in self._project_windows:
            existing_window = self._project_windows[project_name]
            existing_window.raise_()
            existing_window.activateWindow()
            self.statusBar().showMessage(f"Opened project: {project_name}", 3000)
            return

        context = get_project_context(project_name)
        if not context:
            QMessageBox.warning(
                self,
                "Project Not Found",
                f"Could not find project: {project_name}"
            )
            return

        detail_window = ProjectDetailWindow(context, self)
        self._project_windows[project_name] = detail_window

        # Remove from tracking when window closes
        detail_window.destroyed.connect(lambda: self._project_windows.pop(project_name, None))

        if is_dev_mode():
            detail_window.showMaximized()
        else:
            detail_window.show()

        self.statusBar().showMessage(f"Opened project: {project_name}", 3000)

    def _delete_project(self, project_name: str):
        """Delete a project after confirmation."""
        # Show confirmation dialog
        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Are you sure you want to delete project '{project_name}'?\n\n"
            f"This will permanently delete all associated data including:\n"
            f"• Load cases\n"
            f"• Stories\n"
            f"• Drift data\n"
            f"• Acceleration data\n"
            f"• Force data\n"
            f"• Result sets and caches\n\n"
            f"This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Close project detail window if open to release database connection
        if project_name in self._project_windows:
            detail_window = self._project_windows[project_name]
            detail_window.close()
            # Remove from tracking immediately (don't wait for destroyed signal)
            self._project_windows.pop(project_name, None)

        # Delete the project
        try:
            success = delete_project_context(project_name)
            if success:
                QMessageBox.information(
                    self,
                    "Project Deleted",
                    f"Project '{project_name}' has been successfully deleted."
                )
                self.statusBar().showMessage(f"Deleted project: {project_name}", 5000)
                self._refresh_projects()
            else:
                QMessageBox.warning(
                    self,
                    "Project Not Found",
                    f"Could not find project: {project_name}"
                )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Deleting Project",
                f"An error occurred while deleting the project:\n\n{str(e)}"
            )

    def _update_summary(self, totals: dict):
        """Update summary metrics at bottom of page."""
        self.summary_labels["projects"].value_label.setText(str(totals.get("projects", 0)))  # type: ignore[attr-defined]
        self.summary_labels["load_cases"].value_label.setText(str(totals.get("load_cases", 0)))  # type: ignore[attr-defined]
        self.summary_labels["stories"].value_label.setText(str(totals.get("stories", 0)))  # type: ignore[attr-defined]

    @staticmethod
    def _format_date(date_value) -> str:
        """Format datetime for display."""
        if isinstance(date_value, datetime):
            return date_value.strftime("%b %d, %Y")
        return "—"

    def _on_create_project(self):
        """Launch dialog to create a new project entry."""
        dialog = CreateProjectDialog(self)
        if not dialog.exec():
            return

        name, description = dialog.get_project_data()
        if not name:
            return

        try:
            context = ensure_project_context(name, description)
            self.statusBar().showMessage(f"Project ready: {context.name}", 5000)
        except Exception as exc:
            QMessageBox.critical(
                self,
                "Project Error",
                f"Could not create project:\n\n{exc}",
            )
            return

        self._refresh_projects()

    def _on_import(self):
        """Handle import action."""
        from processing.data_importer import DataImporter

        dialog = ImportDialog(self)
        if dialog.exec():
            # Get selected file from dialog
            file_path = dialog.get_selected_file()
            project_name = dialog.get_project_name()
            result_set_name = dialog.get_result_set_name()
            analysis_type = dialog.get_analysis_type()

            if file_path and project_name and result_set_name:
                self.statusBar().showMessage(f"Importing {file_path}...")

                try:
                    context = ensure_project_context(project_name)
                    if result_set_exists(context, result_set_name):
                        QMessageBox.warning(
                            self,
                            "Duplicate Result Set",
                            f"Result set '{result_set_name}' already exists for this project.",
                        )
                        return

                    importer = DataImporter(
                        file_path,
                        context.name,
                        result_set_name,
                        analysis_type,
                        session_factory=context.session_factory(),
                    )
                    stats = importer.import_all()

                    # Show success message
                    message = (
                        f"Import successful!\n\n"
                        f"Project: {stats['project']}\n"
                        f"Load Cases: {stats['load_cases']}\n"
                        f"Stories: {stats['stories']}\n"
                        f"Drifts: {stats['drifts']}\n"
                        f"Accelerations: {stats['accelerations']}\n"
                        f"Forces: {stats['forces']}\n"
                        f"Displacements: {stats['displacements']}"
                    )

                    if stats['errors']:
                        message += f"\n\nWarnings:\n" + "\n".join(stats['errors'])

                    QMessageBox.information(self, "Import Complete", message)

                    self.statusBar().showMessage(f"Import complete: {project_name}", 5000)
                    self.project_label.setText(f"Project: {project_name}")
                    self.current_project = project_name

                    # Refresh projects view
                    self._refresh_projects()

                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Import Error",
                        f"Failed to import data:\n\n{str(e)}"
                    )
                    self.statusBar().showMessage("Import failed", 5000)

    def _on_folder_import(self):
        """Handle folder import action."""
        from .folder_import_dialog import FolderImportDialog
        from .ui_helpers import show_dialog_with_blur

        dialog = FolderImportDialog(self)
        if show_dialog_with_blur(dialog, self) == QDialog.DialogCode.Accepted:
            project_name = dialog.get_project_name() or "Project"
            result_set = dialog.get_result_set_name()
            stats = dialog.get_import_stats() or {}

            summary_lines = [
                f"Files processed: {stats.get('files_processed', 0)}/{stats.get('files_total', 0)}",
                f"Drifts: {stats.get('drifts', 0)}",
                f"Accelerations: {stats.get('accelerations', 0)}",
                f"Forces: {stats.get('forces', 0)}",
                f"Displacements: {stats.get('displacements', 0)}",
            ]

            detail_message = "\n".join(summary_lines)
            title_line = f"Successfully imported project: {project_name}"
            if result_set:
                title_line += f"\nResult set: {result_set}"

            QMessageBox.information(
                self,
                "Folder Import Complete",
                f"{title_line}\n\n{detail_message}\n\n"
                "Review the Projects page to explore the new results.",
            )

            self.statusBar().showMessage(f"Folder import complete: {project_name}", 5000)
            self.project_label.setText(f"Project: {project_name}")
            self.current_project = project_name

            # Refresh projects view
            self._refresh_projects()

    def _on_import_project(self):
        """Handle project import from Excel file."""
        from PyQt6.QtWidgets import QFileDialog
        from pathlib import Path

        # Open file dialog to select Excel file
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Project Excel File",
            str(Path.home()),
            "Excel Files (*.xlsx)"
        )

        if not file_path:
            return

        # Show import dialog with preview
        from .import_project_dialog import ImportProjectDialog

        dialog = ImportProjectDialog(Path(file_path), self)
        if dialog.exec():
            # Import successful - refresh projects list
            self._refresh_projects()
            self.statusBar().showMessage("Project imported successfully!", 5000)

    def _on_refresh(self):
        """Handle refresh action."""
        self.statusBar().showMessage("Refreshing...", 2000)
        self._refresh_projects()

    def _on_database_info(self):
        """Show database information."""
        from database.catalog_base import CATALOG_DB_PATH
        from database.base import PROJECTS_DIR

        message = (
            f"Catalog: {CATALOG_DB_PATH} | "
            f"Projects root: {PROJECTS_DIR}"
        )
        self.statusBar().showMessage(message, 7000)

    def _on_about(self):
        """Show about dialog."""
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.about(
            self,
            "About RPS",
            "<h3>Results Processing System</h3>"
            "<p>Version 0.1.0</p>"
            "<p>A desktop application for processing structural "
            "engineering results from ETABS/SAP2000.</p>"
            "<p><b>Technology Stack:</b></p>"
            "<ul>"
            "<li>PyQt6 - UI Framework</li>"
            "<li>PyQtGraph - Visualization</li>"
            "<li>SQLite - Database</li>"
            "<li>Pandas - Data Processing</li>"
            "</ul>",
        )


class CreateProjectDialog(QDialog):
    """Dialog for capturing new project details."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create Project")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignmentFlag.AlignTop)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., Tower A Retrofit")
        form_layout.addRow("Project Name", self.name_edit)

        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Optional description or notes")
        self.description_edit.setFixedHeight(120)
        form_layout.addRow("Description", self.description_edit)

        layout.addLayout(form_layout)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _accept_if_valid(self):
        if not self.name_edit.text().strip():
            QMessageBox.warning(
                self,
                "Missing Name",
                "Enter a project name before continuing.",
            )
            return
        self.accept()

    def get_project_data(self):
        """Return (name, description) tuple."""
        name = self.name_edit.text().strip()
        description = self.description_edit.toPlainText().strip() or None
        return name, description
