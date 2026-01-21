"""NLTHA section builders for the results tree browser.

This module contains functions to build tree sections for NLTHA
(Non-Linear Time History Analysis) results.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QTreeWidgetItem

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from gui.tree_browser import ResultsTreeBrowser


def add_result_set(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set, expand_first_path: bool = True) -> None:
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
    result_set_item.setExpanded(expand_first_path)

    # Envelopes category
    envelopes_item = QTreeWidgetItem(result_set_item)
    envelopes_item.setText(0, "◆ Envelopes")
    envelopes_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "category",
        "result_set_id": result_set.id,
        "category": "Envelopes"
    })
    envelopes_item.setExpanded(expand_first_path)

    # Global Results
    global_item = QTreeWidgetItem(envelopes_item)
    global_item.setText(0, "◇ Global")
    global_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "category_type",
        "result_set_id": result_set.id,
        "category": "Envelopes",
        "category_type": "Global"
    })
    global_item.setExpanded(expand_first_path)

    # Result types under Global (only show if data exists)
    # Track if we've expanded the first result type
    first_result_type_expanded = False
    
    if browser._has_data_for(result_set.id, "Drifts"):
        add_drifts_section(browser, global_item, result_set.id, expand_first_path)
        first_result_type_expanded = True

    if browser._has_data_for(result_set.id, "Accelerations"):
        add_result_type_with_directions(
            browser, global_item, "> Story Accelerations", result_set.id,
            "Envelopes", "Accelerations", include_maxmin=True, maxmin_label="Accelerations",
            expand_first_path=expand_first_path and not first_result_type_expanded
        )
        if expand_first_path and not first_result_type_expanded:
            first_result_type_expanded = True
    if browser._has_data_for(result_set.id, "Forces"):
        add_result_type_with_directions(
            browser, global_item, "> Story Forces", result_set.id,
            "Envelopes", "Forces", include_maxmin=True, maxmin_label="Story Forces",
            expand_first_path=False
        )
    if browser._has_data_for(result_set.id, "Displacements"):
        add_result_type_with_directions(
            browser, global_item, "> Floors Displacements", result_set.id,
            "Envelopes", "Displacements", include_maxmin=True, maxmin_label="Floors Displacements",
            expand_first_path=False
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

    add_walls_section(browser, elements_item, result_set.id)
    add_columns_section(browser, elements_item, result_set.id)
    add_beams_section(browser, elements_item, result_set.id)

    if elements_item.childCount() == 0:
        envelopes_item.removeChild(elements_item)

    # Joints category
    joints_item = QTreeWidgetItem(envelopes_item)
    joints_item.setText(0, "◇ Joints")
    joints_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "category_type",
        "result_set_id": result_set.id,
        "category": "Envelopes",
        "category_type": "Joints"
    })
    joints_item.setExpanded(True)

    add_soil_pressures_section(browser, joints_item, result_set.id)
    add_vertical_displacements_section(browser, joints_item, result_set.id)

    if joints_item.childCount() == 0:
        envelopes_item.removeChild(joints_item)

    # Time-Series category (only show if data exists)
    if browser._has_time_series_data(result_set.id):
        timeseries_item = QTreeWidgetItem(result_set_item)
        timeseries_item.setText(0, "◆ Time-Series")
        timeseries_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category",
            "result_set_id": result_set.id,
            "category": "Time-Series"
        })
        timeseries_item.setExpanded(False)

        # Add Time-Series Global section
        add_time_series_global_section(browser, timeseries_item, result_set.id)


def add_drifts_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int, expand_first_path: bool = True) -> None:
    """Add Drifts section with directions and Max/Min subsection."""
    drifts_parent = QTreeWidgetItem(parent_item)
    drifts_parent.setText(0, "› Drifts")
    drifts_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "result_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "Drifts"
    })
    drifts_parent.setExpanded(expand_first_path)

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


def add_result_type_with_directions(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    label: str,
    result_set_id: int,
    category: str,
    result_type: str,
    include_maxmin: bool = False,
    maxmin_label: str = None,
    expand_first_path: bool = False,
) -> None:
    """Add a result type with X/Y directions and optional Max/Min."""
    result_type_parent = QTreeWidgetItem(parent_item)
    result_type_parent.setText(0, label)
    result_type_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "result_type_parent",
        "result_set_id": result_set_id,
        "category": category,
        "result_type": result_type
    })
    result_type_parent.setExpanded(expand_first_path)

    # X Direction
    x_item = QTreeWidgetItem(result_type_parent)
    x_item.setText(0, "  ├ X Direction")
    x_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "result_type",
        "result_set_id": result_set_id,
        "category": category,
        "result_type": result_type,
        "direction": "X"
    })

    # Y Direction
    y_item = QTreeWidgetItem(result_type_parent)
    if include_maxmin:
        y_item.setText(0, "  ├ Y Direction")
    else:
        y_item.setText(0, "  └ Y Direction")
    y_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "result_type",
        "result_set_id": result_set_id,
        "category": category,
        "result_type": result_type,
        "direction": "Y"
    })

    # Max/Min subsection (optional)
    if include_maxmin:
        label_text = maxmin_label or result_type
        maxmin_item = QTreeWidgetItem(result_type_parent)
        maxmin_item.setText(0, f"  └ Max/Min {label_text}")
        maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "maxmin_results",
            "result_set_id": result_set_id,
            "category": category,
            "result_type": f"MaxMin{result_type}"
        })


def add_walls_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Walls section with Shears and Quad Rotations subcategories."""
    has_shears = browser._has_data_for(result_set_id, "WallShears")
    has_quad_rotations = browser._has_data_for(result_set_id, "QuadRotations")

    if not has_shears and not has_quad_rotations:
        return

    walls_parent = QTreeWidgetItem(parent_item)
    walls_parent.setText(0, "› Walls")
    walls_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "element_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "element_type": "Walls"
    })
    walls_parent.setExpanded(False)

    wall_elements = [elem for elem in browser.elements if elem.element_type == "Wall"]
    quad_elements = [elem for elem in browser.elements if elem.element_type == "Quad"]

    if has_shears:
        add_shears_section(browser, walls_parent, result_set_id, wall_elements)

    if has_quad_rotations:
        add_quad_rotations_section(browser, walls_parent, result_set_id, quad_elements)


