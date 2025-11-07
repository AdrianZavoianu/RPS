# Import Debug Logging - Missing Load Cases Issue

**Date**: 2024-11-07
**Issue**: "Only drifts have all imported cases, other result types are missing conflicted/bundled results"

---

## Problem

Conflict detection works correctly, but during import:
- ✅ **Drifts**: All load cases imported
- ❌ **Forces, Accelerations, Pier Forces, etc.**: Missing many load cases

**Root Cause**: Unknown - need to debug what's being allowed/skipped during import.

---

## Solution: Comprehensive Import Logging

Added detailed logging to track exactly what's happening during the import process.

### New Logging Features

#### 1. **Per-File Import Summary**
Shows which load cases are being imported from each file:

```
Importing 134Dix_Drifts_DES.xlsx...
  Importing 8 load case(s): TH01, TH02, TH03...
```

#### 2. **Skip Reasons**
Shows why load cases are being skipped:

```
  Importing 2 load case(s): TH05, TH09
  [Story Drifts] Skipped: TH01 (already imported), TH02 (already imported)...
  [Story Forces] Skipped: TH01 (using 134Dix_SS_DES.xlsx), TH05 (user skipped)
```

**Skip Reasons**:
- `(already imported)` - Load case already imported from another file for this sheet
- `(using OtherFile.xlsx)` - User chose a different file in conflict resolution
- `(user skipped)` - User clicked "Skip" in conflict dialog

#### 3. **Empty File Detection**
Shows when files have no allowed load cases:

```
Skipping 134Dix_11_drift.xlsx (no allowed load cases)
```

---

## What You'll See Now

### Example Log Output

```
- Processing 16 file(s)...

Importing 134Dix_Drifts_DES.xlsx... (0/16)
  Importing 8 load case(s): TH01, TH02, TH03...

Importing 134Dix_SS_DES.xlsx... (1/16)
  Importing 8 load case(s): TH01, TH02, TH03...

Importing 134Dix_DES_ss_05_09.xlsx... (2/16)
  Importing 2 load case(s): TH05, TH09
  [Story Forces] Skipped: TH01 (already imported), TH02 (already imported)...

Importing 134Dix_Acc_DES.xlsx... (3/16)
  Importing 8 load case(s): TH01, TH02, TH03...

Importing 134Dix_Piers_DES.xlsx... (4/16)
  Importing 8 load case(s): TH01, TH02, TH03...

Importing 134Dix_ALL_0509.xlsx... (5/16)
  Importing 2 load case(s): TH05, TH09
  [Pier Forces] Skipped: TH05 (using 134Dix_Piers_DES.xlsx)...
  [Diaphragm Accelerations] Skipped: TH09 (using 134Dix_Acc_DES.xlsx)
```

---

## Diagnosing the Issue

Based on the logs, you can identify:

### 1. **Correct Behavior**
```
Importing TH01 from 134Dix_Drifts_DES.xlsx
  [Story Drifts] Allowed: TH01
  [Story Forces] Allowed: TH01  ← Same load case, different sheets!
```
**Result**: TH01 imported for BOTH drifts and forces ✓

### 2. **Conflict Resolution Working**
```
Importing 134Dix_DES_ss_05_09.xlsx
  [Story Forces] Skipped: TH05 (using 134Dix_SS_DES.xlsx)
```
**Result**: User chose the other file for this conflict ✓

### 3. **Potential Bug**
```
Importing 134Dix_Drifts_DES.xlsx
  Importing 8 load case(s): TH01, TH02, TH03...

Importing 134Dix_SS_DES.xlsx
  Importing 0 load case(s):
  [Story Forces] Skipped: TH01 (already imported), TH02 (already imported)...
```
**Problem**: TH01-TH08 imported for Drifts, but NOT for Forces! ❌

---

## Files Modified

**File**: `src/processing/enhanced_folder_importer.py`

**Changes**:
1. **Lines 540-552**: Added logging for skipped files and import summary
2. **Lines 632-680**: Added detailed skip reason tracking in `_get_allowed_load_cases()`

---

## Next Steps

1. **Run the import** with your 134Dix files
2. **Share the complete log output** (all the "Importing..." messages)
3. **Look for patterns**:
   - Are some files showing "0 load case(s)"?
   - Are certain sheets being skipped when they shouldn't be?
   - Are "already imported" messages appearing when they shouldn't?

The logging will show us exactly where the logic is failing!

---

**Status**: Debug logging added, ready for testing ✓
