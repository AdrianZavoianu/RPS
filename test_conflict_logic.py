# Test the conflict detection logic

# Simulate load_case_sources for DES_X appearing in files 05, 09, 11
# for both Story Drifts and Story Forces
load_case_sources = {
    "DES_X": [
        ("file_05.xlsx", "Story Drifts"),
        ("file_05.xlsx", "Story Forces"),
        ("file_09.xlsx", "Story Drifts"),
        ("file_09.xlsx", "Story Forces"),
        ("file_11.xlsx", "Story Drifts"),
        ("file_11.xlsx", "Story Forces"),
    ]
}

selected_load_cases = {"DES_X"}

# Current logic from folder_import_dialog.py line 904-918
conflicts = {}
for lc in selected_load_cases:
    sources = load_case_sources.get(lc, [])
    if len(sources) > 1:
        # This load case appears in multiple files - group by sheet
        sheet_files = {}
        for file_name, sheet_name in sources:
            if sheet_name not in sheet_files:
                sheet_files[sheet_name] = []
            sheet_files[sheet_name].append(file_name)
        
        print(f"\nLoad case: {lc}")
        print(f"Sheet files: {sheet_files}")
        
        # Only add if there are actual conflicts (same sheet in multiple files)
        has_conflict = any(len(files) > 1 for files in sheet_files.values())
        print(f"Has conflict: {has_conflict}")
        
        if has_conflict:
            conflicts[lc] = sheet_files

print(f"\nFinal conflicts: {conflicts}")