def add_shears_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    wall_elements: List,
) -> None:
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

        # Max/Min
        maxmin_item = QTreeWidgetItem(pier_item)
        maxmin_item.setText(0, "      └ Max/Min")
        maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "maxmin_results",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MaxMinWallShears",
            "element_id": element.id
        })


def add_quad_rotations_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    quad_elements: List,
) -> None:
    """Add Quad Rotations subsection under Walls."""
    rotations_parent = QTreeWidgetItem(parent_item)
    rotations_parent.setText(0, "  › Quad Rotations")
    rotations_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "wall_result_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "QuadRotations"
    })
    rotations_parent.setExpanded(True)

    # Add "All" section for scatter plot of all rotations
    all_item = QTreeWidgetItem(rotations_parent)
    all_item.setText(0, "    › All Rotations")
    all_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "all_rotations",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "AllQuadRotations",
        "element_id": -1
    })

    if not quad_elements:
        placeholder = QTreeWidgetItem(rotations_parent)
        placeholder.setText(0, "    └ No quads found")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        return

    for element in quad_elements:
        elem_item = QTreeWidgetItem(rotations_parent)
        elem_item.setText(0, f"    › {element.name}")
        elem_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "element_id": element.id,
            "element_name": element.name
        })
        elem_item.setExpanded(True)

        # Rotation direction
        rotation_item = QTreeWidgetItem(elem_item)
        rotation_item.setText(0, "      ├ Rotation")
        rotation_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "QuadRotations",
            "direction": "Rotation",
            "element_id": element.id
        })

        # Max/Min
        maxmin_item = QTreeWidgetItem(elem_item)
        maxmin_item.setText(0, "      └ Max/Min")
        maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "maxmin_results",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MaxMinQuadRotations",
            "element_id": element.id
        })


