# Per-Sheet Conflict Resolution Fix

**Date**: 2024-11-07
**Issue**: Load cases only imported for one result type, missing from others

---

## The Bug

When you chose a file for a conflicting load case (e.g., `134Dix_11_drift.xlsx` for TH11), the choice was being applied to **ALL result types**, not just the one you chose it for.

### Example

**Conflict detected**:
- TH11 in Story Drifts: `134Dix_11_drift.xlsx` vs `134Dix_Drifts_DES.xlsx`
- TH11 in Accelerations: `134Dix_11_acc.xlsx` vs `134Dix_Acc_DES.xlsx`
- TH11 in Pier Forces: `134Dix_11_piers.xlsx` vs `134Dix_Piers_DES.xlsx`

**User chose**: `134Dix_11_drift.xlsx` for Story Drifts

**WRONG behavior** (before fix):
```
Story Drifts: Import TH11 from 134Dix_11_drift.xlsx ✓
Accelerations: Skip TH11 (using 134Dix_11_drift.xlsx - but it has no accelerations!) ✗
Pier Forces: Skip TH11 (using 134Dix_11_drift.xlsx - but it has no piers!) ✗
```

**Result**: TH11 only imported for Drifts, missing from all other result types!

---

## Root Cause

### Before (Broken)

**Conflict Dialog** returned:
```python
{
    "TH11": "134Dix_11_drift.xlsx"  # Single choice for ALL sheets!
}
```

**Folder Import** transformed it:
```python
# Applied the SAME file to ALL sheets
{
    "Story Drifts": {"TH11": "134Dix_11_drift.xlsx"},
    "Diaphragm Accelerations": {"TH11": "134Dix_11_drift.xlsx"},  # WRONG!
    "Pier Forces": {"TH11": "134Dix_11_drift.xlsx"}  # WRONG!
}
```

### After (Fixed)

**Conflict Dialog** now returns **per-sheet** choices:
```python
{
    "Story Drifts": {"TH11": "134Dix_11_drift.xlsx"},
    "Diaphragm Accelerations": {"TH11": "134Dix_11_acc.xlsx"},
    "Pier Forces": {"TH11": "134Dix_11_piers.xlsx"}
}
```

Each result type gets the correct file!

---

## Changes Made

### 1. Conflict Dialog - Track Per-Sheet Resolutions

**File**: `src/gui/load_case_conflict_dialog.py`

**Before**:
```python
self.resolution = {}  # {load_case: file}

def _on_selection(self, load_case: str, file_name: Optional[str]):
    self.resolution[load_case] = file_name

def get_resolution(self) -> Dict[str, Optional[str]]:
    return self.resolution.copy()
```

**After**:
```python
self.resolution: Dict[str, Dict[str, Optional[str]]] = {}  # {sheet: {load_case: file}}

def _on_selection(self, sheet: str, load_case: str, file_name: Optional[str]):
    if sheet not in self.resolution:
        self.resolution[sheet] = {}
    self.resolution[sheet][load_case] = file_name

def get_resolution(self) -> Dict[str, Dict[str, Optional[str]]]:
    return {sheet: lc_dict.copy() for sheet, lc_dict in self.resolution.items()}
```

**Lines changed**: 49-61, 282-328, 381-394

---

### 2. Pass Sheet Context to Selection Handler

**File**: `src/gui/load_case_conflict_dialog.py`

**Before**:
```python
radio.toggled.connect(
    lambda checked, lc=load_case, f=file_name:
    self._on_selection(lc, f) if checked else None
)
```

**After**:
```python
radio.toggled.connect(
    lambda checked, s=sheet, lc=load_case, f=file_name:
    self._on_selection(s, lc, f) if checked else None
)
```

Now the dialog knows which sheet each selection is for!

---

### 3. Remove Incorrect Transformation

**File**: `src/gui/folder_import_dialog.py`

**Before** (lines 948-959):
```python
# Get resolution in format: {load_case: file_name}
lc_resolution = conflict_dialog.get_resolution()

# Transform to format expected by worker: {sheet: {load_case: file}}
sheet_resolution = {}
for lc, file_name in lc_resolution.items():
    if lc in conflicts:
        for sheet_name in conflicts[lc].keys():
            if sheet_name not in sheet_resolution:
                sheet_resolution[sheet_name] = {}
            sheet_resolution[sheet_name][lc] = file_name  # Applied to ALL sheets!
```

**After** (lines 948-950):
```python
# Get resolution in format: {sheet: {load_case: file_name}}
# Already in the correct format for the worker!
sheet_resolution = conflict_dialog.get_resolution()
```

No transformation needed - dialog returns the correct format!

---

## Test Results

### Before Fix

Log showed:
```
Importing 134Dix_11_drift.xlsx...
  Importing 1 load case(s): TH11

Importing 134Dix_11_acc.xlsx...
  [Diaphragm Accelerations] Skipped: TH11 (using 134Dix_11_drift.xlsx)
  Skipping (no allowed load cases)
```

**Result**: TH11 missing from Accelerations, Pier Forces, Displacements!

### After Fix

Expected log:
```
Importing 134Dix_11_drift.xlsx...
  Importing 1 load case(s): TH11

Importing 134Dix_11_acc.xlsx...
  Importing 1 load case(s): TH11  ← Now imports!

Importing 134Dix_11_piers.xlsx...
  Importing 1 load case(s): TH11  ← Now imports!
```

**Result**: TH11 imported for ALL result types ✓

---

## Files Modified

1. **src/gui/load_case_conflict_dialog.py** (3 changes)
   - Lines 49-61: Changed resolution storage to per-sheet
   - Lines 282-328: Updated radio button connections to pass sheet
   - Lines 381-394: Updated selection handler and getter

2. **src/gui/folder_import_dialog.py** (1 change)
   - Lines 948-954: Removed incorrect transformation

---

## Impact

This fix ensures that:
- ✅ Each result type can have different file choices for the same load case
- ✅ All result types get their data imported correctly
- ✅ No more missing load cases in Forces, Accelerations, Piers, etc.

---

**Status**: Critical bug fixed ✓
**Testing**: Please re-run import and verify all result types now have all load cases
