"""Results browser widget for navigating imported data."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.project_service import list_project_contexts


class ResultsBrowser(QWidget):
    """Widget for browsing and selecting results from project databases."""

    selection_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._create_ui()

    def _create_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

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

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(16)
        self.tree.setRootIsDecorated(True)
        self.tree.itemSelectionChanged.connect(self._on_selection_changed)
        self.tree.setStyleSheet(
            """
            QTreeWidget {
                border: none;
                padding: 0 8px;
            }
            """
        )

        layout.addWidget(self.tree)
        self.refresh()

    def refresh(self) -> None:
        from database.repository import LoadCaseRepository, ProjectRepository

        self.tree.clear()

        contexts = list_project_contexts()
        if not contexts:
            self._create_placeholder_structure()
            return

        for context in contexts:
            session = context.session()
            try:
                project = ProjectRepository(session).get_by_name(context.name)
                if not project:
                    continue

                project_item = QTreeWidgetItem(self.tree, [f"> {project.name}"])
                project_item.setExpanded(True)

                font = project_item.font(0)
                font.setBold(True)
                project_item.setFont(0, font)

                load_cases = LoadCaseRepository(session).get_by_project(project.id)
                if load_cases:
                    cases_node = QTreeWidgetItem(
                        project_item,
                        [f"> Load Cases ({len(load_cases)})"],
                    )
                    cases_node.setExpanded(False)

                    for case in load_cases:
                        case_display = f"  {case.name}"
                        if case.case_type:
                            case_display += f" - {case.case_type}"
                        QTreeWidgetItem(cases_node, [case_display])

                results_node = QTreeWidgetItem(project_item, ["> Results"])
                results_node.setExpanded(True)
                QTreeWidgetItem(results_node, ["  > Story Drifts"])
                QTreeWidgetItem(results_node, ["  > Story Accelerations"])
                QTreeWidgetItem(results_node, ["  > Story Forces"])
                QTreeWidgetItem(results_node, ["  > Floors Displacements"])
            finally:
                session.close()

    def _create_placeholder_structure(self) -> None:
        info_item = QTreeWidgetItem(
            self.tree,
            ["Import Excel files to see results", ""],
        )
        info_item.setDisabled(True)

    def _on_selection_changed(self) -> None:
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        selection = {
            "name": item.text(0),
            "type": item.text(1) if item.columnCount() > 1 else None,
            "item": item,
        }
        self.selection_changed.emit(selection)

    def load_project(self, project_id: int) -> None:
        # Reserved for future expansion.
        pass


