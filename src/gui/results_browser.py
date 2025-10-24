"""Results browser widget for navigating imported data."""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QLabel,
    QPushButton,
    QHBoxLayout,
)
from PyQt6.QtCore import pyqtSignal


class ResultsBrowser(QWidget):
    """Widget for browsing and selecting results from database."""

    # Signal emitted when selection changes
    selection_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_ui()

    def _create_ui(self):
        """Create modern sidebar-style UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        # Header with modern styling
        header_widget = QWidget()
        header_widget.setObjectName("browserHeader")
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 16, 16, 12)
        header_layout.setSpacing(4)

        header_label = QLabel("Results Browser")
        header_label.setProperty("styleClass", "header")
        header_label.setStyleSheet("font-size: 16px; font-weight: 600; padding: 0;")

        subtitle_label = QLabel("Browse imported projects")
        subtitle_label.setProperty("styleClass", "muted")
        subtitle_label.setStyleSheet("font-size: 13px; padding: 0;")

        header_layout.addWidget(header_label)
        header_layout.addWidget(subtitle_label)

        layout.addWidget(header_widget)

        # Tree widget for hierarchical browsing with modern styling
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)  # Hide header for cleaner look
        self.tree.setIndentation(16)
        self.tree.setRootIsDecorated(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: none;
                padding: 0 8px;
            }
        """)

        layout.addWidget(self.tree)

        # Load initial data
        self.refresh()

    def refresh(self):
        """Refresh the results browser from database."""
        from database.base import get_session
        from database.repository import ProjectRepository, LoadCaseRepository

        self.tree.clear()

        session = get_session()
        try:
            project_repo = ProjectRepository(session)
            projects = project_repo.get_all()

            if not projects:
                self._create_placeholder_structure()
                return

            # Create tree structure with modern styling
            for project in projects:
                # Project node with icon-like prefix
                project_item = QTreeWidgetItem(self.tree, [f"▸ {project.name}"])
                project_item.setExpanded(True)

                # Make project name bold
                font = project_item.font(0)
                font.setBold(True)
                project_item.setFont(0, font)

                # Load cases node
                case_repo = LoadCaseRepository(session)
                load_cases = case_repo.get_by_project(project.id)

                if load_cases:
                    cases_node = QTreeWidgetItem(project_item, [f"◆ Load Cases ({len(load_cases)})"])
                    cases_node.setExpanded(False)  # Collapsed by default

                    for case in load_cases:
                        case_display = f"  {case.name}"
                        if case.case_type:
                            case_display += f" • {case.case_type}"
                        case_item = QTreeWidgetItem(cases_node, [case_display])

                # Results node
                results_node = QTreeWidgetItem(project_item, ["◇ Results"])
                results_node.setExpanded(True)

                # Result types with modern icons
                QTreeWidgetItem(results_node, ["  Δ Story Drifts"])
                QTreeWidgetItem(results_node, ["  ≈ Story Accelerations"])
                QTreeWidgetItem(results_node, ["  ↕ Story Forces"])

        finally:
            session.close()

    def _create_placeholder_structure(self):
        """Create placeholder tree structure when no projects exist."""
        info_item = QTreeWidgetItem(
            self.tree, ["Import Excel files to see results", ""]
        )
        info_item.setDisabled(True)

    def _on_selection_changed(self):
        """Handle selection change in tree."""
        selected_items = self.tree.selectedItems()
        if selected_items:
            item = selected_items[0]
            # Emit selection details
            selection = {
                "name": item.text(0),
                "type": item.text(1),
                "item": item,
            }
            self.selection_changed.emit(selection)

    def load_project(self, project_id):
        """Load a specific project into the browser."""
        # TODO: Implement project loading from database
        pass
