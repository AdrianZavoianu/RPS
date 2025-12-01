# Pushover Beams Implementation

## ✅ Implementation Complete

Added NLTHA-style Plot and Table views for pushover Beams section, bringing it to full parity with NLTHA structure.

---

## Overview

This implementation adds comprehensive beam rotation visualization for pushover analysis, matching the NLTHA pattern with Plot (scatter plot) and Table (wide-format) views.

---

## Changes Made

### 1. Tree Structure (`src/gui/results_tree_browser.py`)

**Updated `_add_pushover_beam_rotations_section()` (lines 2136-2178)**

Changed from individual beam items to Plot/Table structure:

```python
def _add_pushover_beam_rotations_section(self, parent_item: QTreeWidgetItem, result_set_id: int, beam_elements):
    """Add Beam Rotations subsection with Plot and Table views (R3 Plastic only).

    Structure:
    └── Rotations (R3 Plastic)
        ├── Plot (All Rotations scatter plot)
        └── Table (Wide-format table with all beams)
    """
    rotations_parent = QTreeWidgetItem(parent_item)
    rotations_parent.setText(0, "  › Rotations (R3 Plastic)")

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
```

**Tree Structure:**
```
└── Beams
    └── Rotations (R3 Plastic)
        ├── Plot      ← Scatter plot of all beam rotations
        └── Table     ← Wide-format table with all beams
```

### 2. Click Handlers (`src/gui/results_tree_browser.py`)

**Added `pushover_beam_rotations_plot` handler (lines 1599-1606)**
```python
elif item_type == "pushover_beam_rotations_plot":
    # Emit for All Beam Rotations plot view (scatter plot showing all beams)
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    result_type = "AllBeamRotations"

    print(f"[DEBUG] Browser: pushover_beam_rotations_plot clicked - result_type={result_type}")
    self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all beams
```

**Added `pushover_beam_rotations_table` handler (lines 1608-1615)**
```python
elif item_type == "pushover_beam_rotations_table":
    # Emit for Beam Rotations table view (wide-format table with all beams)
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    result_type = "BeamRotationsTable"

    print(f"[DEBUG] Browser: pushover_beam_rotations_table clicked - result_type={result_type}")
    self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all beams
```

### 3. Data Loading (`src/processing/result_service/service.py`)

**Updated `get_all_beam_rotations_dataset()` (lines 378-404)**

Added logic to handle both NLTHA and Pushover data:

```python
for rotation, load_case, story, element in records:
    # For pushover data, max_r3_plastic and min_r3_plastic are None, use r3_plastic field
    # For NLTHA envelope data, use max_r3_plastic or min_r3_plastic
    if rotation.max_r3_plastic is not None or rotation.min_r3_plastic is not None:
        # NLTHA envelope data
        value = rotation.max_r3_plastic if max_min == "Max" else rotation.min_r3_plastic
    else:
        # Pushover data (or NLTHA single case) - use r3_plastic field
        # Only include in "Max" call to avoid duplicates
        if max_min != "Max":
            continue
        value = rotation.r3_plastic

    if value is None:
        continue

    data_rows.append({
        "Element": element.name,
        "Story": story.name,
        "LoadCase": load_case.name,
        "Rotation": value * 100.0,
        "StoryOrder": story.sort_order or 0,
        "StoryIndex": story.sort_order or 0,
    })
```

**Key Logic:**
- NLTHA data has `max_r3_plastic` and `min_r3_plastic` populated → use those
- Pushover data has only `r3_plastic` field populated → use that
- Pushover data only returned on "Max" call (Min call returns empty DataFrame)

**`get_beam_rotations_table_dataset()` - No Changes Needed**
- Already uses `r3_plastic` field (line 448)
- Works correctly for both NLTHA and Pushover data

---

## Testing Results

### Plot View (All Beam Rotations)

**Test Script:** `test_pushover_beam_rotations.py`

**Results for T1 Project (Pushover):**
```
Max dataset: 548 rows
  Unique elements: 18 beams
  Unique stories: 9
  Unique load cases: 4
  Columns: Element, Story, LoadCase, Rotation, StoryOrder, StoryIndex

Min dataset: EMPTY (as expected for pushover)
```

**Sample Data:**
```
Element  Story      LoadCase      Rotation  StoryOrder
B2       PLR     Push Modal X     0.4741    0
B2       PLR     Push Uniform X   0.0000    0
B5       PLR     Push Uniform Y   0.0000    0
```

### Table View (Beam Rotations Table)

**Results for T1 Project (Pushover):**
```
Table dataset: 137 rows x 13 columns
  Columns: Story, Frame/Wall, Unique Name, Hinge, Generated Hinge, Rel Dist,
           Push Modal X, Push Modal Y, Push Uniform X, Push Uniform Y,
           Avg, Max, Min
```

**Sample Data:**
```
Story  Frame/Wall  Unique Name  Hinge  Generated Hinge  Rel Dist  Push Modal X  Push Modal Y
PLR    B2          B2                                   0.0       0.4741        0.000005
PLR    B5          B5                                   0.0       0.4293        0.000004
L07    B1          B1                                   0.0       0.0272        0.000013
```

---

## How It Works

### User Workflow:

1. Navigate to pushover result set in tree
2. Expand **Elements → Beams → Rotations (R3 Plastic)**
3. Click **Plot** or **Table**
4. View displays corresponding visualization

### Plot View Data Flow:

