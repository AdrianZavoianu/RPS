"""Comparison section builders for ResultsTreeBrowser.

This module contains builder functions for creating comparison set tree items,
including global comparisons, element comparisons, and joint comparisons.
"""

from typing import TYPE_CHECKING, List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

if TYPE_CHECKING:
    from database.models import ComparisonSet, Element


def add_comparison_set(
    parent_item: QTreeWidgetItem,
    comparison_set: "ComparisonSet",
    elements: List["Element"],
) -> None:
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

    Args:
        parent_item: Parent tree widget item
        comparison_set: ComparisonSet model instance
        elements: List of Element models from the project
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
            _add_result_type_with_directions(
                global_item, "› Drifts", comparison_set.id, "Drifts"
            )
        if 'Accelerations' in comparison_set.result_types:
            _add_result_type_with_directions(
                global_item, "› Accelerations", comparison_set.id, "Accelerations"
            )
        if 'Forces' in comparison_set.result_types:
            _add_result_type_with_directions(
                global_item, "› Forces", comparison_set.id, "Forces"
            )
        if 'Displacements' in comparison_set.result_types:
            _add_result_type_with_directions(
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
            _add_walls_section(elements_item, comparison_set, elements)
        if any(rt in comparison_set.result_types for rt in ['ColumnShears', 'ColumnAxials', 'ColumnRotations']):
            _add_columns_section(elements_item, comparison_set, elements)
        if 'BeamRotations' in comparison_set.result_types:
            _add_beams_section(elements_item, comparison_set, elements)

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
            _add_joint_type(joints_item, comparison_set, 'SoilPressures', 'Soil Pressures')
        if 'VerticalDisplacements' in comparison_set.result_types:
            _add_joint_type(joints_item, comparison_set, 'VerticalDisplacements', 'Vertical Displacements')


def _add_result_type_with_directions(
    parent_item: QTreeWidgetItem,
    label: str,
    comparison_set_id: int,
    result_type: str,
) -> None:
    """Add a result type with X/Y directions for comparison sets.

    Args:
        parent_item: Parent tree widget item
        label: Display label for the result type
        comparison_set_id: ID of the comparison set
        result_type: Result type name (e.g., 'Drifts', 'Forces')
    """
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


def _add_walls_section(
    parent_item: QTreeWidgetItem,
    comparison_set: "ComparisonSet",
    elements: List["Element"],
) -> None:
    """Add Walls section for comparison set.

    Args:
        parent_item: Parent tree widget item (Elements category)
        comparison_set: ComparisonSet model instance
        elements: List of Element models from the project
    """
    walls_item = QTreeWidgetItem(parent_item)
    walls_item.setText(0, "› Walls")
    walls_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "comparison_element_category",
        "comparison_set_id": comparison_set.id,
        "element_type": "Walls"
    })
    walls_item.setExpanded(False)

    # Get wall elements
    wall_elements = [elem for elem in elements if elem.element_type == "Wall"]
    quad_elements = [elem for elem in elements if elem.element_type == "Quad"]

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


def _add_columns_section(
    parent_item: QTreeWidgetItem,
    comparison_set: "ComparisonSet",
    elements: List["Element"],
) -> None:
    """Add Columns section for comparison set.

    Args:
        parent_item: Parent tree widget item (Elements category)
        comparison_set: ComparisonSet model instance
        elements: List of Element models from the project
    """
    columns_item = QTreeWidgetItem(parent_item)
    columns_item.setText(0, "› Columns")
    columns_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "comparison_element_category",
        "comparison_set_id": comparison_set.id,
        "element_type": "Columns"
    })
    columns_item.setExpanded(False)

    # Get column elements
    column_elements = [elem for elem in elements if elem.element_type == "Column"]

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

        all_item = QTreeWidgetItem(rotations_item)
        all_item.setText(0, "    > All Rotations")
        all_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_all_column_rotations",
            "comparison_set_id": comparison_set.id,
            "result_type": "ColumnRotations",
        })

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


def _add_beams_section(
    parent_item: QTreeWidgetItem,
    comparison_set: "ComparisonSet",
    elements: List["Element"],
) -> None:
    """Add Beams section for comparison set.

    Args:
        parent_item: Parent tree widget item (Elements category)
        comparison_set: ComparisonSet model instance
        elements: List of Element models from the project
    """
    beams_item = QTreeWidgetItem(parent_item)
    beams_item.setText(0, "› Beams")
    beams_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "comparison_element_category",
        "comparison_set_id": comparison_set.id,
        "element_type": "Beams"
    })
    beams_item.setExpanded(False)

    # Get beam elements
    beam_elements = [elem for elem in elements if elem.element_type == "Beam"]

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

        all_item = QTreeWidgetItem(rotations_item)
        all_item.setText(0, "    > All Rotations")
        all_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "comparison_all_beam_rotations",
            "comparison_set_id": comparison_set.id,
            "result_type": "BeamRotations"
        })

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


def _add_joint_type(
    parent_item: QTreeWidgetItem,
    comparison_set: "ComparisonSet",
    result_type: str,
    display_name: str,
) -> None:
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