def add_columns_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Columns section with Shears, Axials, and Rotations subcategories."""
    has_shears = browser._has_data_for(result_set_id, "ColumnShears")
    has_axials = browser._has_data_for(result_set_id, "ColumnAxials")
    has_rotations = browser._has_data_for(result_set_id, "ColumnRotations")

    if not has_shears and not has_axials and not has_rotations:
        return

    columns_parent = QTreeWidgetItem(parent_item)
    columns_parent.setText(0, "› Columns")
    columns_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "element_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "element_type": "Columns"
    })
    columns_parent.setExpanded(False)

    column_elements = [elem for elem in browser.elements if elem.element_type == "Column"]

    if has_shears:
        add_column_shears_section(browser, columns_parent, result_set_id, column_elements)

    if has_axials:
        add_column_axials_section(browser, columns_parent, result_set_id, column_elements)

    if has_rotations:
        add_column_rotations_section(browser, columns_parent, result_set_id, column_elements)


def add_column_shears_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    column_elements: List,
) -> None:
    """Add Column Shears subsection."""
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

    for element in column_elements:
        col_item = QTreeWidgetItem(shears_parent)
        col_item.setText(0, f"    › {element.name}")
        col_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "element_id": element.id,
            "element_name": element.name
        })
        col_item.setExpanded(True)

        # V2 Direction
        v2_item = QTreeWidgetItem(col_item)
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
        v3_item = QTreeWidgetItem(col_item)
        v3_item.setText(0, "      ├ V3")
        v3_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnShears",
            "direction": "V3",
            "element_id": element.id
        })

        # Max/Min
        maxmin_item = QTreeWidgetItem(col_item)
        maxmin_item.setText(0, "      └ Max/Min")
        maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "maxmin_results",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MaxMinColumnShears",
            "element_id": element.id
        })


def add_column_axials_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    column_elements: List,
) -> None:
    """Add Column Axials subsection with Min/Max/MinMax views."""
    axials_parent = QTreeWidgetItem(parent_item)
    axials_parent.setText(0, "  › Axials")
    axials_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "column_result_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "ColumnAxials"
    })
    axials_parent.setExpanded(True)

    if not column_elements:
        placeholder = QTreeWidgetItem(axials_parent)
        placeholder.setText(0, "    └ No columns found")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        return

    for element in column_elements:
        col_item = QTreeWidgetItem(axials_parent)
        col_item.setText(0, f"    › {element.name}")
        col_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "element_id": element.id,
            "element_name": element.name
        })
        col_item.setExpanded(True)

        # Min Axial (compression)
        min_item = QTreeWidgetItem(col_item)
        min_item.setText(0, "      ├ Min")
        min_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnAxials",
            "direction": "Min",
            "element_id": element.id
        })

        # Max Axial (tension)
        max_item = QTreeWidgetItem(col_item)
        max_item.setText(0, "      ├ Max")
        max_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnAxials",
            "direction": "Max",
            "element_id": element.id
        })

        # Max/Min envelope view
        maxmin_item = QTreeWidgetItem(col_item)
        maxmin_item.setText(0, "      └ Max/Min")
        maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "maxmin_results",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MaxMinColumnAxials",
            "element_id": element.id
        })


def add_column_rotations_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    column_elements: List,
) -> None:
    """Add Column Rotations subsection."""
    rotations_parent = QTreeWidgetItem(parent_item)
    rotations_parent.setText(0, "  › Rotations")
    rotations_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "column_result_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "ColumnRotations"
    })
    rotations_parent.setExpanded(True)

    # Add "All" section
    all_item = QTreeWidgetItem(rotations_parent)
    all_item.setText(0, "    › All Rotations")
    all_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "all_column_rotations",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "AllColumnRotations",
        "element_id": -1
    })

    if not column_elements:
        placeholder = QTreeWidgetItem(rotations_parent)
        placeholder.setText(0, "    └ No columns found")
        placeholder.setFlags(Qt.ItemFlag.NoItemFlags)
        return

    for element in column_elements:
        col_item = QTreeWidgetItem(rotations_parent)
        col_item.setText(0, f"    › {element.name}")
        col_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "element_parent",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "element_id": element.id,
            "element_name": element.name
        })
        col_item.setExpanded(True)

        # R2 Rotation
        r2_item = QTreeWidgetItem(col_item)
        r2_item.setText(0, "      ├ R2")
        r2_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnRotations",
            "direction": "R2",
            "element_id": element.id
        })

        # R3 Rotation
        r3_item = QTreeWidgetItem(col_item)
        r3_item.setText(0, "      ├ R3")
        r3_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "result_type",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "ColumnRotations",
            "direction": "R3",
            "element_id": element.id
        })

        # Max/Min
        maxmin_item = QTreeWidgetItem(col_item)
        maxmin_item.setText(0, "      └ Max/Min")
        maxmin_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "maxmin_results",
            "result_set_id": result_set_id,
            "category": "Envelopes",
            "result_type": "MaxMinColumnRotations",
            "element_id": element.id
        })


def add_beams_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Beams section with Rotations subcategory."""
    has_rotations = browser._has_data_for(result_set_id, "BeamRotations")

    if not has_rotations:
        return

    beams_parent = QTreeWidgetItem(parent_item)
    beams_parent.setText(0, "› Beams")
    beams_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "element_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "element_type": "Beams"
    })
    beams_parent.setExpanded(False)

    beam_elements = [elem for elem in browser.elements if elem.element_type == "Beam"]

    add_beam_rotations_section(browser, beams_parent, result_set_id, beam_elements)


