#!/usr/bin/env python
"""Quick script to check load cases in Excel files."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from processing.excel_parser import ExcelParser

folder = Path(r"C:\Users\zavoi\Dropbox\134Dix")

print("Checking Excel files for load cases...\n")

for file_path in sorted(folder.glob("*.xlsx")):
    if file_path.name.startswith("~$"):
        continue

    print(f"\n{'='*60}")
    print(f"File: {file_path.name}")
    print('='*60)

    try:
        parser = ExcelParser(str(file_path))

        # Check Story Drifts
        if parser.validate_sheet_exists("Story Drifts"):
            try:
                _, load_cases, _ = parser.get_story_drifts()
                if load_cases:
                    print(f"  Story Drifts: {', '.join(load_cases[:5])}")
                    if len(load_cases) > 5:
                        print(f"                ... and {len(load_cases) - 5} more")
            except Exception as e:
                print(f"  Story Drifts: ERROR - {e}")

        # Check Story Forces
        if parser.validate_sheet_exists("Story Forces"):
            try:
                _, load_cases, _ = parser.get_story_forces()
                if load_cases:
                    print(f"  Story Forces: {', '.join(load_cases[:5])}")
                    if len(load_cases) > 5:
                        print(f"                ... and {len(load_cases) - 5} more")
            except Exception as e:
                print(f"  Story Forces: ERROR - {e}")

        # Check Pier Forces
        if parser.validate_sheet_exists("Pier Forces"):
            try:
                _, load_cases, _, _ = parser.get_pier_forces()
                if load_cases:
                    print(f"  Pier Forces:  {', '.join(load_cases[:5])}")
                    if len(load_cases) > 5:
                        print(f"                ... and {len(load_cases) - 5} more")
            except Exception as e:
                print(f"  Pier Forces: ERROR - {e}")

    except Exception as e:
        print(f"  ERROR opening file: {e}")

print("\n" + "="*60)
print("Done!")
