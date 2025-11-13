"""Test script to check soil pressure import."""

import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.excel_parser import ExcelParser

# Test file path - you'll need to provide an actual Excel file with Soil Pressures sheet
test_file = Path("path/to/your/excel/file.xlsx")  # UPDATE THIS PATH

if not test_file.exists():
    print(f"ERROR: Test file not found: {test_file}")
    print("Please update the test_file path in this script to point to an Excel file with a 'Soil Pressures' sheet")
    sys.exit(1)

parser = ExcelParser(test_file)

# Check if Soil Pressures sheet exists
if not parser.validate_sheet_exists("Soil Pressures"):
    print("ERROR: 'Soil Pressures' sheet not found in Excel file")
    available_sheets = parser.file_path
    print(f"File: {available_sheets}")
    sys.exit(1)

print("✓ Excel file found")
print("✓ 'Soil Pressures' sheet exists")

# Try to parse the data
try:
    df, load_cases, unique_elements = parser.get_soil_pressures()
    print(f"\n=== Parsing Results ===")
    print(f"Load cases found: {len(load_cases)}")
    print(f"Load cases: {load_cases}")
    print(f"Unique elements found: {len(unique_elements)}")
    print(f"Unique elements (first 10): {unique_elements[:10]}")
    print(f"Total rows in aggregated data: {len(df)}")
    print(f"\nFirst few rows:")
    print(df.head())
    print("\n✓ Parsing successful!")

except Exception as e:
    print(f"\nERROR during parsing: {e}")
    import traceback
    traceback.print_exc()