def add_beam_rotations_section(
    browser: "ResultsTreeBrowser",
    parent_item: QTreeWidgetItem,
    result_set_id: int,
    beam_elements: List,
) -> None:
    """Add Beam Rotations subsection with Plot and Table views (like Soil Pressures)."""
    rotations_parent = QTreeWidgetItem(parent_item)
    rotations_parent.setText(0, "  › R3 Plastic Rotations")
    rotations_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "beam_result_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "BeamRotations"
    })
    rotations_parent.setExpanded(False)

    # Plot view
    plot_item = QTreeWidgetItem(rotations_parent)
    plot_item.setText(0, "    ├ Plot")
    plot_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "beam_rotations_plot",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "AllBeamRotations",
        "element_id": -1
    })

    # Table view
    table_item = QTreeWidgetItem(rotations_parent)
    table_item.setText(0, "    └ Table")
    table_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "beam_rotations_table",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "BeamRotationsTable",
        "element_id": -1
    })


def add_soil_pressures_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Soil Pressures section with plot and table views."""
    # Check for SoilPressures_Min (the actual cached type)
    if not browser._has_data_for(result_set_id, "SoilPressures_Min"):
        return

    soil_pressures_parent = QTreeWidgetItem(parent_item)
    soil_pressures_parent.setText(0, "› Soil Pressures (Min)")
    soil_pressures_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "joint_result_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "SoilPressures"
    })
    soil_pressures_parent.setExpanded(False)

    # Plot view
    plot_item = QTreeWidgetItem(soil_pressures_parent)
    plot_item.setText(0, "  ├ Plot")
    plot_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "soil_pressure_plot",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "AllSoilPressures"
    })

    # Table view
    table_item = QTreeWidgetItem(soil_pressures_parent)
    table_item.setText(0, "  └ Table")
    table_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "soil_pressure_table",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "SoilPressuresTable"
    })


def add_vertical_displacements_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Vertical Displacements section with plot and table views."""
    # Check for VerticalDisplacements_Min (the actual cached type)
    if not browser._has_data_for(result_set_id, "VerticalDisplacements_Min"):
        return

    vert_disp_parent = QTreeWidgetItem(parent_item)
    vert_disp_parent.setText(0, "› Vertical Displacements (Min)")
    vert_disp_parent.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "joint_result_type_parent",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "VerticalDisplacements"
    })
    vert_disp_parent.setExpanded(False)

    # Plot view
    plot_item = QTreeWidgetItem(vert_disp_parent)
    plot_item.setText(0, "  ├ Plot")
    plot_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "vertical_displacement_plot",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "AllVerticalDisplacements"
    })

    # Table view
    table_item = QTreeWidgetItem(vert_disp_parent)
    table_item.setText(0, "  └ Table")
    table_item.setData(0, Qt.ItemDataRole.UserRole, {
        "type": "vertical_displacement_table",
        "result_set_id": result_set_id,
        "category": "Envelopes",
        "result_type": "VerticalDisplacementsTable"
    })


def add_time_series_global_section(browser: "ResultsTreeBrowser", parent_item: QTreeWidgetItem, result_set_id: int) -> None:
    """Add Time Series section with load cases as subsections.

    Structure:
    └── Time-Series
        └── TH02 (load case name)
            └── Global
                ├── X Direction (animated: Displacements, Drifts, Accelerations, Shears)
                └── Y Direction (animated: Displacements, Drifts, Accelerations, Shears)
    """
    # Get available load cases for this result set
    time_series_load_cases = browser.time_series_load_cases.get(result_set_id, [])

    if not time_series_load_cases:
        return

    for load_case_name in time_series_load_cases:
        # Load case item
        load_case_item = QTreeWidgetItem(parent_item)
        load_case_item.setText(0, f"› {load_case_name}")
        load_case_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "time_series_load_case",
            "result_set_id": result_set_id,
            "category": "Time-Series",
            "load_case_name": load_case_name
        })
        load_case_item.setExpanded(True)

        # Global Results section under load case
        global_item = QTreeWidgetItem(load_case_item)
        global_item.setText(0, "◇ Global")
        global_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "category_type",
            "result_set_id": result_set_id,
            "category": "Time-Series",
            "category_type": "Global",
            "load_case_name": load_case_name
        })
        global_item.setExpanded(True)

        # X Direction
        x_item = QTreeWidgetItem(global_item)
        x_item.setText(0, "  ├ X Direction")
        x_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "time_series_global",
            "result_set_id": result_set_id,
            "category": "Time-Series",
            "load_case_name": load_case_name,
            "direction": "X"
        })

        # Y Direction
        y_item = QTreeWidgetItem(global_item)
        y_item.setText(0, "  └ Y Direction")
        y_item.setData(0, Qt.ItemDataRole.UserRole, {
            "type": "time_series_global",
            "result_set_id": result_set_id,
            "category": "Time-Series",
            "load_case_name": load_case_name,
            "direction": "Y"
        })
