"""Results tree browser - hierarchical navigation for project results."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout,
                             QWidget)

from .ui_helpers import create_styled_label


class ResultsTreeBrowser(QWidget):
    """Tree browser for navigating project results."""

    selection_changed = pyqtSignal(int, str, str, str, int)  # (result_set_id, category, result_type, direction, element_id)
    comparison_selected = pyqtSignal(int, str, str)  # (comparison_set_id, result_type, direction)
    comparison_element_selected = pyqtSignal(int, str, int, str)  # (comparison_set_id, result_type, element_id, direction)

    def __init__(self, project_id: int, parent=None):
        super().__init__(parent)
        self.project_id = project_id
        self.elements = []  # Will be populated with project elements
        self.setup_ui()

    def _has_data_for(self, result_set_id: int, result_type: str) -> bool:
        """Check if data exists for a given result type in a result set."""
        if not self.available_result_types:
            return True  # If no info provided, show all (backward compatibility)

        result_types_for_set = self.available_result_types.get(result_set_id, set())

        # If no info for this result set, show all (backward compatibility)
        if not result_types_for_set:
            return True

        return result_type in result_types_for_set

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
        self.tree.setIndentation(8)  # Reduced from 16px to 8px for laptop screens
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

    def populate_tree(self, result_sets, stories, elements=None, available_result_types=None, comparison_sets=None, pushover_cases=None):
        """Populate tree with project structure.

        Args:
            result_sets: List of ResultSet model instances
            stories: List of Story model instances
            elements: List of Element model instances (optional)
            available_result_types: Dict mapping result_set_id to set of available result types (optional)
            comparison_sets: List of ComparisonSet model instances (optional)
            pushover_cases: Dict mapping result_set_id to list of PushoverCase instances (optional)
        """
        self.tree.clear()
        self.elements = elements or []
        self.available_result_types = available_result_types or {}
        self.comparison_sets = comparison_sets or []
        self.pushover_cases = pushover_cases or {}

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

        if not result_sets and not self.comparison_sets:
            # Show empty state
            placeholder = QTreeWidgetItem(results_root)
            placeholder.setText(0, "└ No result sets")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            # Separate result sets by analysis type
            nltha_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', 'NLTHA') == 'NLTHA']
            pushover_sets = [rs for rs in result_sets if getattr(rs, 'analysis_type', 'NLTHA') == 'Pushover']

            # NLTHA section (if any NLTHA result sets exist)
            if nltha_sets:
                nltha_root = QTreeWidgetItem(results_root)
                nltha_root.setText(0, "◆ NLTHA")
                nltha_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "analysis_section", "analysis_type": "NLTHA"})
                nltha_root.setExpanded(True)

                for result_set in nltha_sets:
                    self._add_result_set(nltha_root, result_set)

                # Add comparison sets under NLTHA
                for comparison_set in self.comparison_sets:
                    self._add_comparison_set(nltha_root, comparison_set)

            # Pushover section (if any pushover result sets exist)
            if pushover_sets:
                pushover_root = QTreeWidgetItem(results_root)
                pushover_root.setText(0, "◆ Pushover")
                pushover_root.setData(0, Qt.ItemDataRole.UserRole, {"type": "analysis_section", "analysis_type": "Pushover"})
                pushover_root.setExpanded(True)

                # Add each pushover result set
                for result_set in pushover_sets:
                    self._add_pushover_result_set(pushover_root, result_set)

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
        global_item.setExpanded(True)  # Expanded to show result types

        # Result types under Global (only show if data exists)
        # Drifts with special subsections
        if self._has_data_for(result_set.id, "Drifts"):
            self._add_drifts_section(global_item, result_set.id)

        # Other result types
        if self._has_data_for(result_set.id, "Accelerations"):
            self._add_result_type_with_directions(
                global_item,
                "> Story Accelerations",
                result_set.id,
                "Envelopes",
                "Accelerations",
                include_maxmin=True,
                maxmin_label="Accelerations",
            )
        if self._has_data_for(result_set.id, "Forces"):
            self._add_result_type_with_directions(
                global_item,
                "> Story Forces",
                result_set.id,
                "Envelopes",
                "Forces",
                include_maxmin=True,
                maxmin_label="Story Forces",
            )
        if self._has_data_for(result_set.id, "Displacements"):
            self._add_result_type_with_directions(
                global_item,
                "> Floors Displacements",
                result_set.id,
                "Envelopes",
                "Displacements",
                include_maxmin=True,
                maxmin_label="Floors Displacements",
            )

        # Elements category - always create, child sections will self-filter
        elements_item = QTreeWidgetItem(envelopes_item)
        elements_item.setText(0, "◇ Elements")
        elements_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category_type",
            "result_set_id": result_set.id,
            "category": "Envelopes",
            "category_type": "Elements"
        })
        elements_item.setExpanded(True)  # Expanded to show element types (Walls, Columns, Beams)

        # Child sections check for data internally and return early if none exists
        self._add_walls_section(elements_item, result_set.id)
        self._add_columns_section(elements_item, result_set.id)
        self._add_beams_section(elements_item, result_set.id)

        # If no child sections were added (all returned early), hide the Elements section
        if elements_item.childCount() == 0:
            envelopes_item.removeChild(elements_item)

        # Joints category - for soil pressures and other joint-based results
        joints_item = QTreeWidgetItem(envelopes_item)
        joints_item.setText(0, "◇ Joints")
        joints_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category_type",
            "result_set_id": result_set.id,
            "category": "Envelopes",
            "category_type": "Joints"
        })
        joints_item.setExpanded(True)

        # Add soil pressures if available
        self._add_soil_pressures_section(joints_item, result_set.id)

        # Add vertical displacements if available
        self._add_vertical_displacements_section(joints_item, result_set.id)

        # If no child sections were added, hide the Joints section
        if joints_item.childCount() == 0:
            envelopes_item.removeChild(joints_item)

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

    def _add_comparison_set(self, parent_item: QTreeWidgetItem, comparison_set):
        """Add a comparison set with its hierarchy.

        Structure:
        └── Comparison Set Name (COM1, COM2, etc.)
            ├── Global Results
            │   ├── Drifts
            │   ├── Accelerations
            │   ├── Forces
            │   └── Displacements
            └── Elements
                ├── Walls
                ├── Columns
                └── Beams
        """
        # Main comparison set item
        comparison_item = QTreeWidgetItem(parent_item)
        comparison_item.setText(0, f"▸ {comparison_set.name}")
        comparison_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_set",
            "comparison_set_id": comparison_set.id,
            "comparison_set_name": comparison_set.name,
            "result_set_ids": comparison_set.result_set_ids,
            "result_types": comparison_set.result_types
        })
        comparison_item.setExpanded(False)

        # Global Results category
        if any(rt in comparison_set.result_types for rt in ['Drifts', 'Accelerations', 'Forces', 'Displacements']):
            global_item = QTreeWidgetItem(comparison_item)
            global_item.setText(0, "◇ Global")
            global_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_category",
                "comparison_set_id": comparison_set.id,
                "category": "Global"
            })
            global_item.setExpanded(True)

            # Add global result types
            if 'Drifts' in comparison_set.result_types:
                self._add_comparison_result_type_with_directions(
                    global_item, "› Drifts", comparison_set.id, "Drifts"
                )
            if 'Accelerations' in comparison_set.result_types:
                self._add_comparison_result_type_with_directions(
                    global_item, "› Accelerations", comparison_set.id, "Accelerations"
                )
            if 'Forces' in comparison_set.result_types:
                self._add_comparison_result_type_with_directions(
                    global_item, "› Forces", comparison_set.id, "Forces"
                )
            if 'Displacements' in comparison_set.result_types:
                self._add_comparison_result_type_with_directions(
                    global_item, "› Displacements", comparison_set.id, "Displacements"
                )

        # Elements category
        if any(rt in comparison_set.result_types for rt in ['WallShears', 'QuadRotations', 'ColumnShears', 'ColumnAxials', 'ColumnRotations', 'BeamRotations']):
            elements_item = QTreeWidgetItem(comparison_item)
            elements_item.setText(0, "◇ Elements")
            elements_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_category",
                "comparison_set_id": comparison_set.id,
                "category": "Elements"
            })
            elements_item.setExpanded(True)

            # Add element result types (simplified hierarchy for comparison)
            if 'WallShears' in comparison_set.result_types or 'QuadRotations' in comparison_set.result_types:
                self._add_comparison_walls_section(elements_item, comparison_set)
            if any(rt in comparison_set.result_types for rt in ['ColumnShears', 'ColumnAxials', 'ColumnRotations']):
                self._add_comparison_columns_section(elements_item, comparison_set)
            if 'BeamRotations' in comparison_set.result_types:
                self._add_comparison_beams_section(elements_item, comparison_set)

        # Joints category (foundation results)
        if any(rt in comparison_set.result_types for rt in ['SoilPressures', 'VerticalDisplacements']):
            joints_item = QTreeWidgetItem(comparison_item)
            joints_item.setText(0, "◈ Joints")
            joints_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_category",
                "comparison_set_id": comparison_set.id,
                "category": "Joints"
            })
            joints_item.setExpanded(True)

            # Add joint result types
            if 'SoilPressures' in comparison_set.result_types:
                self._add_comparison_joint_type(joints_item, comparison_set, 'SoilPressures', 'Soil Pressures')
            if 'VerticalDisplacements' in comparison_set.result_types:
                self._add_comparison_joint_type(joints_item, comparison_set, 'VerticalDisplacements', 'Vertical Displacements')

    def _add_comparison_result_type_with_directions(self, parent_item: QTreeWidgetItem, label: str, comparison_set_id: int, result_type: str):
        """Add a result type with X/Y directions for comparison sets."""
        result_type_parent = QTreeWidgetItem(parent_item)
        result_type_parent.setText(0, label)
        result_type_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_result_type_parent",
            "comparison_set_id": comparison_set_id,
            "result_type": result_type
        })
        result_type_parent.setExpanded(False)

        # X Direction
        x_item = QTreeWidgetItem(result_type_parent)
        x_item.setText(0, "  ├ X Direction")
        x_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_result_type",
            "comparison_set_id": comparison_set_id,
            "result_type": result_type,
            "direction": "X"
        })

        # Y Direction
        y_item = QTreeWidgetItem(result_type_parent)
        y_item.setText(0, "  └ Y Direction")
        y_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_result_type",
            "comparison_set_id": comparison_set_id,
            "result_type": result_type,
            "direction": "Y"
        })

    def _add_comparison_walls_section(self, parent_item: QTreeWidgetItem, comparison_set):
        """Add Walls section for comparison set."""
        walls_item = QTreeWidgetItem(parent_item)
        walls_item.setText(0, "› Walls")
        walls_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_element_category",
            "comparison_set_id": comparison_set.id,
            "element_type": "Walls"
        })
        walls_item.setExpanded(False)

        # Get wall elements
        wall_elements = [elem for elem in self.elements if elem.element_type == "Wall"]
        quad_elements = [elem for elem in self.elements if elem.element_type == "Quad"]

        if 'WallShears' in comparison_set.result_types:
            shears_item = QTreeWidgetItem(walls_item)
            shears_item.setText(0, "  › Shears")
            shears_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_element_result_parent",
                "comparison_set_id": comparison_set.id,
                "element_type": "Walls",
                "result_type": "WallShears"
            })
            shears_item.setExpanded(False)

            # Add individual wall elements with directions
            for element in wall_elements:
                element_parent = QTreeWidgetItem(shears_item)
                element_parent.setText(0, f"    › {element.name}")
                element_parent.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_parent",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Walls",
                    "result_type": "WallShears",
                    "element_id": element.id
                })
                element_parent.setExpanded(False)

                # V2 Direction
                v2_item = QTreeWidgetItem(element_parent)
                v2_item.setText(0, "      ├ V2")
                v2_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Walls",
                    "result_type": "WallShears",
                    "element_id": element.id,
                    "element_name": element.name,
                    "direction": "V2"
                })

                # V3 Direction
                v3_item = QTreeWidgetItem(element_parent)
                v3_item.setText(0, "      └ V3")
                v3_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Walls",
                    "result_type": "WallShears",
                    "element_id": element.id,
                    "element_name": element.name,
                    "direction": "V3"
                })

        if 'QuadRotations' in comparison_set.result_types:
            rotations_item = QTreeWidgetItem(walls_item)
            rotations_item.setText(0, "  └ Quad Rotations")
            rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_element_result_parent",
                "comparison_set_id": comparison_set.id,
                "element_type": "Walls",
                "result_type": "QuadRotations"
            })
            rotations_item.setExpanded(False)

            # Add "All Rotations" item first
            all_rotations_item = QTreeWidgetItem(rotations_item)
            all_rotations_item.setText(0, "    ├ All Rotations")
            all_rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_all_rotations",
                "comparison_set_id": comparison_set.id,
                "result_type": "QuadRotations"
            })

            # Add individual quad elements
            for element in quad_elements:
                element_item = QTreeWidgetItem(rotations_item)
                element_item.setText(0, f"    › {element.name}")
                element_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Walls",
                    "result_type": "QuadRotations",
                    "element_id": element.id,
                    "element_name": element.name
                })

    def _add_comparison_columns_section(self, parent_item: QTreeWidgetItem, comparison_set):
        """Add Columns section for comparison set."""
        columns_item = QTreeWidgetItem(parent_item)
        columns_item.setText(0, "› Columns")
        columns_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_element_category",
            "comparison_set_id": comparison_set.id,
            "element_type": "Columns"
        })
        columns_item.setExpanded(False)

        # Get column elements
        column_elements = [elem for elem in self.elements if elem.element_type == "Column"]

        # Add column result types
        if 'ColumnShears' in comparison_set.result_types:
            shears_item = QTreeWidgetItem(columns_item)
            shears_item.setText(0, "  › Shears")
            shears_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_element_result_parent",
                "comparison_set_id": comparison_set.id,
                "element_type": "Columns",
                "result_type": "ColumnShears"
            })
            shears_item.setExpanded(False)

            # Add individual column elements with directions
            for element in column_elements:
                element_parent = QTreeWidgetItem(shears_item)
                element_parent.setText(0, f"    › {element.name}")
                element_parent.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_parent",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Columns",
                    "result_type": "ColumnShears",
                    "element_id": element.id
                })
                element_parent.setExpanded(False)

                # V2 Direction
                v2_item = QTreeWidgetItem(element_parent)
                v2_item.setText(0, "      ├ V2")
                v2_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Columns",
                    "result_type": "ColumnShears",
                    "element_id": element.id,
                    "element_name": element.name,
                    "direction": "V2"
                })

                # V3 Direction
                v3_item = QTreeWidgetItem(element_parent)
                v3_item.setText(0, "      └ V3")
                v3_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Columns",
                    "result_type": "ColumnShears",
                    "element_id": element.id,
                    "element_name": element.name,
                    "direction": "V3"
                })

        if 'ColumnAxials' in comparison_set.result_types:
            axials_item = QTreeWidgetItem(columns_item)
            axials_item.setText(0, "  › Axials")
            axials_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_element_result_parent",
                "comparison_set_id": comparison_set.id,
                "element_type": "Columns",
                "result_type": "ColumnAxials"
            })
            axials_item.setExpanded(False)

            # Add individual column elements
            for element in column_elements:
                element_item = QTreeWidgetItem(axials_item)
                element_item.setText(0, f"    › {element.name}")
                element_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Columns",
                    "result_type": "ColumnAxials",
                    "element_id": element.id,
                    "element_name": element.name
                })

        if 'ColumnRotations' in comparison_set.result_types:
            rotations_item = QTreeWidgetItem(columns_item)
            rotations_item.setText(0, "  └ Rotations")
            rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_element_result_parent",
                "comparison_set_id": comparison_set.id,
                "element_type": "Columns",
                "result_type": "ColumnRotations"
            })
            rotations_item.setExpanded(False)

            # Add individual column elements
            for element in column_elements:
                element_item = QTreeWidgetItem(rotations_item)
                element_item.setText(0, f"    › {element.name}")
                element_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Columns",
                    "result_type": "ColumnRotations",
                    "element_id": element.id,
                    "element_name": element.name
                })

    def _add_comparison_beams_section(self, parent_item: QTreeWidgetItem, comparison_set):
        """Add Beams section for comparison set."""
        beams_item = QTreeWidgetItem(parent_item)
        beams_item.setText(0, "› Beams")
        beams_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_element_category",
            "comparison_set_id": comparison_set.id,
            "element_type": "Beams"
        })
        beams_item.setExpanded(False)

        # Get beam elements
        beam_elements = [elem for elem in self.elements if elem.element_type == "Beam"]

        if 'BeamRotations' in comparison_set.result_types:
            rotations_item = QTreeWidgetItem(beams_item)
            rotations_item.setText(0, "  └ Rotations")
            rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "comparison_element_result_parent",
                "comparison_set_id": comparison_set.id,
                "element_type": "Beams",
                "result_type": "BeamRotations"
            })
            rotations_item.setExpanded(False)

            # Add individual beam elements
            for element in beam_elements:
                element_item = QTreeWidgetItem(rotations_item)
                element_item.setText(0, f"    › {element.name}")
                element_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "comparison_element_result",
                    "comparison_set_id": comparison_set.id,
                    "element_type": "Beams",
                    "result_type": "BeamRotations",
                    "element_id": element.id,
                    "element_name": element.name
                })

    def _add_comparison_joint_type(self, parent_item: QTreeWidgetItem, comparison_set, result_type: str, display_name: str):
        """Add a joint result type with scatter plot view for comparison set.

        Args:
            parent_item: Parent tree item (Joints category)
            comparison_set: ComparisonSet model instance
            result_type: Result type key ('SoilPressures', 'VerticalDisplacements')
            display_name: Display name for the tree item
        """
        # Add "All [Type]" item for scatter plot view
        all_item = QTreeWidgetItem(parent_item)
        all_item.setText(0, f"  › All {display_name}")
        all_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_all_joints",
            "comparison_set_id": comparison_set.id,
            "result_type": result_type
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
        drifts_parent.setExpanded(False)  # Collapsed to hide directions

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
        # Check if any wall result types have data
        has_shears = self._has_data_for(result_set_id, "WallShears")
        has_quad_rotations = self._has_data_for(result_set_id, "QuadRotations")

        if not has_shears and not has_quad_rotations:
            return  # Don't show Walls section if no data

        # Walls parent item
        walls_parent = QTreeWidgetItem(parent_item)
        walls_parent.setText(0, "› Walls")
        walls_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "element_type": "Walls"
        })
        walls_parent.setExpanded(False)  # Collapsed to hide subcategories

        # Filter elements to get only walls/piers (for shears)
        wall_elements = [elem for elem in self.elements if elem.element_type == "Wall"]

        # Filter elements to get only quads (for rotations)
        quad_elements = [elem for elem in self.elements if elem.element_type == "Quad"]

        # Shears subsection under Walls (only if data exists)
        if has_shears:
            self._add_shears_section(walls_parent, result_set_id, wall_elements)

        # Quad Rotations subsection under Walls (only if data exists)
        if has_quad_rotations:
            self._add_quad_rotations_section(walls_parent, result_set_id, quad_elements)

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

    def _add_quad_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, quad_elements):
        """Add Quad Rotations subsection with quad elements.

        Structure:
        └── Quad Rotations
            ├── All Rotations
            │   ├── Max
            │   └── Min
            ├── Quad A-2
            │   ├── Rotation
            │   └── Max/Min
            └── Quad B-1
                ├── Rotation
                └── Max/Min
        """
        quad_parent = QTreeWidgetItem(parent_item)
        quad_parent.setText(0, "  › Quad Rotations")
        quad_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "wall_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "QuadRotations"
        })
        quad_parent.setExpanded(True)

        if not quad_elements:
            placeholder = QTreeWidgetItem(quad_parent)
            placeholder.setText(0, "    └ No quads found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Add "All Rotations" item as first item (before individual quads)
        all_rotations_item = QTreeWidgetItem(quad_parent)
        all_rotations_item.setText(0, "    ├ All Rotations")
        all_rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "all_rotations",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "QuadRotations"
        })

        # Create section for each quad element under Quad Rotations
        for element in quad_elements:
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

    def _add_columns_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Columns section with Shears, Min Axial, and Rotations subcategories.

        Structure:
        └── Columns
            ├── Shears
            │   ├── Column1 (dynamic, from database)
            │   │   ├── V2
            │   │   ├── V3
            │   │   └── Max/Min
            │   └── Column2
            │       ├── V2
            │       ├── V3
            │       └── Max/Min
            ├── Min Axial
            │   ├── Column1
            │   └── Column2
            └── Rotations
                ├── Column1
                │   ├── R2
                │   ├── R3
                │   └── Max/Min
                └── Column2
                    ├── R2
                    ├── R3
                    └── Max/Min
        """
        # Check if any column result types have data
        has_shears = self._has_data_for(result_set_id, "ColumnShears")
        has_axials = self._has_data_for(result_set_id, "ColumnAxials")
        has_rotations = self._has_data_for(result_set_id, "ColumnRotations")

        if not has_shears and not has_axials and not has_rotations:
            return  # Don't show Columns section if no data

        # Columns parent item
        columns_parent = QTreeWidgetItem(parent_item)
        columns_parent.setText(0, "› Columns")
        columns_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "element_type": "Columns"
        })
        columns_parent.setExpanded(False)  # Collapsed to hide subcategories

        # Filter elements to get only columns
        column_elements = [elem for elem in self.elements if elem.element_type == "Column"]

        # Shears subsection under Columns (only if data exists)
        if has_shears:
            self._add_column_shears_section(columns_parent, result_set_id, column_elements)

        # Min Axial subsection under Columns (only if data exists)
        if has_axials:
            self._add_column_min_axials_section(columns_parent, result_set_id, column_elements)

        # Rotations subsection under Columns (only if data exists)
        if has_rotations:
            self._add_column_rotations_section(columns_parent, result_set_id, column_elements)

    def _add_column_shears_section(self, parent_item: QTreeWidgetItem, result_set_id: int, column_elements):
        """Add Column Shears subsection with columns."""
        shears_parent = QTreeWidgetItem(parent_item)
        shears_parent.setText(0, "  › Shears")
        shears_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "column_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnShears"
        })
        shears_parent.setExpanded(True)

        if not column_elements:
            placeholder = QTreeWidgetItem(shears_parent)
            placeholder.setText(0, "    └ No columns found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Create section for each column under Shears
        for element in column_elements:
            column_item = QTreeWidgetItem(shears_parent)
            column_item.setText(0, f"    › {element.name}")
            column_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_parent",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "element_id": element.id,
                "element_name": element.name
            })
            column_item.setExpanded(True)

            # V2 Direction
            v2_item = QTreeWidgetItem(column_item)
            v2_item.setText(0, "      ├ V2")
            v2_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "ColumnShears",
                "direction": "V2",
                "element_id": element.id
            })

            # V3 Direction
            v3_item = QTreeWidgetItem(column_item)
            v3_item.setText(0, "      ├ V3")
            v3_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "ColumnShears",
                "direction": "V3",
                "element_id": element.id
            })

            # Max/Min Shears subsection
            maxmin_item = QTreeWidgetItem(column_item)
            maxmin_item.setText(0, "      └ Max/Min")
            maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_maxmin_results",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "MaxMinColumnShears",
                "element_id": element.id
            })

    def _add_column_min_axials_section(self, parent_item: QTreeWidgetItem, result_set_id: int, column_elements):
        """Add Column Min Axial subsection with columns (no Max/Min, just regular view)."""
        minaxial_parent = QTreeWidgetItem(parent_item)
        minaxial_parent.setText(0, "  › Min Axial")
        minaxial_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "column_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MinAxial"
        })
        minaxial_parent.setExpanded(True)

        if not column_elements:
            placeholder = QTreeWidgetItem(minaxial_parent)
            placeholder.setText(0, "    └ No columns found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Create section for each column under Min Axial (no directions, just column names)
        for element in column_elements:
            column_item = QTreeWidgetItem(minaxial_parent)
            column_item.setText(0, f"    └ {element.name}")
            column_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "MinAxial",
                "direction": "",  # No direction for axial forces
                "element_id": element.id
            })

    def _add_column_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, column_elements):
        """Add Column Rotations subsection with columns (R2 and R3 directions).

        Structure:
        └── Rotations
            ├── All Rotations
            ├── Column1
            │   ├── R2
            │   ├── R3
            │   └── Max/Min
            └── Column2
                ├── R2
                ├── R3
                └── Max/Min
        """
        rotations_parent = QTreeWidgetItem(parent_item)
        rotations_parent.setText(0, "  › Rotations")
        rotations_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "column_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnRotations"
        })
        rotations_parent.setExpanded(True)

        if not column_elements:
            placeholder = QTreeWidgetItem(rotations_parent)
            placeholder.setText(0, "    └ No columns found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Add "All Rotations" item as first item (before individual columns)
        all_rotations_item = QTreeWidgetItem(rotations_parent)
        all_rotations_item.setText(0, "    ├ All Rotations")
        all_rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "all_column_rotations",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnRotations"
        })

        # Create section for each column under Rotations
        for element in column_elements:
            column_item = QTreeWidgetItem(rotations_parent)
            column_item.setText(0, f"    › {element.name}")
            column_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_parent",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "element_id": element.id,
                "element_name": element.name
            })
            column_item.setExpanded(True)

            # R2 Direction
            r2_item = QTreeWidgetItem(column_item)
            r2_item.setText(0, "      ├ R2")
            r2_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "ColumnRotations",
                "direction": "R2",
                "element_id": element.id
            })

            # R3 Direction
            r3_item = QTreeWidgetItem(column_item)
            r3_item.setText(0, "      ├ R3")
            r3_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "result_type",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "ColumnRotations",
                "direction": "R3",
                "element_id": element.id
            })

            # Max/Min Rotations subsection
            maxmin_item = QTreeWidgetItem(column_item)
            maxmin_item.setText(0, "      └ Max/Min")
            maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "element_maxmin_results",
                "result_set_id": result_set_id,
                "category": "Envelopes",
                "result_type": "MaxMinColumnRotations",
                "element_id": element.id
            })

    def _add_beams_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Beams section with Rotations (R3 Plastic) subcategory.

        Structure:
        └── Beams
            └── Rotations (R3 Plastic)
                ├── All Rotations
                ├── Beam1
                │   ├── Table
                │   └── Plot
                └── Beam2
                    ├── Table
                    └── Plot
        """
        # Check if beam rotation data exists
        has_beam_rotations = self._has_data_for(result_set_id, "BeamRotations")

        if not has_beam_rotations:
            return  # Don't show Beams section if no data

        beams_parent = QTreeWidgetItem(parent_item)
        beams_parent.setText(0, "› Beams")
        beams_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_category",
            "category": "Elements",
            "result_set_id": result_set_id
        })
        beams_parent.setExpanded(False)

        # Get beam elements from database
        beam_elements = [el for el in self.elements if el.element_type == "Beam"]

        if not beam_elements:
            return

        # Add Rotations (R3 Plastic) subsection
        self._add_beam_rotations_section(beams_parent, result_set_id, beam_elements)

    def _add_beam_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, beam_elements):
        """Add Beam Rotations (R3 Plastic) subsection with Plot and Table tabs.

        Structure:
        └── Rotations (R3 Plastic)
            ├── Plot (All Rotations scatter plot)
            └── Table (Wide-format table with all beams)
        """
        rotations_parent = QTreeWidgetItem(parent_item)
        rotations_parent.setText(0, "  › Rotations (R3 Plastic)")
        rotations_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "beam_result_type_parent",
            "category": "Elements",
            "result_set_id": result_set_id
        })
        rotations_parent.setExpanded(False)

        # Plot tab - All Rotations scatter plot
        plot_item = QTreeWidgetItem(rotations_parent)
        plot_item.setText(0, "    ├ Plot")
        plot_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "beam_rotations_plot",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "BeamRotations"
        })

        # Table tab - Wide-format table with all beams
        table_item = QTreeWidgetItem(rotations_parent)
        table_item.setText(0, "    └ Table")
        table_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "beam_rotations_table",
            "result_set_id": result_set_id,
            "category": "Elements",
            "result_type": "BeamRotations"
        })

    def _add_soil_pressures_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add soil pressures section under Joints category with Plot and Table tabs.

        Structure:
        └── Soil Pressures (Min)
            ├── Plot (Scatter plot of all foundation elements)
            └── Table (Wide-format table with all elements)
        """
        # Check if soil pressure data exists
        if not self._has_data_for(result_set_id, "SoilPressures_Min"):
            return

        # Create parent item for Soil Pressures
        soil_parent = QTreeWidgetItem(parent_item)
        soil_parent.setText(0, "  › Soil Pressures (Min)")
        soil_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "soil_pressure_parent",
            "category": "Joints",
            "result_set_id": result_set_id
        })
        soil_parent.setExpanded(False)

        # Plot tab - Scatter plot of all foundation elements
        plot_item = QTreeWidgetItem(soil_parent)
        plot_item.setText(0, "    ├ Plot")
        plot_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "soil_pressure_plot",
            "result_set_id": result_set_id,
            "category": "Joints",
            "result_type": "SoilPressures_Min"
        })

        # Table tab - Wide-format table with all foundation elements
        table_item = QTreeWidgetItem(soil_parent)
        table_item.setText(0, "    └ Table")
        table_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "soil_pressure_table",
            "result_set_id": result_set_id,
            "category": "Joints",
            "result_type": "SoilPressures_Min"
        })

    def _add_vertical_displacements_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add vertical displacements section under Joints category with Plot and Table tabs.

        Structure:
        └── Vertical Displacements (Min)
            ├── Plot (Scatter plot of all foundation joints)
            └── Table (Wide-format table with all joints)
        """
        # Check if vertical displacement data exists
        if not self._has_data_for(result_set_id, "VerticalDisplacements_Min"):
            return

        # Create parent item for Vertical Displacements
        vert_disp_parent = QTreeWidgetItem(parent_item)
        vert_disp_parent.setText(0, "  › Vertical Displacements (Min)")
        vert_disp_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "vertical_displacement_parent",
            "category": "Joints",
            "result_set_id": result_set_id
        })
        vert_disp_parent.setExpanded(False)

        # Plot tab - Scatter plot of all foundation joints
        plot_item = QTreeWidgetItem(vert_disp_parent)
        plot_item.setText(0, "    ├ Plot")
        plot_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "vertical_displacement_plot",
            "result_set_id": result_set_id,
            "category": "Joints",
            "result_type": "VerticalDisplacements_Min"
        })

        # Table tab - Wide-format table with all foundation joints
        table_item = QTreeWidgetItem(vert_disp_parent)
        table_item.setText(0, "    └ Table")
        table_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "vertical_displacement_table",
            "result_set_id": result_set_id,
            "category": "Joints",
            "result_type": "VerticalDisplacements_Min"
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
        parent_result_item.setExpanded(False)  # Collapsed to hide directions

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
        elif item_type == "all_rotations":
            # Emit for All Rotations view (both Max and Min on same plot)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllQuadRotations"
            self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all elements
        elif item_type == "all_column_rotations":
            # Emit for All Column Rotations view (both Max and Min on same plot)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllColumnRotations"
            self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all elements
        elif item_type == "beam_rotations_plot":
            # Emit for Beam Rotations Plot view (All Rotations scatter plot)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllBeamRotations"
            self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all elements
        elif item_type == "beam_rotations_table":
            # Emit for Beam Rotations Table view (wide-format table)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "BeamRotationsTable"
            self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all elements
        elif item_type == "soil_pressure_plot":
            # Emit for Soil Pressure Plot view (scatter plot of all foundation elements)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllSoilPressures"  # Special type for scatter plot
            self.selection_changed.emit(result_set_id, category, result_type, "", -3)  # -3 means soil pressure plot
        elif item_type == "soil_pressure_table":
            # Emit for Soil Pressure Table view (wide-format table)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "SoilPressuresTable"  # Special type for table
            self.selection_changed.emit(result_set_id, category, result_type, "", -4)  # -4 means soil pressure table
        elif item_type == "vertical_displacement_plot":
            # Emit for Vertical Displacement Plot view (scatter plot of all foundation joints)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllVerticalDisplacements"  # Special type for scatter plot
            self.selection_changed.emit(result_set_id, category, result_type, "", -5)  # -5 means vertical displacement plot
        elif item_type == "vertical_displacement_table":
            # Emit for Vertical Displacement Table view (wide-format table)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "VerticalDisplacementsTable"  # Special type for table
            self.selection_changed.emit(result_set_id, category, result_type, "", -6)  # -6 means vertical displacement table
        elif item_type == "comparison_result_type":
            # Emit for comparison set result type with direction
            comparison_set_id = data.get("comparison_set_id")
            result_type = data.get("result_type")
            direction = data.get("direction", "X")
            self.comparison_selected.emit(comparison_set_id, result_type, direction)
        elif item_type == "comparison_element_result":
            # Emit for comparison set element result with specific element
            comparison_set_id = data.get("comparison_set_id")
            result_type = data.get("result_type")
            element_id = data.get("element_id")
            element_name = data.get("element_name", "")
            direction = data.get("direction")  # Get direction from tree item data

            self.comparison_element_selected.emit(comparison_set_id, result_type, element_id, direction)
        elif item_type == "comparison_all_rotations":
            # Emit for comparison all rotations view
            comparison_set_id = data.get("comparison_set_id")
            result_type = data.get("result_type")  # QuadRotations
            # Use special signal or reuse comparison_selected with special marker
            self.comparison_selected.emit(comparison_set_id, result_type, "All")

        elif item_type == "comparison_all_joints":
            # Emit for comparison all joints (soil pressures, vertical displacements)
            comparison_set_id = data.get("comparison_set_id")
            result_type = data.get("result_type")  # SoilPressures, VerticalDisplacements
            self.comparison_selected.emit(comparison_set_id, result_type, "AllJoints")

        elif item_type == "pushover_global_result":
            # Emit for pushover global result (Story Drifts, Forces, Displacements)
            result_set_id = data.get("result_set_id")
            result_type = data.get("result_type")  # "Story Drifts", "Story Forces", "Floor Displacements"
            direction = data.get("direction")  # "X" or "Y"

            # Map display name to internal type
            type_map = {
                "Story Drifts": "Drifts",
                "Story Forces": "Forces",
                "Floor Displacements": "Displacements"
            }
            internal_type = type_map.get(result_type, result_type)

            self.selection_changed.emit(result_set_id, "Pushover", internal_type, direction, 0)

        elif item_type == "pushover_curve":
            # Emit for pushover curve (case_name is stored in direction field)
            result_set_id = data.get("result_set_id")
            case_name = data.get("case_name")
            self.selection_changed.emit(result_set_id, "Pushover", "Curves", case_name, 0)

        elif item_type == "pushover_all_curves":
            # Emit for all pushover curves in a direction
            result_set_id = data.get("result_set_id")
            direction = data.get("direction")  # X or Y
            # Use "AllCurves_X" or "AllCurves_Y" as the identifier
            self.selection_changed.emit(result_set_id, "Pushover", "AllCurves", direction, 0)

        elif item_type == "pushover_wall_result":
            # Emit for pushover wall result (V2 or V3 shear)
            result_set_id = data.get("result_set_id")
            result_type = data.get("result_type")  # "WallShears"
            direction = data.get("direction")  # "V2" or "V3"
            element_id = data.get("element_id")

            self.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)

        elif item_type == "pushover_quad_rotation_result":
            # Emit for pushover quad rotation result
            result_set_id = data.get("result_set_id")
            result_type = data.get("result_type")  # "QuadRotations"
            direction = data.get("direction")  # "" (no direction for rotations)
            element_id = data.get("element_id")

            self.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)

        elif item_type == "pushover_column_result":
            # Emit for pushover column rotation result (R2 or R3)
            result_set_id = data.get("result_set_id")
            result_type_with_suffix = data.get("result_type")  # "ColumnRotations_R2" or "ColumnRotations_R3"
            direction = data.get("direction")  # "R2" or "R3"
            element_id = data.get("element_id")

            # Strip the _R2 or _R3 suffix to get base result type
            result_type = "ColumnRotations"

            print(f"[DEBUG] Browser: pushover_column_result clicked - result_type={result_type}, direction={direction}, element_id={element_id}")
            self.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)

        elif item_type == "pushover_column_shear_result":
            # Emit for pushover column shear result (V2 or V3)
            result_set_id = data.get("result_set_id")
            result_type = data.get("result_type")  # "ColumnShears"
            direction = data.get("direction")  # "V2" or "V3"
            element_id = data.get("element_id")

            print(f"[DEBUG] Browser: pushover_column_shear_result clicked - result_type={result_type}, direction={direction}, element_id={element_id}")
            self.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)

        elif item_type == "pushover_beam_result":
            # Emit for pushover beam rotation result (R3 Plastic)
            result_set_id = data.get("result_set_id")
            result_type = data.get("result_type")  # "BeamRotations"
            direction = data.get("direction")  # ""
            element_id = data.get("element_id")

            print(f"[DEBUG] Browser: pushover_beam_result clicked - result_type={result_type}, element_id={element_id}")
            self.selection_changed.emit(result_set_id, "Pushover", result_type, direction, element_id)

        elif item_type == "pushover_all_column_rotations":
            # Emit for All Column Rotations view (scatter plot showing all columns)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllColumnRotations"

            print(f"[DEBUG] Browser: pushover_all_column_rotations clicked - result_type={result_type}")
            self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all elements

        elif item_type == "pushover_beam_rotations_plot":
            # Emit for All Beam Rotations plot view (scatter plot showing all beams)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllBeamRotations"

            print(f"[DEBUG] Browser: pushover_beam_rotations_plot clicked - result_type={result_type}")
            self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all beams

        elif item_type == "pushover_beam_rotations_table":
            # Emit for Beam Rotations table view (wide-format table with all beams)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "BeamRotationsTable"

            print(f"[DEBUG] Browser: pushover_beam_rotations_table clicked - result_type={result_type}")
            self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all beams

        elif item_type == "pushover_joint_displacement_result":
            # Emit for pushover joint displacement result (Ux, Uy, Uz)
            result_set_id = data.get("result_set_id")
            result_type = data.get("result_type")  # "JointDisplacements_Ux", "JointDisplacements_Uy", "JointDisplacements_Uz"
            direction = data.get("direction")  # "Ux", "Uy", "Uz"

            print(f"[DEBUG] Browser: pushover_joint_displacement_result clicked - result_type={result_type}, direction={direction}")
            self.selection_changed.emit(result_set_id, "Pushover", result_type, direction, -7)  # -7 means joint displacement table

        elif item_type == "pushover_soil_pressure_plot":
            # Emit for Pushover Soil Pressure Plot view (scatter plot of all foundation elements)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllSoilPressures"  # Special type for scatter plot

            print(f"[DEBUG] Browser: pushover_soil_pressure_plot clicked - result_type={result_type}")
            self.selection_changed.emit(result_set_id, category, result_type, "", -3)  # -3 means soil pressure plot

        elif item_type == "pushover_soil_pressure_table":
            # Emit for Pushover Soil Pressure Table view (wide-format table)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "SoilPressuresTable"  # Special type for table

            print(f"[DEBUG] Browser: pushover_soil_pressure_table clicked - result_type={result_type}")
            self.selection_changed.emit(result_set_id, category, result_type, "", -4)  # -4 means soil pressure table

        elif item_type == "pushover_vertical_displacement_plot":
            # Emit for Pushover Vertical Displacement Plot view (scatter plot of all foundation joints)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "AllVerticalDisplacements"  # Special type for scatter plot

            print(f"[DEBUG] Browser: pushover_vertical_displacement_plot clicked - result_type={result_type}")
            self.selection_changed.emit(result_set_id, category, result_type, "", -5)  # -5 means vertical displacement plot

        elif item_type == "pushover_vertical_displacement_table":
            # Emit for Pushover Vertical Displacement Table view (wide-format table)
            result_set_id = data.get("result_set_id")
            category = data.get("category")
            result_type = "VerticalDisplacementsTable"  # Special type for table

            print(f"[DEBUG] Browser: pushover_vertical_displacement_table clicked - result_type={result_type}")
            self.selection_changed.emit(result_set_id, category, result_type, "", -6)  # -6 means vertical displacement table

    def _add_pushover_result_set(self, parent_item: QTreeWidgetItem, result_set):
        """Add a pushover result set with Curves, Global Results, and Elements sections.

        Structure:
        └── Result Set Name (e.g., "160Will_Push")
            ├── Curves
            │   ├── X Direction
            │   │   ├── Push_Mod_X+Ecc+
            │   │   └── ...
            │   └── Y Direction
            │       ├── Push_Mod_Y+Ecc+
            │       └── ...
            ├── Global Results
            │   ├── Story Drifts
            │   │   ├── X
            │   │   └── Y
            │   ├── Story Forces
            │   │   ├── X
            │   │   └── Y
            │   └── Floor Displacements
            │       ├── X
            │       └── Y
            └── Elements
                └── Walls
                    ├── P1
                    │   ├── V2
                    │   └── V3
                    └── P2
                        ├── V2
                        └── V3
        """
        # Result set item
        result_set_item = QTreeWidgetItem(parent_item)
        result_set_item.setText(0, f"▸ {result_set.name}")
        result_set_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_result_set",
            "id": result_set.id
        })
        result_set_item.setExpanded(True)

        # Curves category (parent level)
        curves_item = QTreeWidgetItem(result_set_item)
        curves_item.setText(0, "◆ Curves")
        curves_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_curves_category",
            "result_set_id": result_set.id
        })
        curves_item.setExpanded(True)

        # Get cases for this result set
        all_cases = self.pushover_cases.get(result_set.id, [])

        # Separate by direction
        x_cases = [c for c in all_cases if c.direction == 'X']
        y_cases = [c for c in all_cases if c.direction == 'Y']

        # Add X Direction under Curves
        if x_cases or True:  # Always show even if empty
            self._add_direction_section(curves_item, 'X', x_cases, result_set.id)

        # Add Y Direction under Curves
        if y_cases or True:  # Always show even if empty
            self._add_direction_section(curves_item, 'Y', y_cases, result_set.id)

        # Global Results category (same level as Curves)
        global_item = QTreeWidgetItem(result_set_item)
        global_item.setText(0, "◆ Global Results")
        global_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_global_category",
            "result_set_id": result_set.id
        })
        global_item.setExpanded(True)

        # Add global result types
        self._add_pushover_global_result_type(global_item, "Story Drifts", result_set.id)
        self._add_pushover_global_result_type(global_item, "Story Forces", result_set.id)
        self._add_pushover_global_result_type(global_item, "Floor Displacements", result_set.id)

        # Elements category (same level as Curves and Global Results)
        elements_item = QTreeWidgetItem(result_set_item)
        elements_item.setText(0, "◆ Elements")
        elements_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_elements_category",
            "result_set_id": result_set.id
        })
        elements_item.setExpanded(True)

        # Add walls section
        self._add_pushover_walls_section(elements_item, result_set.id)

        # Add columns section
        self._add_pushover_columns_section(elements_item, result_set.id)

        # Add beams section
        self._add_pushover_beams_section(elements_item, result_set.id)

        # If no child sections were added, hide the Elements section
        if elements_item.childCount() == 0:
            result_set_item.removeChild(elements_item)

        # Joints category (same level as Curves, Global Results, and Elements)
        joints_item = QTreeWidgetItem(result_set_item)
        joints_item.setText(0, "◆ Joints")
        joints_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_joints_category",
            "result_set_id": result_set.id
        })
        joints_item.setExpanded(True)

        # Add joint displacement sections
        self._add_pushover_joint_displacements_section(joints_item, result_set.id)

        # Add soil pressures if available
        self._add_pushover_soil_pressures_section(joints_item, result_set.id)

        # Add vertical displacements if available
        self._add_pushover_vertical_displacements_section(joints_item, result_set.id)

        # If no child sections were added, hide the Joints section
        if joints_item.childCount() == 0:
            result_set_item.removeChild(joints_item)

    def _add_direction_section(self, parent_item: QTreeWidgetItem, direction: str, cases: list, result_set_id: int):
        """Add X or Y direction section under Curves."""
        # Direction item
        direction_item = QTreeWidgetItem(parent_item)
        direction_item.setText(0, f"▸ {direction} Direction")
        direction_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_direction",
            "direction": direction,
            "result_set_id": result_set_id
        })
        direction_item.setExpanded(True)

        # Add curves
        if not cases:
            placeholder = QTreeWidgetItem(direction_item)
            placeholder.setText(0, f"└ No {direction} curves imported yet")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        else:
            for case in cases:
                case_item = QTreeWidgetItem(direction_item)
                case_item.setText(0, f"› {case.name}")
                case_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "type": "pushover_curve",
                    "case_name": case.name,
                    "pushover_case_id": case.id,
                    "result_set_id": result_set_id,
                    "direction": direction
                })

            # Add "All Curves" item at the end
            all_curves_item = QTreeWidgetItem(direction_item)
            all_curves_item.setText(0, f"› All Curves")
            all_curves_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_all_curves",
                "direction": direction,
                "result_set_id": result_set_id
            })

    def _add_pushover_global_result_type(self, parent_item: QTreeWidgetItem, result_type: str, result_set_id: int):
        """Add a global result type with X and Y direction children.

        Args:
            parent_item: Parent tree item (Global Results)
            result_type: Result type name (e.g., "Story Drifts", "Story Forces", "Floor Displacements")
            result_set_id: Result set ID
        """
        # Result type parent
        result_type_item = QTreeWidgetItem(parent_item)
        result_type_item.setText(0, f"▸ {result_type}")
        result_type_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_global_result_parent",
            "result_type": result_type,
            "result_set_id": result_set_id
        })
        result_type_item.setExpanded(False)

        # X Direction
        x_item = QTreeWidgetItem(result_type_item)
        x_item.setText(0, "  ├ X")
        x_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_global_result",
            "result_type": result_type,
            "direction": "X",
            "result_set_id": result_set_id
        })

        # Y Direction
        y_item = QTreeWidgetItem(result_type_item)
        y_item.setText(0, "  └ Y")
        y_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_global_result",
            "result_type": result_type,
            "direction": "Y",
            "result_set_id": result_set_id
        })

    def _add_pushover_walls_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Walls section for pushover results with pier shears and quad rotations.

        Structure (NLTHA-like but without Max/Min):
        └── Walls
            ├── Shears
            │   ├── P1
            │   │   ├── V2
            │   │   └── V3
            │   └── P2
            │       ├── V2
            │       └── V3
            └── Quad Rotations
                ├── 1
                └── 2
        """
        # Check if any wall result types have data
        has_wall_shears = self._has_data_for(result_set_id, "WallShears")
        has_quad_rotations = self._has_data_for(result_set_id, "QuadRotations")

        if not has_wall_shears and not has_quad_rotations:
            return  # Don't show Walls section if no data

        # Walls parent item
        walls_parent = QTreeWidgetItem(parent_item)
        walls_parent.setText(0, "› Walls")
        walls_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "element_type": "Walls"
        })
        walls_parent.setExpanded(False)

        # Filter elements
        wall_elements = [elem for elem in self.elements if elem.element_type == "Wall"]
        quad_elements = [elem for elem in self.elements if elem.element_type == "Quad"]

        # Add Shears subsection (only if data exists)
        if has_wall_shears:
            self._add_pushover_shears_section(walls_parent, result_set_id, wall_elements)

        # Add Quad Rotations subsection (only if data exists)
        if has_quad_rotations:
            self._add_pushover_quad_rotations_section(walls_parent, result_set_id, quad_elements)

    def _add_pushover_shears_section(self, parent_item: QTreeWidgetItem, result_set_id: int, wall_elements):
        """Add Shears subsection under Walls for pushover piers."""
        shears_parent = QTreeWidgetItem(parent_item)
        shears_parent.setText(0, "  › Shears")
        shears_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_wall_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "WallShears"
        })
        shears_parent.setExpanded(True)

        if not wall_elements:
            placeholder = QTreeWidgetItem(shears_parent)
            placeholder.setText(0, "    └ No piers/walls found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Create section for each pier under Shears
        for element in wall_elements:
            pier_item = QTreeWidgetItem(shears_parent)
            pier_item.setText(0, f"    › {element.name}")
            pier_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_wall_element",
                "result_set_id": result_set_id,
                "element_id": element.id,
                "element_name": element.name
            })
            pier_item.setExpanded(True)

            # V2 Direction
            v2_item = QTreeWidgetItem(pier_item)
            v2_item.setText(0, "      ├ V2")
            v2_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_wall_result",
                "result_set_id": result_set_id,
                "result_type": "WallShears",
                "direction": "V2",
                "element_id": element.id
            })

            # V3 Direction
            v3_item = QTreeWidgetItem(pier_item)
            v3_item.setText(0, "      └ V3")
            v3_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_wall_result",
                "result_set_id": result_set_id,
                "result_type": "WallShears",
                "direction": "V3",
                "element_id": element.id
            })

    def _add_pushover_quad_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, quad_elements):
        """Add Quad Rotations subsection under Walls for pushover quads."""
        quad_parent = QTreeWidgetItem(parent_item)
        quad_parent.setText(0, "  › Quad Rotations")
        quad_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_wall_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "QuadRotations"
        })
        quad_parent.setExpanded(True)

        if not quad_elements:
            placeholder = QTreeWidgetItem(quad_parent)
            placeholder.setText(0, "    └ No quads found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Create section for each quad element
        for element in quad_elements:
            quad_item = QTreeWidgetItem(quad_parent)
            quad_item.setText(0, f"    › {element.name}")
            quad_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_quad_rotation_result",
                "result_set_id": result_set_id,
                "result_type": "QuadRotations",
                "direction": "",  # No direction for rotations
                "element_id": element.id
            })

    def _add_pushover_columns_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Columns section for pushover column shears and rotations.

        Structure (NLTHA-like but without Max/Min):
        └── Columns
            ├── Shears
            │   ├── C1
            │   │   ├── V2
            │   │   └── V3
            │   └── C2
            │       ├── V2
            │       └── V3
            └── Rotations
                ├── C1
                │   ├── R2
                │   └── R3
                └── C2
                    ├── R2
                    └── R3
        """
        # Check if any column data exists
        has_column_shears = self._has_data_for(result_set_id, "ColumnShears")
        has_column_rotations = self._has_data_for(result_set_id, "ColumnRotations")

        if not has_column_shears and not has_column_rotations:
            return  # Don't show Columns section if no data

        # Columns parent item
        columns_parent = QTreeWidgetItem(parent_item)
        columns_parent.setText(0, "› Columns")
        columns_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "element_type": "Columns"
        })
        columns_parent.setExpanded(False)

        # Filter column elements
        column_elements = [elem for elem in self.elements if elem.element_type == "Column"]

        # Shears subsection under Columns (only if data exists)
        if has_column_shears:
            self._add_pushover_column_shears_section(columns_parent, result_set_id, column_elements)

        # Rotations subsection under Columns (only if data exists)
        if has_column_rotations:
            self._add_pushover_column_rotations_section(columns_parent, result_set_id, column_elements)

    def _add_pushover_column_shears_section(self, parent_item: QTreeWidgetItem, result_set_id: int, column_elements):
        """Add Column Shears subsection with columns (V2 and V3 directions).

        Structure:
        └── Shears
            ├── C1
            │   ├── V2
            │   └── V3
            └── C2
                ├── V2
                └── V3
        """
        shears_parent = QTreeWidgetItem(parent_item)
        shears_parent.setText(0, "  › Shears")
        shears_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_column_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "ColumnShears"
        })
        shears_parent.setExpanded(True)

        if not column_elements:
            placeholder = QTreeWidgetItem(shears_parent)
            placeholder.setText(0, "    └ No columns found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Create section for each column under Shears
        for element in column_elements:
            column_item = QTreeWidgetItem(shears_parent)
            column_item.setText(0, f"    › {element.name}")
            column_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_column_element",
                "result_set_id": result_set_id,
                "element_id": element.id,
                "element_name": element.name
            })
            column_item.setExpanded(True)

            # V2 Direction
            v2_item = QTreeWidgetItem(column_item)
            v2_item.setText(0, "      ├ V2")
            v2_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_column_shear_result",
                "result_set_id": result_set_id,
                "result_type": "ColumnShears",
                "direction": "V2",
                "element_id": element.id
            })

            # V3 Direction
            v3_item = QTreeWidgetItem(column_item)
            v3_item.setText(0, "      └ V3")
            v3_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_column_shear_result",
                "result_set_id": result_set_id,
                "result_type": "ColumnShears",
                "direction": "V3",
                "element_id": element.id
            })

    def _add_pushover_column_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, column_elements):
        """Add Column Rotations subsection with columns (R2 and R3 directions).

        Structure:
        └── Rotations
            ├── All Rotations
            ├── C1
            │   ├── R2
            │   └── R3
            └── C2
                ├── R2
                └── R3
        """
        rotations_parent = QTreeWidgetItem(parent_item)
        rotations_parent.setText(0, "  › Rotations")
        rotations_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_column_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "ColumnRotations"
        })
        rotations_parent.setExpanded(True)

        if not column_elements:
            placeholder = QTreeWidgetItem(rotations_parent)
            placeholder.setText(0, "    └ No columns found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Add "All Rotations" item as first item (before individual columns)
        all_rotations_item = QTreeWidgetItem(rotations_parent)
        all_rotations_item.setText(0, "    ├ All Rotations")
        all_rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_all_column_rotations",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "ColumnRotations"
        })

        # Create section for each column under Rotations
        for element in column_elements:
            column_item = QTreeWidgetItem(rotations_parent)
            column_item.setText(0, f"    › {element.name}")
            column_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_column_element",
                "result_set_id": result_set_id,
                "element_id": element.id,
                "element_name": element.name
            })
            column_item.setExpanded(True)

            # R2 Direction
            r2_item = QTreeWidgetItem(column_item)
            r2_item.setText(0, "      ├ R2")
            r2_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_column_result",
                "result_set_id": result_set_id,
                "result_type": "ColumnRotations_R2",
                "direction": "R2",
                "element_id": element.id
            })

            # R3 Direction
            r3_item = QTreeWidgetItem(column_item)
            r3_item.setText(0, "      └ R3")
            r3_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "pushover_column_result",
                "result_set_id": result_set_id,
                "result_type": "ColumnRotations_R3",
                "direction": "R3",
                "element_id": element.id
            })

    def _add_pushover_beams_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Beams section for pushover beam hinge rotations.

        Structure (NLTHA-like but without Max/Min):
        └── Beams
            └── Rotations
                ├── B1
                └── B2
        """
        # Check if beam rotation data exists
        has_beam_rotations = self._has_data_for(result_set_id, "BeamRotations")

        if not has_beam_rotations:
            return  # Don't show Beams section if no data

        # Beams parent item
        beams_parent = QTreeWidgetItem(parent_item)
        beams_parent.setText(0, "› Beams")
        beams_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "element_type": "Beams"
        })
        beams_parent.setExpanded(False)

        # Filter beam elements
        beam_elements = [elem for elem in self.elements if elem.element_type == "Beam"]

        # Rotations subsection under Beams
        if has_beam_rotations:
            self._add_pushover_beam_rotations_section(beams_parent, result_set_id, beam_elements)

    def _add_pushover_beam_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, beam_elements):
        """Add Beam Rotations subsection with Plot and Table views (R3 Plastic only).

        Structure:
        └── Rotations (R3 Plastic)
            ├── Plot (All Rotations scatter plot)
            └── Table (Wide-format table with all beams)
        """
        rotations_parent = QTreeWidgetItem(parent_item)
        rotations_parent.setText(0, "  › Rotations (R3 Plastic)")
        rotations_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_beam_result_type_parent",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "BeamRotations"
        })
        rotations_parent.setExpanded(False)

        if not beam_elements:
            placeholder = QTreeWidgetItem(rotations_parent)
            placeholder.setText(0, "    └ No beams found")
            placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
            return

        # Plot tab - All Rotations scatter plot
        plot_item = QTreeWidgetItem(rotations_parent)
        plot_item.setText(0, "    ├ Plot")
        plot_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_beam_rotations_plot",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "BeamRotations"
        })

        # Table tab - Wide-format table with all beams
        table_item = QTreeWidgetItem(rotations_parent)
        table_item.setText(0, "    └ Table")
        table_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_beam_rotations_table",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "BeamRotations"
        })

    def _add_pushover_joint_displacements_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Joint Displacements section for pushover joint results.

        Structure:
        └── Joint Displacements
            ├── Ux (mm)
            ├── Uy (mm)
            └── Uz (mm)
        """
        # Check if any joint displacement data exists (use base type without _Ux/_Uy/_Uz suffix)
        has_joint_displacements = self._has_data_for(result_set_id, "JointDisplacements")

        if not has_joint_displacements:
            return  # Don't show Joint Displacements section if no data

        # Joint Displacements parent item
        joint_disp_parent = QTreeWidgetItem(parent_item)
        joint_disp_parent.setText(0, "› Joint Displacements")
        joint_disp_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_joint_displacements_parent",
            "result_set_id": result_set_id
        })
        joint_disp_parent.setExpanded(True)

        # Add Ux direction (always show if joint displacements exist)
        ux_item = QTreeWidgetItem(joint_disp_parent)
        ux_item.setText(0, "  › Ux (mm)")
        ux_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_joint_displacement_result",
            "result_set_id": result_set_id,
            "result_type": "JointDisplacements_Ux",
            "direction": "Ux"
        })

        # Add Uy direction (always show if joint displacements exist)
        uy_item = QTreeWidgetItem(joint_disp_parent)
        uy_item.setText(0, "  › Uy (mm)")
        uy_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_joint_displacement_result",
            "result_set_id": result_set_id,
            "result_type": "JointDisplacements_Uy",
            "direction": "Uy"
        })

        # Add Uz direction (always show if joint displacements exist)
        uz_item = QTreeWidgetItem(joint_disp_parent)
        uz_item.setText(0, "  › Uz (mm)")
        uz_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_joint_displacement_result",
            "result_set_id": result_set_id,
            "result_type": "JointDisplacements_Uz",
            "direction": "Uz"
        })

    def _add_pushover_soil_pressures_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Soil Pressures section for pushover foundation results.

        Structure:
        └── Soil Pressures (Min)
            ├── Plot (Scatter plot of all foundation elements)
            └── Table (Wide-format table with all elements)
        """
        # Check if soil pressure data exists
        has_soil_pressures = self._has_data_for(result_set_id, "SoilPressures_Min")

        if not has_soil_pressures:
            return  # Don't show Soil Pressures section if no data

        # Create parent item for Soil Pressures
        soil_parent = QTreeWidgetItem(parent_item)
        soil_parent.setText(0, "  › Soil Pressures (Min)")
        soil_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_soil_pressure_parent",
            "result_set_id": result_set_id
        })
        soil_parent.setExpanded(False)

        # Plot tab - Scatter plot of all foundation elements
        plot_item = QTreeWidgetItem(soil_parent)
        plot_item.setText(0, "    ├ Plot")
        plot_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_soil_pressure_plot",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "AllSoilPressures"
        })

        # Table tab - Wide-format table with all elements
        table_item = QTreeWidgetItem(soil_parent)
        table_item.setText(0, "    └ Table")
        table_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_soil_pressure_table",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "SoilPressuresTable"
        })

    def _add_pushover_vertical_displacements_section(self, parent_item: QTreeWidgetItem, result_set_id: int):
        """Add Vertical Displacements section for pushover foundation results.

        Structure:
        └── Vertical Displacements (Min)
            ├── Plot (Scatter plot of all foundation joints)
            └── Table (Wide-format table with all joints)
        """
        # Check if vertical displacement data exists
        has_vert_displacements = self._has_data_for(result_set_id, "VerticalDisplacements_Min")

        if not has_vert_displacements:
            return  # Don't show Vertical Displacements section if no data

        # Create parent item for Vertical Displacements
        vert_disp_parent = QTreeWidgetItem(parent_item)
        vert_disp_parent.setText(0, "  › Vertical Displacements (Min)")
        vert_disp_parent.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_vertical_displacement_parent",
            "result_set_id": result_set_id
        })
        vert_disp_parent.setExpanded(False)

        # Plot tab - Scatter plot of all foundation joints
        plot_item = QTreeWidgetItem(vert_disp_parent)
        plot_item.setText(0, "    ├ Plot")
        plot_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_vertical_displacement_plot",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "AllVerticalDisplacements"
        })

        # Table tab - Wide-format table with all joints
        table_item = QTreeWidgetItem(vert_disp_parent)
        table_item.setText(0, "    └ Table")
        table_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_vertical_displacement_table",
            "result_set_id": result_set_id,
            "category": "Pushover",
            "result_type": "VerticalDisplacementsTable"
        })




