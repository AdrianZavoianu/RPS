"""Results tree browser - hierarchical navigation for project results."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .ui_helpers import create_styled_label


class ResultsTreeBrowser(QWidget):
    """Tree browser for navigating project results."""

    selection_changed = pyqtSignal(int, str, str, str, int)  # (result_set_id, category, result_type, direction, element_id)

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.elements = []  # Will be populated with project elements
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

    def populate_tree(self, result_sets, stories, elements=None):
        """Populate tree with project structure.

        Args:
            result_sets: List of ResultSet model instances
            stories: List of Story model instances
            elements: List of Element model instances (optional)
        """
        self.tree.clear()
        self.elements = elements or []

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
        self._add_result_type_with_directions(
            global_item,
            "> Story Accelerations",
            result_set.id,
            "Envelopes",
            "Accelerations",
            include_maxmin=True,
            maxmin_label="Accelerations",
        )
        self._add_result_type_with_directions(
            global_item,
            "> Story Forces",
            result_set.id,
            "Envelopes",
            "Forces",
            include_maxmin=True,
            maxmin_label="Story Forces",
        )
        self._add_result_type_with_directions(
            global_item,
            "> Floors Displacements",
            result_set.id,
            "Envelopes",
            "Displacements",
            include_maxmin=True,
            maxmin_label="Floors Displacements",
        )

        # Elements category
        elements_item = QTreeWidgetItem(envelopes_item)
        elements_item.setText(0, "◇ Elements")
        elements_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category_type",
            "result_set_id": result_set.id,
            "category": "Envelopes",
            "category_type": "Elements"
        })
        elements_item.setExpanded(True)

        # Walls subsection under Elements
        self._add_walls_section(elements_item, result_set.id)

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
            "type": "maxmin_results",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MaxMinDrifts"
        })

    def _add_walls_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Walls section with Shears and Quad Rotations subcategories.

        Structure:
        └── Walls
            ├── Shears
            │   ├── Pier1 (dynamic, from database)
            │   │   ├── V2
            │   │   ├── V3
            │   │   └── Max/Min
            │   └── Pier2
            │       ├── V2
            │       ├── V3
            │       └── Max/Min
            └── Quad Rotations
                ├── Pier1
                │   ├── Rotation
                │   └── Max/Min
                └── Pier2
                    ├── Rotation
                    └── Max/Min
        """
        # Walls parent item
        walls_parent = QTreeWidgetItem(parent_item)
        walls_parent.setText(0, "› Walls")
        walls_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "element_type": "Walls"
        })
        walls_parent.setExpanded(True)

        # Filter elements to get only walls/piers
        wall_elements = [elem for elem in self.elements if elem.element_type == "Wall"]

        # Shears subsection under Walls
        self._add_shears_section(walls_parent, result_set_id, wall_elements)

        # Quad Rotations subsection under Walls
        self._add_quad_rotations_section(walls_parent, result_set_id, wall_elements)

    def _add_shears_section(self, parent_item: QTreeWidgetItem, result_set_id: int, wall_elements):
        """Add Shears subsection with piers."""
        shears_parent = QTreeWidgetItem(parent_item)
        shears_parent.setText(0, "  › Shears")
        shears_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "wall_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "WallShears"
        })
        shears_parent.setExpanded(True)

        if not wall_elements:
            placeholder = QTreeWidgetItem(shears_parent)
            placeholder.setText(0, "    └ No piers/walls found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Create section for each pier/wall under Shears
        for element in wall_elements:
            pier_item = QTreeWidgetItem(shears_parent)
            pier_item.setText(0, f"    › {element.name}")
            pier_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_parent",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "element_id": element.id,
                "element_name": element.name
            })
            pier_item.setExpanded(True)

            # V2 Direction
            v2_item = QTreeWidgetItem(pier_item)
            v2_item.setText(0, "      ├ V2")
            v2_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "WallShears",
                "direction": "V2",
                "element_id": element.id
            })

            # V3 Direction
            v3_item = QTreeWidgetItem(pier_item)
            v3_item.setText(0, "      ├ V3")
            v3_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "WallShears",
                "direction": "V3",
                "element_id": element.id
            })

            # Max/Min Shears subsection
            maxmin_item = QTreeWidgetItem(pier_item)
            maxmin_item.setText(0, "      └ Max/Min")
            maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_maxmin_results",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "MaxMinWallShears",
                "element_id": element.id
            })

    def _add_quad_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, wall_elements):
        """Add Quad Rotations subsection with piers."""
        quad_parent = QTreeWidgetItem(parent_item)
        quad_parent.setText(0, "  › Quad Rotations")
        quad_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "wall_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "QuadRotations"
        })
        quad_parent.setExpanded(True)

        if not wall_elements:
            placeholder = QTreeWidgetItem(quad_parent)
            placeholder.setText(0, "    └ No piers/walls found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Create section for each pier/wall under Quad Rotations
        for element in wall_elements:
            pier_item = QTreeWidgetItem(quad_parent)
            pier_item.setText(0, f"    › {element.name}")
            pier_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_parent",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "element_id": element.id,
                "element_name": element.name
            })
            pier_item.setExpanded(True)

            # Rotation (no direction needed)
            rotation_item = QTreeWidgetItem(pier_item)
            rotation_item.setText(0, "      ├ Rotation")
            rotation_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "QuadRotations",
                "direction": "",  # No direction for rotations
                "element_id": element.id
            })

            # Max/Min Quad Rotations subsection
            maxmin_item = QTreeWidgetItem(pier_item)
            maxmin_item.setText(0, "      └ Max/Min")
            maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_maxmin_results",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "MaxMinQuadRotations",
                "element_id": element.id
            })

    def _add_result_type_with_directions(
        self,
        parent_item: QTreeWidgetItem,
        label: str,
        result_set_id: int,
        category: str,
        result_type: str,
        include_maxmin: bool = False,
        maxmin_label: str | None = None,
    ):
        """Add a result type item with X/Y subsections and optional Max/Min child."""
        parent_result_item = QTreeWidgetItem(parent_item)
        parent_result_item.setText(0, label)
        parent_result_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type_parent",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": result_type,
        })
        parent_result_item.setExpanded(True)

        x_item = QTreeWidgetItem(parent_result_item)
        x_item.setText(0, "   X Direction")
        x_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": result_type,
            "direction": "X",
        })

        y_item = QTreeWidgetItem(parent_result_item)
        y_item.setText(0, "   Y Direction")
        y_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": result_type,
            "direction": "Y",
        })

        if include_maxmin:
            label_text = maxmin_label or label.replace('> ', '').strip()
            maxmin_item = QTreeWidgetItem(parent_result_item)
            maxmin_item.setText(0, f"   Max/Min {label_text}")
            maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "maxmin_results",
                "result_set_id": result_set_id,
                "category": category,
                "result_type": f"MaxMin{result_type}",
            })


    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle tree item click."""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or not isinstance(data, dict):
            return

        item_type = data.get("type")

        if item_type == "result_type":
            # Emit with full hierarchy path including direction and optional element_id
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = data.get("result_type")
            direction = data.get("direction", "X")  # Default to X if not specified
            element_id = data.get("element_id", 0)  # 0 means no specific element (global results)
            self.selection_changed.emit(result_set_id, category, result_type, direction, element_id)
        elif item_type == "maxmin_results":
            # Emit for Max/Min results (no direction needed, no element)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = data.get("result_type")
            self.selection_changed.emit(result_set_id, category, result_type, "", 0)
        elif item_type == "element_maxmin_results":
            # Emit for element-specific Max/Min results (pier shears, etc.)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = data.get("result_type")
            element_id = data.get("element_id", 0)
            self.selection_changed.emit(result_set_id, category, result_type, "", element_id)




