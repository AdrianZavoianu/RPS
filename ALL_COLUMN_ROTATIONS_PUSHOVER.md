# All Column Rotations Implementation for Pushover

## ✅ Implementation Complete

Added "All Rotations" view for pushover columns, matching NLTHA structure.

---

## Changes Made

### 1. Tree Structure (`src/gui/results_tree_browser.py`)

**Updated `_add_pushover_column_rotations_section()` (lines 2021-2092)**

Added "All Rotations" item as first child under Rotations:

```python
# Add "All Rotations" item as first item (before individual columns)
all_rotations_item = QTreeWidgetItem(rotations_parent)
all_rotations_item.setText(0, "    ├ All Rotations")
all_rotations_item.setData(0, Qt.ItemDataRole.UserRole, {
    "type": "pushover_all_column_rotations",
    "result_set_id": result_set_id,
    "category": "Pushover",
    "result_type": "ColumnRotations"
})
```

**Tree Structure:**
```
└── Columns
    ├── Shears
    │   └── ... (V2, V3 for each column)
    └── Rotations
        ├── All Rotations  ← NEW!
        ├── C1
        │   ├── R2
        │   └── R3
        └── ... (all columns)
```

### 2. Click Handler (`src/gui/results_tree_browser.py`)

**Added `pushover_all_column_rotations` handler (lines 1590-1597)**

```python
elif item_type == "pushover_all_column_rotations":
    # Emit for All Column Rotations view (scatter plot showing all columns)
    result_set_id = data.get("result_set_id")
    category = data.get("category")
    result_type = "AllColumnRotations"

    print(f"[DEBUG] Browser: pushover_all_column_rotations clicked - result_type={result_type}")
    self.selection_changed.emit(result_set_id, category, result_type, "", -1)  # -1 means all elements
```

### 3. Data Loading (`src/processing/result_service/service.py`)

**Updated `get_all_column_rotations_dataset()` (lines 322-349)**

Added logic to handle both NLTHA and Pushover data:

```python
# For pushover data, max_rotation and min_rotation are None, use rotation field
# For NLTHA envelope data, use max_rotation or min_rotation
if rotation.max_rotation is not None or rotation.min_rotation is not None:
    # NLTHA envelope data
    value = rotation.max_rotation if max_min == "Max" else rotation.min_rotation
else:
    # Pushover data (or NLTHA single case) - use rotation field
    # Only include in "Max" call to avoid duplicates
    if max_min != "Max":
        continue
    value = rotation.rotation
```

**Key Logic:**
- NLTHA data has `max_rotation` and `min_rotation` populated → use those
- Pushover data has only `rotation` field populated → use that
- Pushover data only returned on "Max" call (Min call returns empty DataFrame)

---

## Testing Results

### Data Loading Verification

**Test Script:** `test_pushover_all_rotations.py`

**Results for T1 Project (Pushover):**
```
Max dataset: 1,360 rows
  Unique elements: 72 columns
  Unique stories: 9
  Unique load cases: 4
  Unique directions: 2 (R2, R3)

Min dataset: EMPTY (as expected for pushover)
```

**Data Calculation:**
- 72 columns × 9 stories × 4 load cases × 2 directions = 5,184 potential data points
- Actual: 1,360 rows (some combinations filtered/missing)

---

## How It Works

### User Workflow:

1. Navigate to pushover result set in tree
2. Expand **Elements → Columns → Rotations**
3. Click **"All Rotations"**
4. View displays scatter plot with all column rotation data points

### Data Flow:

```
User clicks "All Rotations"
    ↓
Browser emits: result_type="AllColumnRotations", element_id=-1
    ↓
ProjectDetailWindow.on_selection_changed()
    ↓
load_all_column_rotations(result_set_id)
    ↓
ResultDataService.get_all_column_rotations_dataset(result_set_id, "Max")
    ↓
Queries ColumnRotation table
    ↓
For pushover: uses rotation field (not max_rotation/min_rotation)
    ↓
Returns DataFrame with columns: Element, Story, LoadCase, Direction, Rotation, StoryOrder
    ↓
AllRotationsWidget displays scatter plot
```

### View Display:

- **X-axis:** Column Rotation (%)
- **Y-axis:** Story Order
- **Points:** Each rotation value (colored by load case and direction)
- **Legend:** Shows load cases and R2/R3 directions

---

## Differences from NLTHA

| Aspect | NLTHA | Pushover |
|--------|-------|----------|
| Data Source | `max_rotation`, `min_rotation` | `rotation` |
| View Calls | Two datasets (Max + Min) | One dataset (Max only) |
| Plot | Max and Min overlaid | Single dataset |
| Legend | Shows Max/Min distinction | Shows load cases + directions |

---

## Files Modified

1. **`src/gui/results_tree_browser.py`**
   - Line 2050-2058: Added "All Rotations" tree item
   - Line 1590-1597: Added click handler

2. **`src/processing/result_service/service.py`**
   - Line 322-349: Updated data loading logic

---

## Database Structure

**ColumnRotation Table:**
```sql
rotation FLOAT NOT NULL          -- Pushover uses this
max_rotation FLOAT NULL           -- NLTHA envelope max
min_rotation FLOAT NULL           -- NLTHA envelope min
```

**For Pushover:**
- `rotation` is populated
- `max_rotation` and `min_rotation` are NULL

**For NLTHA:**
- `max_rotation` and `min_rotation` are populated
- `rotation` may also be populated for individual cases

---

## Testing Checklist

- [x] Tree item appears under Rotations
- [x] Click handler emits correct signal
- [x] Data loading returns pushover rotation values
- [x] Min call returns empty (no duplicates)
- [x] Max call returns all rotation data points
- [ ] View displays scatter plot correctly (test in app)
- [ ] Load case legend shows correct names
- [ ] Shorthand mapping applied (Px1, Py1, etc.)

---

## Next Steps (Optional)

1. **Test in Application:** Run the app and verify the scatter plot displays correctly
2. **Test Shorthand Mapping:** Verify load case names use shorthand (Px1, Py1, etc.)
3. **Test Multiple Projects:** Verify works for different pushover files
4. **Add Similar for Beams:** Consider adding "All Rotations" for beam section too

---

**Status:** ✅ **COMPLETE - Ready for Testing**

**Last Updated:** 2025-11-30
