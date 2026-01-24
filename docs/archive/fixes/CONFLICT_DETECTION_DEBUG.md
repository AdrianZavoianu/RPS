# Conflict Detection Debugging

**Date**: 2024-11-07
**Issue**: Not all duplications are being detected for 135Dix project files 05, 09, 11

---

## Analysis

### Expected Behavior
If load case `DES_X` appears in files 05, 09, and 11 across multiple result types:
- File 05: Story Drifts, Story Forces, etc.
- File 09: Story Drifts, Story Forces, etc.
- File 11: Story Drifts, Story Forces, etc.

**Expected**: Conflict dialog should show `DES_X` with conflicts for each sheet type.

---

## Conflict Detection Logic

### Phase 1: Scanning (Lines 592-632)
```python
# Collects all load cases from all files
for file_name, sheets in file_load_cases.items():
    for sheet_name, load_cases in sheets.items():
        for lc in load_cases:
            all_load_cases.add(lc)
            if lc not in load_case_sources:
                load_case_sources[lc] = []
            load_case_sources[lc].append((file_name, sheet_name))
```

**Result**: `load_case_sources` structure:
```python
{
    "DES_X": [
        ("file_05.xlsx", "Story Drifts"),
        ("file_05.xlsx", "Story Forces"),
        ("file_09.xlsx", "Story Drifts"),
        ("file_09.xlsx", "Story Forces"),
        ("file_11.xlsx", "Story Drifts"),
        ("file_11.xlsx", "Story Forces"),
    ]
}
```

### Phase 2: Conflict Detection (Lines 904-923)
```python
for lc in selected_load_cases:
    sources = self.load_case_sources.get(lc, [])
    if len(sources) > 1:
        # Group by sheet
        sheet_files = {}
        for file_name, sheet_name in sources:
            if sheet_name not in sheet_files:
                sheet_files[sheet_name] = []
            sheet_files[sheet_name].append(file_name)

        # Check if any sheet has multiple files
        has_conflict = any(len(files) > 1 for files in sheet_files.values())
        if has_conflict:
            conflicts[lc] = sheet_files
```

**Result**: `conflicts` structure:
```python
{
    "DES_X": {
        "Story Drifts": ["file_05.xlsx", "file_09.xlsx", "file_11.xlsx"],
        "Story Forces": ["file_05.xlsx", "file_09.xlsx", "file_11.xlsx"]
    }
}
```

---

## Debug Logging Added

### 1. After Scanning (Line 618-626)
Shows load cases that appear in multiple files:
```
- Load cases in multiple files (X):
  DES_X: 6 occurrences in file_05.xlsx, file_09.xlsx, file_11.xlsx
  MCE_X: 6 occurrences in file_05.xlsx, file_09.xlsx, file_11.xlsx
  ...
```

### 2. During Conflict Detection (Line 919-923)
Shows detailed conflict breakdown:
```
- Detected 2 conflicting load case(s)
  Conflict: DES_X in 6 locations
    Story Drifts: file_05.xlsx, file_09.xlsx, file_11.xlsx
    Story Forces: file_05.xlsx, file_09.xlsx, file_11.xlsx
  Conflict: MCE_X in 6 locations
    Story Drifts: file_05.xlsx, file_09.xlsx, file_11.xlsx
    Story Forces: file_05.xlsx, file_09.xlsx, file_11.xlsx
```

---

## Possible Issues

### 1. **Scanning Not Detecting All Sheets**
If some sheets are missing from `file_load_cases`, they won't be detected.

**Check**: Look at log output after scanning completes:
- Does it show all expected files?
- Does it list load cases in multiple files?

### 2. **Load Cases Not Selected**
Conflict detection only runs for `selected_load_cases`.

**Check**: Are all load cases checked in the UI before clicking "Import"?

### 3. **File Naming Issues**
If file names are inconsistent (e.g., "05.xlsx" vs "file_05.xlsx"), they won't be grouped.

**Check**: Log output shows actual file names.

### 4. **Sheet Names Differ**
If different files use slightly different sheet names, they won't conflict.

**Check**: Log output shows sheet names for each occurrence.

### 5. **Excel Parser Errors**
If some files fail to parse, they won't appear in `file_load_cases`.

**Check**: Look for errors in scanning phase.

---

## Testing Steps

1. **Open 135Dix project import dialog**
2. **Select folder with files 05, 09, 11**
3. **Check log output after scan**:
   ```
   - Scanning file_05.xlsx...
   - Scanning file_09.xlsx...
   - Scanning file_11.xlsx...
   - Load cases in multiple files (X):
     DES_X: 6 occurrences in file_05.xlsx, file_09.xlsx, file_11.xlsx
   ```
4. **Select all load cases** (or at least DES_X, MCE_X, etc.)
5. **Click "Start Import"**
6. **Check log output for conflicts**:
   ```
   - Checking for conflicts...
     Conflict: DES_X in 6 locations
       Story Drifts: file_05.xlsx, file_09.xlsx, file_11.xlsx
       Story Forces: file_05.xlsx, file_09.xlsx, file_11.xlsx
   - Detected 2 conflicting load case(s)
   ```
7. **Conflict dialog should appear**

---

## Next Steps

Based on log output, we can determine:
- ✅ If scanning detects all files and sheets
- ✅ If load case sources are populated correctly
- ✅ If conflicts are detected properly
- ✅ Which specific load cases/sheets are missing

**Please run the import and share the log output.**

---

## Files Modified

- `src/gui/folder_import_dialog.py`:
  - Line 618-626: Added debug logging for multi-source load cases
  - Line 919-923: Added debug logging for detected conflicts

---

**Status**: Debug logging added, ready for testing
