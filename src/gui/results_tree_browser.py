"""Results tree browser - hierarchical navigation for project results."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .ui_helpers import create_styled_label


class ResultsTreeBrowser(QWidget):
    """Tree browser for navigating project results."""

    selection_changed = pyqtSignal(int, str, str, str)  # (result_set_id, category, result_type, direction)

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
        self.tree.setIndentation(16)
        self.tree.setAnimated(True)
        self.tree.setUniformRowHeights(False)
        self.tree.itemClicked.connect(self.on_item_clicked)

        # Modern minimalist data-vis style (Vercel/Linear inspired)
        self.tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
                outline: none;
                padding: 4px;
                font-size: 14px;
            }
            QTreeWidget::item {
                padding: 7px 10px;
                border-radius: 5px;
                color: #9ca3af;
                margin: 1px 0px;
                border: none;
                background-color: transparent;
            }
            QTreeWidget::item:hover {
                background-color: rgba(255, 255, 255, 0.03);
                color: #d1d5db;
            }
            QTreeWidget::item:selected {
                background-color: rgba(74, 125, 137, 0.12);
                color: #67e8f9;
                font-weight: 400;
            }
            QTreeWidget::item:selected:hover {
                background-color: rgba(74, 125, 137, 0.18);
            }
            QTreeWidget::branch {
                background-color: transparent;
                border: none;
            }
            QTreeWidget::branch:has-children:closed {
                image: none;
                border: none;
            }
            QTreeWidget::branch:has-children:open {
                image: none;
                border: none;
            }
        """)

        layout.addWidget(self.tree)

    def populate_tree(self, result_sets, stories):
        """Populate tree with project structure.

        Args:
            result_sets: List of ResultSet model instances
            stories: List of Story model instances
        """
        self.tree.clear()

        # Project info item
        info_item = QTreeWidgetItem(self.tree)
        info_item.setText(0, f"ⓘ Project Info")
        info_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "info"})
        info_item.setExpanded(False)

        # Add stories count
        stories_info = QTreeWidgetItem(info_item)
        stories_info.setText(0, f"└ {len(stories)} stories")
        stories_info.setFlags(Qt.ItemFlag.NoItemFlags)  # Non-selectable

        # Add result sets count
        sets_info = QTreeWidgetItem(info_item)
        sets_info.setText(0, f"└ {len(result_sets)} result sets")
        sets_info.setFlags(Qt.ItemFlag.NoItemFlags)

        # Results root
        results_root = QTreeWidgetItem(self.tree)
        results_root.setText(0, "▸ Results")
        results_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "root"})
        results_root.setExpanded(True)

        if not result_sets:
            # Show empty state
            placeholder = QTreeWidgetItem(results_root)
            placeholder.setText(0, "└ No result sets")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            # Add each result set
            for result_set in result_sets:
                self._add_result_set(results_root, result_set)

    def _add_result_set(self, parent_item: QTreeWidgetItem, result_set):
        """Add a result set with its hierarchy.

        Structure:
        └── Result Set Name (DES, MCE, etc.)
            ├── Envelopes
            │   └── Global Results
            │       ├── Story Drifts
            │       ├── Story Accelerations
            │       ├── Story Shears
            │       └── Story Displacements
            └── Time-Series (placeholder)
        """
        # Result set item
        result_set_item = QTreeWidgetItem(parent_item)
        result_set_item.setText(0, f"▸ {result_set.name}")
        result_set_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "result_set", "id": result_set.id})
        result_set_item.setExpanded(True)

        # Envelopes category
        envelopes_item = QTreeWidgetItem(result_set_item)
        envelopes_item.setText(0, "◆ Envelopes")
        envelopes_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category",
            "result_set_id": result_set.id,
            "category": "Envelopes"
        })
        envelopes_item.setExpanded(True)

        # Global Results
        global_item = QTreeWidgetItem(envelopes_item)
        global_item.setText(0, "◇ Global")
        global_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category_type",
            "result_set_id": result_set.id,
            "category": "Envelopes",
            "category_type": "Global"
        })
        global_item.setExpanded(True)

        # Result types under Global
        # Drifts with special subsections
        self._add_drifts_section(global_item, result_set.id)

        # Other result types
        self._add_result_type_with_directions(global_item, "› Accelerations", result_set.id, "Envelopes", "Accelerations")
        self._add_result_type_with_directions(global_item, "› Shears", result_set.id, "Envelopes", "Forces")
        self._add_result_type_with_directions(global_item, "› Displacements", result_set.id, "Envelopes", "Displacements")

        # Time-Series category (placeholder)
        timeseries_item = QTreeWidgetItem(result_set_item)
        timeseries_item.setText(0, "◆ Time-Series")
        timeseries_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category",
            "result_set_id": result_set.id,
            "category": "Time-Series"
        })
        timeseries_item.setExpanded(False)

        placeholder = QTreeWidgetItem(timeseries_item)
        placeholder.setText(0, "└ Coming soon")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)

    def _add_result_type(self, parent_item: QTreeWidgetItem, label: str, result_set_id: int, category: str, result_type: str):
        """Add a result type item to the tree."""
        item = QTreeWidgetItem(parent_item)
        item.setText(0, label)
        item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": result_type,
            "direction": None  # No direction for non-directional types
        })

    def _add_drifts_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Drifts section with directions and Max/Min subsection.

        Structure:
        └── Drifts
            ├── X Direction
            ├── Y Direction
            └── Max/Min Drifts
        """
        # Parent Drifts item
        drifts_parent = QTreeWidgetItem(parent_item)
        drifts_parent.setText(0, "› Drifts")
        drifts_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "Drifts"
        })
        drifts_parent.setExpanded(True)

        # X Direction
        x_item = QTreeWidgetItem(drifts_parent)
        x_item.setText(0, "  ├ X Direction")
        x_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "Drifts",
            "direction": "X"
        })

        # Y Direction
        y_item = QTreeWidgetItem(drifts_parent)
        y_item.setText(0, "  ├ Y Direction")
        y_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "Drifts",
            "direction": "Y"
        })

        # Max/Min Drifts subsection
        maxmin_item = QTreeWidgetItem(drifts_parent)
        maxmin_item.setText(0, "  └ Max/Min Drifts")
        maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "maxmin_drifts",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MaxMinDrifts"
        })

    def _add_result_type_with_directions(self, parent_item: QTreeWidgetItem, label: str, result_set_id: int, category: str, result_type: str):
        """Add a result type item with X/Y direction subsections.

        Structure:
        └── Drifts
            ├── X Direction
            └── Y Direction
        """
        # Parent result type item (non-clickable, just for grouping)
        parent_result_item = QTreeWidgetItem(parent_item)
        parent_result_item.setText(0, label)
        parent_result_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type_parent",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": result_type
        })
        parent_result_item.setExpanded(True)  # Start expanded

        # X Direction subsection
        x_item = QTreeWidgetItem(parent_result_item)
        x_item.setText(0, "  ├ X Direction")
        x_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": result_type,
            "direction": "X"
        })

        # Y Direction subsection
        y_item = QTreeWidgetItem(parent_result_item)
        y_item.setText(0, "  └ Y Direction")
        y_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": result_type,
            "direction": "Y"
        })

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            return

        item_type = data.get("type")

        if item_type == "result_type":
            # Emit with full hierarchy path including direction
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = data.get("result_type")
            direction = data.get("direction", "X")  # Default to X if not specified
            self.selection_changed.emit(result_set_id, category, result_type, direction)
        elif item_type == "maxmin_drifts":
            # Emit for Max/Min Drifts (no direction needed)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = data.get("result_type")
            self.selection_changed.emit(result_set_id, category, result_type, "")
