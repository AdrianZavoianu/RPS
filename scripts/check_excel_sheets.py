"""Check what sheets are in sample Excel files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from processing.excel_parser import ExcelParser

files = [
    "Typical Input/160Wil_DES_Global.xlsx",
    "Typical Input/160Wil_DES_Elem.xlsx",
]

for file_path in files:
    print(f"\n{'='*60}")
    print(f"File: {file_path}")
    print('='*60)

    try:
        parser = ExcelParser(file_path)
        sheets = parser.get_available_sheets()
        print(f"Found {len(sheets)} sheets:")
        for sheet in sorted(sheets):
            print(f"  - {sheet}")
    except Exception as e:
        print(f"ERROR: {e}")
