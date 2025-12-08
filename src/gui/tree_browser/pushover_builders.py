"""Pushover section builders for the results tree browser.

This module contains functions to build tree sections for Pushover analysis results.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gui.results_tree_browser import ResultsTreeBrowser


def add_pushover_result_set(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set) -> None:
    """Add a pushover result set with Curves, Global Results, Elements, and Joints sections."""
    # Result set item
    result_set_item = QTreeWidgetItem(parent_item)
    result_set_item.setText(0, f"▸ {result_set.name}")
    result_set_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_result_set",
        "id": result_set.id
    })
    result_set_item.setExpanded(True)

    # Curves category
    curves_item = QTreeWidgetItem(result_set_item)
    curves_item.setText(0, "◆ Curves")
    curves_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_curves_category",
        "result_set_id": result_set.id
    })
    curves_item.setExpanded(True)

    # Get cases for this result set
    all_cases = browser.pushover_cases.get(result_set.id, [])

    # Separate by direction
    x_cases = [c for c in all_cases if c.direction == 'X']
    y_cases = [c for c in all_cases if c.direction == 'Y']

    # Add X and Y direction sections
    add_direction_section(browser, curves_item, 'X', x_cases, result_set.id)
    add_direction_section(browser, curves_item, 'Y', y_cases, result_set.id)

    # Global Results category
    global_item = QTreeWidgetItem(result_set_item)
    global_item.setText(0, "◆ Global Results")
    global_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_global_category",
        "result_set_id": result_set.id
    })
    global_item.setExpanded(True)

    add_pushover_global_result_type(browser, global_item, "Story Drifts", result_set.id)
    add_pushover_global_result_type(browser, global_item, "Story Forces", result_set.id)
    add_pushover_global_result_type(browser, global_item, "Floor Displacements", result_set.id)

    # Elements category
    elements_item = QTreeWidgetItem(result_set_item)
    elements_item.setText(0, "◆ Elements")
    elements_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_elements_category",
        "result_set_id": result_set.id
    })
    elements_item.setExpanded(True)

    add_pushover_walls_section(browser, elements_item, result_set.id)
    add_pushover_columns_section(browser, elements_item, result_set.id)
    add_pushover_beams_section(browser, elements_item, result_set.id)

    if elements_item.childCount() == 0:
        result_set_item.removeChild(elements_item)

    # Joints category
    joints_item = QTreeWidgetItem(result_set_item)
    joints_item.setText(0, "◆ Joints")
    joints_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_joints_category",
        "result_set_id": result_set.id
    })
    joints_item.setExpanded(True)

    add_pushover_joint_displacements_section(browser, joints_item, result_set.id)
    add_pushover_soil_pressures_section(browser, joints_item, result_set.id)
    add_pushover_vertical_displacements_section(browser, joints_item, result_set.id)

    if joints_item.childCount() == 0:
        result_set_item.removeChild(joints_item)


def add_direction_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    direction: str,
    cases: list,
    result_set_id: int,
) -> None:
    """Add X or Y direction section under Curves."""
    direction_item = QTreeWidgetItem(parent_item)
    direction_item.setText(0, f"▸ {direction} Direction")
    direction_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_direction",
        "direction": direction,
        "result_set_id": result_set_id
    })
    direction_item.setExpanded(True)

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

        # Add "All Curves" item
        all_curves_item = QTreeWidgetItem(direction_item)
        all_curves_item.setText(0, "› All Curves")
        all_curves_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_all_curves",
            "direction": direction,
            "result_set_id": result_set_id
        })


def add_pushover_global_result_type(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_type: str,
    result_set_id: int,
) -> None:
    """Add a global result type with X and Y direction children."""
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


def add_pushover_walls_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Walls section for pushover results."""
    has_wall_shears = browser._has_data_for(result_set_id, "WallShears")
    has_quad_rotations = browser._has_data_for(result_set_id, "QuadRotations")

    if not has_wall_shears and not has_quad_rotations:
        return

    walls_parent = QTreeWidgetItem(parent_item)
    walls_parent.setText(0, "› Walls")
    walls_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "element_type_parent",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "element_type": "Walls"
    })
    walls_parent.setExpanded(False)

    wall_elements = [elem for elem in browser.elements if elem.element_type == "Wall"]
    quad_elements = [elem for elem in browser.elements if elem.element_type == "Quad"]

    if has_wall_shears:
        add_pushover_shears_section(browser, walls_parent, result_set_id, wall_elements)

    if has_quad_rotations:
        add_pushover_quad_rotations_section(browser, walls_parent, result_set_id, quad_elements)


def add_pushover_shears_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    wall_elements: List,
) -> None:
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


def add_pushover_quad_rotations_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    quad_elements: List,
) -> None:
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

    for element in quad_elements:
        quad_item = QTreeWidgetItem(quad_parent)
        quad_item.setText(0, f"    › {element.name}")
        quad_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "pushover_quad_rotation_result",
            "result_set_id": result_set_id,
            "result_type": "QuadRotations",
            "direction": "",
            "element_id": element.id
        })


