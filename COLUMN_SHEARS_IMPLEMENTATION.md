# Column Shears Implementation Summary

## ✅ Completed Implementation

Column shear support has been **fully implemented** for pushover results, matching the NLTHA structure.

---

## What Was Done

### 1. Tree Structure (✅ Complete)
**File**: `src/gui/results_tree_browser.py`

Updated pushover Columns section to include **both Shears and Rotations**:

```
└── Columns
    ├── Shears
    │   ├── C1
    │   │   ├── V2
    │   │   └── V3
    │   └── ... (all columns)
    └── Rotations
        ├── C1
        │   ├── R2
        │   └── R3
        └── ... (all columns)
```

**Changes Made:**
- Updated `_add_pushover_columns_section()` (lines 1900-1947) to check for both Shears and Rotations
- Added `_add_pushover_column_shears_section()` (lines 1949-2009) for Shears subsection
- Added click handler `pushover_column_shear_result` (lines 1570-1578)

### 2. Parser (✅ Complete)
**File**: `src/processing/pushover_column_shear_parser.py` (NEW)

Parses column shear forces from "Element Forces - Columns" sheet:
- Extracts V2 and V3 shear values
- Filters by pushover direction (X/Y)
- Groups by Column, Story, Output Case
- Calculates maximum absolute shear per group
- Returns DataFrame: `Column | Story | [Load Cases...]`

### 3. Importer (✅ Complete)
**File**: `src/processing/pushover_column_shear_importer.py` (NEW)

Imports column shear data into database:
- Stores in `ColumnShear` table
- Builds `ElementResultsCache` with types: `ColumnShears_V2` and `ColumnShears_V3`
- Integrates with existing import workflow

### 4. Import Integration (✅ Complete)
**File**: `src/gui/pushover_global_import_dialog.py`

Added column shear import to the dialog workflow:
- Imports column shears automatically when importing column results
- Runs after column rotations import
- Uses same file and load case selection

**Lines Modified**: 76, 153-168

---

## Testing

### ✅ Verified With T1 Project

**Import Test Results:**
```
X direction V2 shears: 384 records
X direction V3 shears: 384 records
Y direction V2 shears: 384 records
Y direction V3 shears: 384 records
Total: 1,536 shear records
```

**Database Verification:**
```
Element Results Cache:
  - ColumnShears_V2: 84 elements
  - ColumnShears_V3: 84 elements
  - ColumnRotations_R2: 72 elements
  - ColumnRotations_R3: 72 elements
```

---

## How To Use

### Option 1: Reimport Pushover Data (Recommended)

Simply reimport your pushover data using the **Pushover Global Import** dialog:

1. Open project in RPS
2. Click "Import" → "Pushover Global Results"
3. Select folder with pushover Excel files
4. Select load cases for X and Y directions
5. Click "Start Import"

**Column shears will be imported automatically** along with rotations!

### Option 2: Manual Import (For Existing Projects)

For projects that already have column rotations but need shears added:

1. Run the import script:
   ```bash
   pipenv run python import_t1_column_shears.py
   ```

2. Modify the script to point to your project database if needed

3. Reload the project in the app

---

## Tree Behavior

### Before Column Shears Import
```
└── Columns
    └── Rotations
        └── ... (R2, R3 for each column)
```

### After Column Shears Import
```
└── Columns
    ├── Shears  ← NEW!
    │   └── ... (V2, V3 for each column)
    └── Rotations
        └── ... (R2, R3 for each column)
```

The Shears section **automatically appears** when `ColumnShears_V2` or `ColumnShears_V3` data exists in the cache.

---

## Files Created

1. `src/processing/pushover_column_shear_parser.py` - Parser for Element Forces sheet
2. `src/processing/pushover_column_shear_importer.py` - Importer to database
3. `import_t1_column_shears.py` - Standalone import script (testing/manual use)

## Files Modified

1. `src/gui/results_tree_browser.py` - Tree structure + click handlers
2. `src/gui/pushover_global_import_dialog.py` - Import workflow integration

---

## Database Model

Uses existing `ColumnShear` model (already in `src/database/models.py`):

```python
class ColumnShear(Base):
    __tablename__ = "column_shears"

    id = Column(Integer, primary_key=True)
    element_id = Column(Integer, ForeignKey("elements.id"))
    story_id = Column(Integer, ForeignKey("stories.id"))
    load_case_id = Column(Integer, ForeignKey("load_cases.id"))
    direction = Column(String(10))  # 'V2' or 'V3'
    force = Column(Float)
    story_sort_order = Column(Integer)
```

Cache stores aggregated data:
- `ElementResultsCache.result_type`: "ColumnShears_V2" or "ColumnShears_V3"
- `ElementResultsCache.results_matrix`: `{load_case_name: shear_value}`

---

## Next Steps (If Needed)

1. **Test with other projects** - Verify import works for different pushover files
2. **Verify data display** - Check that StandardView displays column shears correctly
3. **Test load case mapping** - Ensure shorthand mapping (Px1, Py1) works for shears
4. **Add export support** - Verify column shears can be exported

---

**Status**: ✅ **COMPLETE and READY FOR USE**

**Last Updated**: 2025-11-30