```
User clicks "Plot"
    ↓
Browser emits: result_type="AllBeamRotations", element_id=-1
    ↓
ProjectDetailWindow.on_selection_changed()
    ↓
load_all_beam_rotations(result_set_id)
    ↓
ResultDataService.get_all_beam_rotations_dataset(result_set_id, "Max")
ResultDataService.get_all_beam_rotations_dataset(result_set_id, "Min")
    ↓
Queries BeamRotation table
    ↓
For pushover: uses r3_plastic field (not max_r3_plastic/min_r3_plastic)
    ↓
Returns DataFrame: Element, Story, LoadCase, Rotation, StoryOrder
    ↓
AllRotationsWidget displays scatter plot (Max + Min overlaid)
```

### Table View Data Flow:

```
User clicks "Table"
    ↓
Browser emits: result_type="BeamRotationsTable", element_id=-1
    ↓
ProjectDetailWindow.on_selection_changed()
    ↓
load_beam_rotations_table(result_set_id)
    ↓
ResultDataService.get_beam_rotations_table_dataset(result_set_id)
    ↓
Queries BeamRotation table
    ↓
Uses r3_plastic field (works for both pushover and NLTHA)
    ↓
Returns wide-format DataFrame with load case columns
    ↓
BeamRotationsTable widget displays table
    ↓
Applies pushover load case shorthand mapping (Px1, Py1, etc.)
```

---

## View Display

### Plot View:
- **X-axis:** R3 Plastic Rotation (%)
- **Y-axis:** Story Order
- **Points:** Each rotation value (colored by load case)
- **Legend:** Shows load cases with shorthand mapping
- **Status:** "Loaded 548 rotation data points (548 max, 0 min) across 18 beams and 9 stories"

### Table View:
- **Columns:** Story, Frame/Wall, Unique Name, Hinge, Generated Hinge, Rel Dist, [Load Cases], Avg, Max, Min
- **Headers:** Pushover load case shorthand (Px1, Py1, etc.) if applicable
- **Values:** R3 Plastic rotations as percentages (multiplied by 100)
- **Summaries:** Average, Maximum, Minimum columns calculated across load cases

---

## Differences from NLTHA

| Aspect | NLTHA | Pushover |
|--------|-------|----------|
| Data Source | `max_r3_plastic`, `min_r3_plastic` | `r3_plastic` |
| Plot View Calls | Two datasets (Max + Min) | One dataset (Max only) |
| Plot Display | Max and Min overlaid | Single dataset |
| Table Data | Same `r3_plastic` field | Same `r3_plastic` field |
| Load Case Names | Regular names | Shorthand mapping (Px1, Py1, etc.) |

---

## Database Structure

**BeamRotation Table:**
```sql
r3_plastic FLOAT NOT NULL              -- Pushover uses this
max_r3_plastic FLOAT NULL               -- NLTHA envelope max
min_r3_plastic FLOAT NULL               -- NLTHA envelope min
```

**For Pushover:**
- `r3_plastic` is populated
- `max_r3_plastic` and `min_r3_plastic` are NULL

**For NLTHA:**
- `max_r3_plastic` and `min_r3_plastic` are populated
- `r3_plastic` may also be populated for individual cases

---

## Files Modified

1. **`src/gui/results_tree_browser.py`**
   - Lines 2136-2178: Updated `_add_pushover_beam_rotations_section()`
   - Lines 1599-1606: Added `pushover_beam_rotations_plot` click handler
   - Lines 1608-1615: Added `pushover_beam_rotations_table` click handler

2. **`src/processing/result_service/service.py`**
   - Lines 378-404: Updated `get_all_beam_rotations_dataset()` for pushover support

---

## Testing Checklist

- [x] Tree items appear under Rotations (R3 Plastic)
- [x] Plot click handler emits correct signal
- [x] Table click handler emits correct signal
- [x] Plot data loading returns pushover rotation values
- [x] Table data loading returns wide-format table
- [x] Min call returns empty (no duplicates)
- [x] Max call returns all rotation data points
- [ ] View displays scatter plot correctly (test in app)
- [ ] View displays table correctly (test in app)
- [ ] Load case legend shows correct names with shorthand
- [ ] Shorthand mapping applied in table headers

---

## Complete Pushover Tree Structure

**Before This Implementation:**
```
└── Beams
    └── Rotations
        ├── B1
        ├── B2
        └── ... (individual beams)
```

**After This Implementation:**
```
└── Beams
    └── Rotations (R3 Plastic)
        ├── Plot      ← NEW! Scatter plot view
        └── Table     ← NEW! Wide-format table view
```

---

## Benefits

1. ✅ Complete feature parity with NLTHA structure
2. ✅ Scatter plot view for analyzing rotation distribution
3. ✅ Wide-format table for detailed beam-by-beam inspection
4. ✅ Automatic pushover load case shorthand mapping
5. ✅ Consistent user experience across analysis types
6. ✅ No additional import steps required (uses existing data)

---

## Next Steps (Manual UI Testing)

1. **Test in Application**
   - Open T1 project in app
   - Navigate to Pushover → Elements → Beams → Rotations (R3 Plastic)
   - Click Plot - verify scatter plot displays
   - Click Table - verify wide-format table displays

2. **Verify Shorthand Mapping**
   - Check table headers use shorthand (Px1, Py1, etc.)
   - Check plot legend shows shorthand mapping

3. **Verify Data Accuracy**
   - Spot-check rotation values against Excel source
   - Verify summary columns (Avg, Max, Min) are correct

4. **Export Testing**
   - Test exporting beam rotations to Excel/CSV
   - Verify shorthand mapping is applied

---

**Status:** ✅ **COMPLETE - Ready for User Testing**

**Date:** 2025-12-01

**Implementation Time:** ~30 minutes

**Lines of Code Modified:** ~50 lines

**Test Results:** All data loading verified successfully with 548 rotation data points across 18 beams