def add_pushover_columns_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Columns section for pushover column shears and rotations."""
    has_column_shears = browser._has_data_for(result_set_id, "ColumnShears")
    has_column_rotations = browser._has_data_for(result_set_id, "ColumnRotations")

    if not has_column_shears and not has_column_rotations:
        return

    columns_parent = QTreeWidgetItem(parent_item)
    columns_parent.setText(0, "› Columns")
    columns_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "element_type_parent",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "element_type": "Columns"
    })
    columns_parent.setExpanded(False)

    column_elements = [elem for elem in browser.elements if elem.element_type == "Column"]

    if has_column_shears:
        add_pushover_column_shears_section(browser, columns_parent, result_set_id, column_elements)

    if has_column_rotations:
        add_pushover_column_rotations_section(browser, columns_parent, result_set_id, column_elements)


def add_pushover_column_shears_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    column_elements: List,
) -> None:
    """Add Column Shears subsection with columns."""
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


def add_pushover_column_rotations_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    column_elements: List,
) -> None:
    """Add Column Rotations subsection with columns."""
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

    # All Rotations item
    all_rotations_item = QTreeWidgetItem(rotations_parent)
    all_rotations_item.setText(0, "    ├ All Rotations")
    all_rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_all_column_rotations",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "result_type": "ColumnRotations"
    })

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


def add_pushover_beams_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Beams section for pushover beam rotations."""
    has_beam_rotations = browser._has_data_for(result_set_id, "BeamRotations")

    if not has_beam_rotations:
        return

    beams_parent = QTreeWidgetItem(parent_item)
    beams_parent.setText(0, "› Beams")
    beams_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "element_type_parent",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "element_type": "Beams"
    })
    beams_parent.setExpanded(False)

    beam_elements = [elem for elem in browser.elements if elem.element_type == "Beam"]
    add_pushover_beam_rotations_section(browser, beams_parent, result_set_id, beam_elements)


def add_pushover_beam_rotations_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    beam_elements: List,
) -> None:
    """Add Beam Rotations subsection with Plot and Table views."""
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

    # Plot tab
    plot_item = QTreeWidgetItem(rotations_parent)
    plot_item.setText(0, "    ├ Plot")
    plot_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_beam_rotations_plot",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "result_type": "BeamRotations"
    })

    # Table tab
    table_item = QTreeWidgetItem(rotations_parent)
    table_item.setText(0, "    └ Table")
    table_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_beam_rotations_table",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "result_type": "BeamRotations"
    })


def add_pushover_joint_displacements_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Joint Displacements section for pushover joint results."""
    has_joint_displacements = browser._has_data_for(result_set_id, "JointDisplacements")

    if not has_joint_displacements:
        return

    joint_disp_parent = QTreeWidgetItem(parent_item)
    joint_disp_parent.setText(0, "› Joint Displacements")
    joint_disp_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_joint_displacements_parent",
        "result_set_id": result_set_id
    })
    joint_disp_parent.setExpanded(True)

    # Ux direction
    ux_item = QTreeWidgetItem(joint_disp_parent)
    ux_item.setText(0, "  › Ux (mm)")
    ux_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_joint_displacement_result",
        "result_set_id": result_set_id,
        "result_type": "JointDisplacements_Ux",
        "direction": "Ux"
    })

    # Uy direction
    uy_item = QTreeWidgetItem(joint_disp_parent)
    uy_item.setText(0, "  › Uy (mm)")
    uy_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_joint_displacement_result",
        "result_set_id": result_set_id,
        "result_type": "JointDisplacements_Uy",
        "direction": "Uy"
    })

    # Uz direction
    uz_item = QTreeWidgetItem(joint_disp_parent)
    uz_item.setText(0, "  › Uz (mm)")
    uz_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_joint_displacement_result",
        "result_set_id": result_set_id,
        "result_type": "JointDisplacements_Uz",
        "direction": "Uz"
    })


def add_pushover_soil_pressures_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Soil Pressures section for pushover foundation results."""
    has_soil_pressures = browser._has_data_for(result_set_id, "SoilPressures_Min")

    if not has_soil_pressures:
        return

    soil_parent = QTreeWidgetItem(parent_item)
    soil_parent.setText(0, "  › Soil Pressures (Min)")
    soil_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_soil_pressure_parent",
        "result_set_id": result_set_id
    })
    soil_parent.setExpanded(False)

    # Plot tab
    plot_item = QTreeWidgetItem(soil_parent)
    plot_item.setText(0, "    ├ Plot")
    plot_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_soil_pressure_plot",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "result_type": "AllSoilPressures"
    })

    # Table tab
    table_item = QTreeWidgetItem(soil_parent)
    table_item.setText(0, "    └ Table")
    table_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_soil_pressure_table",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "result_type": "SoilPressuresTable"
    })


def add_pushover_vertical_displacements_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Vertical Displacements section for pushover foundation results."""
    has_vert_displacements = browser._has_data_for(result_set_id, "VerticalDisplacements_Min")

    if not has_vert_displacements:
        return

    vert_disp_parent = QTreeWidgetItem(parent_item)
    vert_disp_parent.setText(0, "  › Vertical Displacements (Min)")
    vert_disp_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_vertical_displacement_parent",
        "result_set_id": result_set_id
    })
    vert_disp_parent.setExpanded(False)

    # Plot tab
    plot_item = QTreeWidgetItem(vert_disp_parent)
    plot_item.setText(0, "    ├ Plot")
    plot_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_vertical_displacement_plot",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "result_type": "AllVerticalDisplacements"
    })

    # Table tab
    table_item = QTreeWidgetItem(vert_disp_parent)
    table_item.setText(0, "    └ Table")
    table_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "pushover_vertical_displacement_table",
        "result_set_id": result_set_id,
        "category": "Pushover",
        "result_type": "VerticalDisplacementsTable"
    })
