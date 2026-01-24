# Enhanced Conflict Detection Logging

**Date**: 2024-11-07
**Issue**: Conflicts only detected for drifts, accelerations, quad rotations - other result types missing

---

## Problem

User reported: "The conflicts pick up only drifts, accelerations and quad rotation nothing else and all result types should have conflicts based on current test files"

**Root Cause**: Errors during sheet parsing were being **silently swallowed** (`except Exception: continue`), so we couldn't see why other sheets were failing.

---

## Solution: Detailed Scan Logging

Added comprehensive logging to show **exactly** what's happening during file scanning:

### 1. Per-Sheet Success/Error Tracking

**Before**: Silent failures
```python
try:
    load_cases = parser.get_story_forces()
    if load_cases:
        load_cases_by_sheet[sheet_name] = load_cases
except Exception:
    continue  # Silent failure!
```

**After**: Logged errors
```python
sheets_found = []
sheets_errored = []

try:
    load_cases = parser.get_story_forces()
    if load_cases:
        load_cases_by_sheet[sheet_name] = load_cases
        sheets_found.append(f"{sheet_name}({len(load_cases)})")
except Exception as e:
    sheets_errored.append(f"{sheet_name}: {str(e)[:30]}")
    continue
```

### 2. Progress Logging

After scanning each file, you'll now see:

**Success**:
```
Scanning 134Dix_Drifts_DES.xlsx...
  ✓ Story Drifts(8), Story Forces(8), Pier Forces(8)...
```

**Errors**:
```
Scanning 134Dix_SS_DES.xlsx...
  ✓ Story Forces(8)
  ✗ Pier Forces: list index out of range
```

---

## What You'll See Now

### During File Scanning

```
- Scanning files for load cases...
  Scanning 134Dix_11_drift.xlsx (1/16)
  ✓ Story Drifts(8)

  Scanning 134Dix_Acc_DES.xlsx (2/16)
  ✓ Diaphragm Accelerations(8)

  Scanning 134Dix_DES_Drifts_05_09.xlsx (3/16)
  ✓ Story Drifts(8)

  Scanning 134Dix_Piers_DES.xlsx (4/16)
  ✓ Pier Forces(8)
  ✗ Story Forces: 'Story Forces' sheet not found

  Scanning 134Dix_SS_DES.xlsx (5/16)
  ✓ Story Forces(8)
  ✗ Pier Forces: list index out of range
```

This will tell you:
- ✅ Which sheets were successfully scanned
- ✅ How many load cases were found in each
- ❌ Which sheets failed and why

---

## Diagnosing the Issue

Based on the logs, you can determine:

### 1. **Sheet Not Found**
```
✗ Story Forces: 'Story Forces' sheet not found
```
**Solution**: File doesn't have that sheet - expected, no action needed.

### 2. **Parsing Errors**
```
✗ Pier Forces: list index out of range
```
**Solution**: Excel format issue - column missing or unexpected format.

### 3. **No Load Cases Found**
```
Scanning file.xlsx...
(no output)
```
**Solution**: File has no recognizable data or all sheets failed.

### 4. **Only Some Sheets Work**
```
✓ Story Drifts(8), Diaphragm Accelerations(8), Quad Strain Gauge - Rotation(8)
✗ Story Forces: KeyError: 'VX'
✗ Pier Forces: ValueError: invalid literal
```
**Solution**: Some sheets have correct format, others don't - Excel format mismatch.

---

## Expected vs Actual

### Expected (if all sheets parse correctly):
```
Scanning 134Dix_ALL_0509.xlsx...
  ✓ Story Drifts(8), Diaphragm Accelerations(8), Story Forces(8)...
  ✓ Pier Forces(8), Element Forces - Columns(8), Quad Strain Gauge - Rotation(8)
```

### Actual (if some fail):
```
Scanning 134Dix_ALL_0509.xlsx...
  ✓ Story Drifts(8), Diaphragm Accelerations(8), Quad Strain Gauge - Rotation(8)
  ✗ Story Forces: KeyError: 'VX'
  ✗ Pier Forces: IndexError: list index out of range
```

---

## Files Modified

**File**: `src/processing/enhanced_folder_importer.py`

**Changes**:
1. **Lines 120-160**: Added `sheets_found` and `sheets_errored` tracking to static method
2. **Lines 284-322**: Added same tracking to instance method
3. **Both methods**: Log successes with ✓ and errors with ✗

---

## Next Steps

1. **Run the import** on your 134Dix folder
2. **Check the log output** for error messages
3. **Identify which sheets are failing** and why
4. **Share the log output** so we can fix the Excel parsing for those sheets

The logging will tell us exactly which result types are failing to parse and what the errors are!

---

**Status**: Enhanced logging added, ready for testing ✓
