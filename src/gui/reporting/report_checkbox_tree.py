"""Checkbox tree widget for selecting report sections."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt6.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from sqlalchemy.orm import Session

from gui.styles import COLORS
from services.data_access import DataAccessService


class ReportCheckboxTree(QTreeWidget):
    """Tree widget with checkboxes for selecting report sections.

    Structure:
    ☑ Global Results
      ☑ Story Drifts
        ☑ X Direction
        ☑ Y Direction
      ☐ Story Forces
        ☐ X Direction
        ☐ Y Direction
      ...
    """

    selection_changed = pyqtSignal()

    # Mapping of cache result types to display names and units
    RESULT_TYPE_LABELS = {
        "Drifts": "Story Drifts",
        "Forces": "Story Forces",
        "Displacements": "Floor Displacements",
        "Accelerations": "Floor Accelerations",
    }

    # Units for each result type (matches config/result_config.py)
    RESULT_TYPE_UNITS = {
        "Drifts": "%",
        "Forces": "kN",
        "Displacements": "mm",
        "Accelerations": "g",
    }

    # Element result type labels
    ELEMENT_TYPE_LABELS = {
        "BeamRotations": "Beam Plastic Rotations",
        "ColumnRotations": "Column Plastic Rotations",
    }

    # Element result type units
    ELEMENT_TYPE_UNITS = {
        "BeamRotations": "%",
        "ColumnRotations": "%",
    }

    # Joint result type labels
    JOINT_TYPE_LABELS = {
        "SoilPressures_Min": "Soil Pressures (Min)",
    }

    # Joint result type units
    JOINT_TYPE_UNITS = {
        "SoilPressures_Min": "kN/m²",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setIndentation(20)
        self.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {COLORS['background']};
                border: none;
                color: {COLORS['text']};
                outline: none;
            }}
            QTreeWidget::item {{
                padding: 6px 4px;
                border-radius: 4px;
            }}
            QTreeWidget::item:hover {{
                background-color: {COLORS['hover']};
            }}
            QTreeWidget::indicator {{
                width: 16px;
                height: 16px;
            }}
            QTreeWidget::indicator:unchecked {{
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                background-color: transparent;
            }}
            QTreeWidget::indicator:checked {{
                border: 1px solid {COLORS['accent']};
                border-radius: 3px;
                background-color: {COLORS['accent']};
            }}
            QTreeWidget::indicator:indeterminate {{
                border: 1px solid {COLORS['accent']};
                border-radius: 3px;
                background-color: {COLORS['hover']};
            }}
        """)

        self.itemChanged.connect(self._on_item_changed)
        self._updating = False  # Prevent recursive updates

        # Debounce timer for selection_changed signal
        self._signal_timer = QTimer(self)
        self._signal_timer.setSingleShot(True)
        self._signal_timer.setInterval(100)  # 100ms debounce
        self._signal_timer.timeout.connect(self.selection_changed.emit)

    def populate_from_result_set(self, result_set_id: int, session_factory: Callable[[], Session]) -> None:
        """Populate tree with available result types for the given result set.

        Args:
            result_set_id: Result set ID to populate from
            session_factory: Callable that returns a new Session (used by DataAccessService)
        """
        self._updating = True
        self.clear()

        # Use DataAccessService for all queries
        data_service = DataAccessService(session_factory)

        # Query available result types from cache
        available_types = self._get_available_types(result_set_id, data_service)
        available_element_types = self._get_available_element_types(result_set_id, data_service)
        available_joint_types = self._get_available_joint_types(result_set_id, data_service)

        if not available_types and not available_element_types and not available_joint_types:
            # Show empty state
            empty_item = QTreeWidgetItem(self, ["No results available"])
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self._updating = False
            return

        # Create Global Results parent (if we have global results)
        if available_types:
            global_parent = QTreeWidgetItem(self, ["Global Results"])
            global_parent.setFlags(
                Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsUserCheckable |
                Qt.ItemFlag.ItemIsAutoTristate
            )
            global_parent.setCheckState(0, Qt.CheckState.Unchecked)
            global_parent.setData(0, Qt.ItemDataRole.UserRole, {"category": "Global"})

            # Add result types
            for base_type, directions in available_types.items():
                display_name = self.RESULT_TYPE_LABELS.get(base_type, base_type)

                type_item = QTreeWidgetItem(global_parent, [display_name])
                type_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsUserCheckable |
                    Qt.ItemFlag.ItemIsAutoTristate
                )
                type_item.setCheckState(0, Qt.CheckState.Unchecked)
                type_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "category": "Global",
                    "result_type": base_type
                })

                # Add direction children
                for direction in sorted(directions):
                    dir_item = QTreeWidgetItem(type_item, [f"{direction} Direction"])
                    dir_item.setFlags(
                        Qt.ItemFlag.ItemIsEnabled |
                        Qt.ItemFlag.ItemIsUserCheckable
                    )
                    dir_item.setCheckState(0, Qt.CheckState.Unchecked)
                    dir_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "category": "Global",
                        "result_type": base_type,
                        "direction": direction
                    })

            global_parent.setExpanded(True)

        # Create Element Results parent (if we have element results like BeamRotations)
        if available_element_types:
            element_parent = QTreeWidgetItem(self, ["Element Results"])
            element_parent.setFlags(
                Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsUserCheckable |
                Qt.ItemFlag.ItemIsAutoTristate
            )
            element_parent.setCheckState(0, Qt.CheckState.Unchecked)
            element_parent.setData(0, Qt.ItemDataRole.UserRole, {"category": "Element"})

            # Add element result types (e.g., BeamRotations)
            for elem_type in available_element_types:
                display_name = self.ELEMENT_TYPE_LABELS.get(elem_type, elem_type)

                type_item = QTreeWidgetItem(element_parent, [display_name])
                type_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsUserCheckable
                )
                type_item.setCheckState(0, Qt.CheckState.Unchecked)
                type_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "category": "Element",
                    "result_type": elem_type,
                    "direction": ""  # No direction for beam rotations
                })

            element_parent.setExpanded(True)

        # Create Joint Results parent (if we have joint results like SoilPressures)
        if available_joint_types:
            joint_parent = QTreeWidgetItem(self, ["Joint Results"])
            joint_parent.setFlags(
                Qt.ItemFlag.ItemIsEnabled |
                Qt.ItemFlag.ItemIsUserCheckable |
                Qt.ItemFlag.ItemIsAutoTristate
            )
            joint_parent.setCheckState(0, Qt.CheckState.Unchecked)
            joint_parent.setData(0, Qt.ItemDataRole.UserRole, {"category": "Joint"})

            # Add joint result types (e.g., SoilPressures_Min)
            for joint_type in available_joint_types:
                display_name = self.JOINT_TYPE_LABELS.get(joint_type, joint_type)

                type_item = QTreeWidgetItem(joint_parent, [display_name])
                type_item.setFlags(
                    Qt.ItemFlag.ItemIsEnabled |
                    Qt.ItemFlag.ItemIsUserCheckable
                )
                type_item.setCheckState(0, Qt.CheckState.Unchecked)
                type_item.setData(0, Qt.ItemDataRole.UserRole, {
                    "category": "Joint",
                    "result_type": joint_type,
                    "direction": ""  # No direction for joint results
                })

            joint_parent.setExpanded(True)

        self._updating = False

    def _get_available_types(self, result_set_id: int, data_service: DataAccessService) -> dict[str, set[str]]:
        """Query cache for available result types and directions via DataAccessService.

        The cache stores result_type as base type (e.g., "Drifts") and directions
        are embedded in the load case names within results_matrix JSON:
        - Drifts: "_X", "_Y" (e.g., "TH01_X", "TH01_Y")
        - Accelerations/Displacements: "_UX", "_UY" (e.g., "TH01_UX", "TH01_UY")
        - Forces: "_VX", "_VY" (e.g., "TH01_VX", "TH01_VY")
        """
        import json

        results = data_service.get_global_cache_with_matrix(result_set_id)

        # Parse result types and extract directions from matrix keys
        available: dict[str, set[str]] = {}
        for result_type, results_matrix in results:
            if result_type not in available:
                available[result_type] = set()

            # Parse the results_matrix JSON to extract directions from load case names
            if results_matrix:
                try:
                    matrix = json.loads(results_matrix) if isinstance(results_matrix, str) else results_matrix
                    for key in matrix.keys():
                        # Different result types use different direction suffixes:
                        # Drifts: _X, _Y
                        # Accelerations/Displacements: _UX, _UY
                        # Forces: _VX, _VY
                        if key.endswith("_X") or key.endswith("_UX") or key.endswith("_VX"):
                            available[result_type].add("X")
                        elif key.endswith("_Y") or key.endswith("_UY") or key.endswith("_VY"):
                            available[result_type].add("Y")
                except (json.JSONDecodeError, AttributeError):
                    pass

        return available

    def _get_available_element_types(self, result_set_id: int, data_service: DataAccessService) -> list[str]:
        """Query element cache for available element result types via DataAccessService.

        Returns list of available element result types (e.g., BeamRotations, ColumnRotations).
        """
        types = data_service.get_available_element_types_for_result_set(result_set_id)

        available = []
        for result_type in types:
            # Map specific cache types to base types
            if result_type.startswith("BeamRotations"):
                if "BeamRotations" not in available:
                    available.append("BeamRotations")
            elif result_type.startswith("ColumnRotations"):
                if "ColumnRotations" not in available:
                    available.append("ColumnRotations")

        return available

    def _get_available_joint_types(self, result_set_id: int, data_service: DataAccessService) -> list[str]:
        """Query joint cache for available joint result types via DataAccessService.

        Returns list of available joint result types (e.g., SoilPressures_Min).
        """
        types = data_service.get_available_joint_types_for_result_set(result_set_id)

        available = []
        for result_type in types:
            # Only include soil pressures for now
            if result_type == "SoilPressures_Min":
                if result_type not in available:
                    available.append(result_type)

        return available

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item check state changes."""
        if self._updating:
            return

        self._updating = True

        # Update parent states based on children
        self._update_parent_state(item)

        # Update children states based on parent
        self._update_children_state(item)

        self._updating = False
        # Debounce the signal to avoid excessive updates during rapid clicking
        self._signal_timer.start()

    def _update_parent_state(self, item: QTreeWidgetItem) -> None:
        """Update parent check state based on children."""
        parent = item.parent()
        if parent is None:
            return

        checked_count = 0
        total_count = parent.childCount()

        for i in range(total_count):
            child = parent.child(i)
            if child.checkState(0) == Qt.CheckState.Checked:
                checked_count += 1
            elif child.checkState(0) == Qt.CheckState.PartiallyChecked:
                checked_count += 0.5

        if checked_count == 0:
            parent.setCheckState(0, Qt.CheckState.Unchecked)
        elif checked_count == total_count:
            parent.setCheckState(0, Qt.CheckState.Checked)
        else:
            parent.setCheckState(0, Qt.CheckState.PartiallyChecked)

        # Recursively update grandparent
        self._update_parent_state(parent)

    def _update_children_state(self, item: QTreeWidgetItem) -> None:
        """Update children check states based on parent."""
        state = item.checkState(0)
        if state == Qt.CheckState.PartiallyChecked:
            return  # Don't propagate partial state to children

        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, state)
            self._update_children_state(child)

    def get_selected_sections(self, result_set_id: int, analysis_context: str = "NLTHA") -> list:
        """Get list of selected sections as ReportSection objects."""
        from .report_view import ReportSection

        sections = []
        self._collect_selected_items(self.invisibleRootItem(), result_set_id, sections, analysis_context)
        return sections

    def _collect_selected_items(self, parent: QTreeWidgetItem, result_set_id: int, sections: list, analysis_context: str = "NLTHA") -> None:
        """Recursively collect checked leaf items."""
        from .report_view import ReportSection

        for i in range(parent.childCount()):
            item = parent.child(i)
            data = item.data(0, Qt.ItemDataRole.UserRole)

            if item.childCount() == 0:
                # Leaf node - check if selected
                if item.checkState(0) == Qt.CheckState.Checked and data:
                    direction = data.get("direction", "")
                    result_type = data.get("result_type")
                    category = data.get("category", "Global")

                    if result_type:
                        # Element results (e.g., BeamRotations) don't have direction
                        if category == "Element":
                            display_name = self.ELEMENT_TYPE_LABELS.get(result_type, result_type)
                            unit = self.ELEMENT_TYPE_UNITS.get(result_type, "")
                            title = f"{display_name} [{unit}]" if unit else display_name
                            section = ReportSection(
                                title=title,
                                result_type=result_type,
                                direction=direction,
                                result_set_id=result_set_id,
                                category=category,
                                analysis_context=analysis_context
                            )
                            sections.append(section)
                        elif category == "Joint":
                            display_name = self.JOINT_TYPE_LABELS.get(result_type, result_type)
                            unit = self.JOINT_TYPE_UNITS.get(result_type, "")
                            title = f"{display_name} [{unit}]" if unit else display_name
                            section = ReportSection(
                                title=title,
                                result_type=result_type,
                                direction=direction,
                                result_set_id=result_set_id,
                                category=category,
                                analysis_context=analysis_context
                            )
                            sections.append(section)
                        elif direction:
                            # Global results require direction
                            display_name = self.RESULT_TYPE_LABELS.get(result_type, result_type)
                            unit = self.RESULT_TYPE_UNITS.get(result_type, "")
                            # Match normal window format: "Story Drifts [%] - X Direction"
                            title = f"{display_name} [{unit}] - {direction} Direction" if unit else f"{display_name} - {direction} Direction"
                            section = ReportSection(
                                title=title,
                                result_type=result_type,
                                direction=direction,
                                result_set_id=result_set_id,
                                category=category,
                                analysis_context=analysis_context
                            )
                            sections.append(section)
            else:
                # Parent node - recurse
                self._collect_selected_items(item, result_set_id, sections, analysis_context)

    def select_all(self) -> None:
        """Check all items."""
        self._updating = True
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Checked)
            self._update_children_state(item)
        self._updating = False
        self._signal_timer.start()

    def clear_selection(self) -> None:
        """Uncheck all items."""
        self._updating = True
        for i in range(self.topLevelItemCount()):
            item = self.topLevelItem(i)
            item.setCheckState(0, Qt.CheckState.Unchecked)
            self._update_children_state(item)
        self._updating = False
        self._signal_timer.start()
