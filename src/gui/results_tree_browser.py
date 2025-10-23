"""Results tree browser - hierarchical navigation for project results."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .ui_helpers import create_styled_label


class ResultsTreeBrowser(QWidget):
    """Tree browser for navigating project results."""

    selection_changed = pyqtSignal(str, str)  # (selection_type, result_type)

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.setup_ui()

    def setup_ui(self):
        """Setup the browser UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header
        header = create_styled_label("Results Browser", "subheader")
        header.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(header)

        # Tree widget
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setIndentation(20)
        self.tree.setAnimated(True)
        self.tree.itemClicked.connect(self.on_item_clicked)

        # Style tree
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: #0a0c10;
                border: none;
                outline: none;
                padding: 4px;
            }
            QTreeWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
                color: #d1d5db;
            }
            QTreeWidget::item:hover {
                background-color: #161b22;
            }
            QTreeWidget::item:selected {
                background-color: rgba(74, 125, 137, 0.2);
                border-left: 2px solid #4a7d89;
                color: #4a7d89;
            }
            QTreeWidget::branch {
                background-color: transparent;
            }
            QTreeWidget::branch:has-children:closed {
                image: url(none);
            }
            QTreeWidget::branch:has-children:open {
                image: url(none);
            }
        """)

        layout.addWidget(self.tree)

    def populate_tree(self, result_sets, stories):
        """Populate tree with project structure."""
        self.tree.clear()

        # Project info item
        info_item = QTreeWidgetItem(self.tree)
        info_item.setText(0, f"📋 Project Info")
        info_item.setData(0, Qt.ItemDataRole.UserRole, ("info", None))
        info_item.setExpanded(False)

        # Add stories count
        stories_info = QTreeWidgetItem(info_item)
        stories_info.setText(0, f"  Stories: {len(stories)}")
        stories_info.setFlags(Qt.ItemFlag.NoItemFlags)  # Non-selectable

        # Add result sets count
        sets_info = QTreeWidgetItem(info_item)
        sets_info.setText(0, f"  Result Sets: {len(result_sets)}")
        sets_info.setFlags(Qt.ItemFlag.NoItemFlags)

        # Envelopes section
        envelopes_item = QTreeWidgetItem(self.tree)
        envelopes_item.setText(0, "📊 Envelope Results")
        envelopes_item.setData(0, Qt.ItemDataRole.UserRole, ("envelopes", None))
        envelopes_item.setExpanded(True)

        # Add result types under Envelopes
        self._add_result_type(envelopes_item, "Δ Story Drifts", "Drifts")
        self._add_result_type(envelopes_item, "≈ Story Accelerations", "Accelerations")
        self._add_result_type(envelopes_item, "↕ Story Forces", "Forces")

        # Time-Series section (placeholder)
        timeseries_item = QTreeWidgetItem(self.tree)
        timeseries_item.setText(0, "📈 Time-Series Results")
        timeseries_item.setData(0, Qt.ItemDataRole.UserRole, ("timeseries", None))
        timeseries_item.setExpanded(False)

        placeholder = QTreeWidgetItem(timeseries_item)
        placeholder.setText(0, "  (Coming soon)")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)

        # Elements section (placeholder)
        elements_item = QTreeWidgetItem(self.tree)
        elements_item.setText(0, "🏗️ Element Results")
        elements_item.setData(0, Qt.ItemDataRole.UserRole, ("elements", None))
        elements_item.setExpanded(False)

        placeholder2 = QTreeWidgetItem(elements_item)
        placeholder2.setText(0, "  (Coming soon)")
        placeholder2.setFlags(Qt.ItemFlag.NoItemFlags)

    def _add_result_type(self, parent_item: QTreeWidgetItem, label: str, result_type: str):
        """Add a result type item to the tree."""
        item = QTreeWidgetItem(parent_item)
        item.setText(0, f"  {label}")
        item.setData(0, Qt.ItemDataRole.UserRole, ("result_type", result_type))

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        selection_type, result_type = data

        if selection_type == "result_type":
            self.selection_changed.emit(selection_type, result_type)
        elif selection_type == "info":
            self.selection_changed.emit(selection_type, None)
