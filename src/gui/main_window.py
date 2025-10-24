"""Main application window."""

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
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QMessageBox
from datetime import datetime
from pathlib import Path

from .import_dialog import ImportDialog
from .window_utils import enable_dark_title_bar
from .project_detail_window import ProjectDetailWindow
from .styles import COLORS
from database.base import get_session
from database.repository import ProjectRepository
from utils.env import is_dev_mode


class MainWindow(QMainWindow):
    """Main application window with menu, results browser, and visualization area."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Results Processing System")
        self.setMinimumSize(QSize(1200, 800))

        # Initialize UI components
        self._create_central_widget()
        self._create_status_bar()

        # Store current project
        self.current_project = None

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
        header.setFixedHeight(64)  # Compact fixed height
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 8, 16, 8)
        header_layout.setSpacing(16)

        # Branded logo on the left
        logo_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "RPS_Logo.png"
        logo_label = QLabel()
        logo_label.setObjectName("headerLogo")
        logo_label.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        logo_label.setFixedSize(100, 48)  # Compact logo size
        pixmap = QPixmap(str(logo_path))
        if not pixmap.isNull():
            scaled = pixmap.scaled(100, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled)
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
            ("Project", self._show_projects),
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

        # Default to Home
        self._set_active_nav("Home")
        self.stack.setCurrentWidget(self.home_page)
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

        subtitle = QLabel("Manage your seismic analysis projects and collaborate with your team.")
        subtitle.setObjectName("pageSubheadline")
        outer_layout.addWidget(subtitle)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        create_button = QPushButton("Create New Project")
        create_button.setObjectName("primaryAction")
        create_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        create_button.clicked.connect(self._on_create_project)
        controls.addWidget(create_button)

        import_button = QPushButton("Import from Excel")
        import_button.setObjectName("ghostAction")
        import_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        import_button.clicked.connect(self._on_import)
        controls.addWidget(import_button)

        controls.addStretch()
        outer_layout.addLayout(controls)

        self.projects_scroll = QScrollArea()
        self.projects_scroll.setWidgetResizable(True)
        self.projects_container = QWidget()
        self.projects_layout = QGridLayout(self.projects_container)
        self.projects_layout.setContentsMargins(0, 0, 0, 0)
        self.projects_layout.setHorizontalSpacing(16)
        self.projects_layout.setVerticalSpacing(16)
        self.projects_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.projects_scroll.setWidget(self.projects_container)
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
        elif name == "Project":
            self.stack.setCurrentWidget(self.projects_page)
            self._refresh_projects()
        elif name == "Doc":
            self.stack.setCurrentWidget(self.docs_page)

    def _show_home(self):
        """Navigate to home page."""
        self._set_active_nav("Home")

    def _show_projects(self):
        """Navigate to projects page."""
        self._set_active_nav("Project")

    def _show_docs(self):
        """Navigate to docs page."""
        self._set_active_nav("Doc")

    def _refresh_projects(self):
        """Load projects from database and render cards."""
        session = get_session()
        project_rows = []
        totals = {"projects": 0, "load_cases": 0, "stories": 0}
        try:
            repo = ProjectRepository(session)
            projects = repo.get_all()
            for project in projects:
                load_cases = list(project.load_cases)
                stories = list(project.stories)

                row = {
                    "name": project.name,
                    "description": project.description,
                    "load_cases": len(load_cases),
                    "stories": len(stories),
                    "created_at": project.created_at,
                }
                project_rows.append(row)

                totals["projects"] += 1
                totals["load_cases"] += row["load_cases"]
                totals["stories"] += row["stories"]

        finally:
            session.close()

        # Clear existing cards
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

        if not project_rows:
            empty_label = QLabel("No projects imported yet. Use the Home page to import results.")
            empty_label.setObjectName("pageBodyText")
            empty_label.setWordWrap(True)
            self.projects_layout.addWidget(empty_label, 0, 0)
            self._update_summary({"projects": 0, "load_cases": 0, "stories": 0})
            self.summary_card.setVisible(False)
            return

        columns = 3
        for index, project in enumerate(project_rows):
            row_idx = index // columns
            col_idx = index % columns
            card = self._create_project_card(project)
            self.projects_layout.addWidget(card, row_idx, col_idx)

        # absorb remaining horizontal space so cards stay left-aligned
        self.projects_layout.setColumnStretch(columns, 1)

        self._update_summary(totals)
        self.summary_card.setVisible(True)

    def _create_project_card(self, data: dict) -> QWidget:
        """Create a stylized project card."""
        card = QFrame()
        card.setObjectName("projectCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setFixedSize(320, 240)
        card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel(data["name"])
        title.setObjectName("cardTitle")
        layout.addWidget(title)

        body_text = data.get("description") or "Imported project with structural results ready for analysis."
        body = QLabel(body_text)
        body.setObjectName("cardBody")
        body.setWordWrap(True)
        layout.addWidget(body)

        stats_container = QFrame()
        stats_container.setObjectName("cardStatsContainer")
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(8)

        stats = [
            ("Load cases", data.get("load_cases", 0)),
            ("Stories", data.get("stories", 0)),
        ]

        for label, value in stats:
            row = QHBoxLayout()
            row.setSpacing(8)
            label_widget = QLabel(label)
            label_widget.setObjectName("cardStatLabel")
            value_widget = QLabel(str(value))
            value_widget.setObjectName("cardStatValue")
            row.addWidget(label_widget)
            row.addStretch()
            row.addWidget(value_widget)
            stats_layout.addLayout(row)

        layout.addWidget(stats_container)

        layout.addStretch()

        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setObjectName("cardDivider")
        layout.addWidget(divider)

        footer = QHBoxLayout()
        footer.setSpacing(12)

        created_label = QLabel("Created")
        created_label.setObjectName("cardFooterLabel")
        footer.addWidget(created_label)

        created_at = data.get("created_at")
        created_value = QLabel(self._format_date(created_at))
        created_value.setObjectName("cardFooterValue")
        footer.addWidget(created_value)

        footer.addStretch()

        layout.addLayout(footer)

        # Action buttons layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)

        open_button = QPushButton("Open Project")
        open_button.setObjectName("cardAction")
        open_button.clicked.connect(lambda: self._open_project_detail(data["name"]))
        button_layout.addWidget(open_button)

        delete_button = QPushButton("Delete")
        delete_button.setObjectName("dangerAction")
        delete_button.clicked.connect(lambda: self._delete_project(data["name"]))
        button_layout.addWidget(delete_button)

        button_layout.addStretch()

        layout.addLayout(button_layout)

        return card

    def _open_project_detail(self, project_name: str):
        """Open project detail window."""
        session = get_session()
        try:
            repo = ProjectRepository(session)
            project = repo.get_by_name(project_name)

            if not project:
                QMessageBox.warning(
                    self,
                    "Project Not Found",
                    f"Could not find project: {project_name}"
                )
                return

            # Create and show project detail window
            detail_window = ProjectDetailWindow(project.id, project.name, self)
            if is_dev_mode():
                detail_window.showMaximized()
            else:
                detail_window.show()

            self.statusBar().showMessage(f"Opened project: {project_name}", 3000)

        except Exception as e:
            QMessageBox.critical(
                self,
                "Error Opening Project",
                f"Could not open project:\n\n{str(e)}"
            )
        finally:
            session.close()

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

        # Delete the project
        session = get_session()
        try:
            repo = ProjectRepository(session)
            project = repo.get_by_name(project_name)

            if not project:
                QMessageBox.warning(
                    self,
                    "Project Not Found",
                    f"Could not find project: {project_name}"
                )
                return

            # Delete project (cascading deletes will handle related data)
            success = repo.delete(project.id)

            if success:
                QMessageBox.information(
                    self,
                    "Project Deleted",
                    f"Project '{project_name}' has been successfully deleted."
                )
                self.statusBar().showMessage(f"Deleted project: {project_name}", 5000)

                # Refresh projects view
                self._refresh_projects()
            else:
                QMessageBox.warning(
                    self,
                    "Delete Failed",
                    f"Could not delete project: {project_name}"
                )

        except Exception as e:
            session.rollback()
            QMessageBox.critical(
                self,
                "Error Deleting Project",
                f"An error occurred while deleting the project:\n\n{str(e)}"
            )
        finally:
            session.close()

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

        session = get_session()
        try:
            repo = ProjectRepository(session)
            if repo.get_by_name(name):
                QMessageBox.warning(
                    self,
                    "Project Exists",
                    "A project with that name already exists. Choose a different name.",
                )
                return

            repo.create(name=name, description=description)
            self.statusBar().showMessage(f"Created project: {name}", 5000)
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(
                self,
                "Project Error",
                f"Could not create project:\n\n{exc}",
            )
            return
        finally:
            session.close()

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
                    # Import data
                    importer = DataImporter(file_path, project_name, result_set_name, analysis_type)
                    stats = importer.import_all()

                    # Show success message
                    message = (
                        f"Import successful!\n\n"
                        f"Project: {stats['project']}\n"
                        f"Load Cases: {stats['load_cases']}\n"
                        f"Stories: {stats['stories']}\n"
                        f"Drifts: {stats['drifts']}\n"
                        f"Accelerations: {stats['accelerations']}\n"
                        f"Forces: {stats['forces']}"
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

        dialog = FolderImportDialog(self)
        if dialog.exec():
            project_name = dialog.get_project_name()

            # Show success and refresh
            QMessageBox.information(
                self,
                "Folder Import Complete",
                f"Successfully imported project: {project_name}\n\n"
                f"Check the Projects page to view the imported data."
            )

            self.statusBar().showMessage(f"Folder import complete: {project_name}", 5000)
            self.project_label.setText(f"Project: {project_name}")
            self.current_project = project_name

            # Refresh projects view
            self._refresh_projects()

    def _on_refresh(self):
        """Handle refresh action."""
        self.statusBar().showMessage("Refreshing...", 2000)
        self._refresh_projects()

    def _on_database_info(self):
        """Show database information."""
        from database.base import DB_PATH

        self.statusBar().showMessage(f"Database: {DB_PATH}", 5000)

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
