"""Check what sheets are available in the pushover Excel file."""

from pathlib import Path
import pandas as pd

excel_file = Path(r"Typical Pushover Results\711Vic_Push_DES_All.xlsx")

if not excel_file.exists():
    print(f"[ERROR] File not found: {excel_file}")
    exit(1)

print(f"Checking sheets in: {excel_file.name}")
print("=" * 80)

xl = pd.ExcelFile(excel_file)

print(f"\nFound {len(xl.sheet_names)} sheets:")
print("-" * 80)

for i, sheet_name in enumerate(xl.sheet_names, 1):
    print(f"{i:2d}. {sheet_name}")

# Check for column-related sheets
print("\n" + "=" * 80)
print("Column-related sheets:")
print("-" * 80)

column_sheets = [s for s in xl.sheet_names if 'Column' in s or 'column' in s]
if column_sheets:
    for sheet in column_sheets:
        print(f"  - {sheet}")
else:
    print("  [No column-specific sheets found]")

# Check for element force sheets
print("\n" + "=" * 80)
print("Element Force sheets:")
print("-" * 80)

force_sheets = [s for s in xl.sheet_names if 'Force' in s or 'force' in s or 'Element' in s]
if force_sheets:
    for sheet in force_sheets:
        print(f"  - {sheet}")
        # Read first few rows to check structure
        df = pd.read_excel(xl, sheet_name=sheet, nrows=5)
        print(f"    Columns: {', '.join(df.columns[:10].tolist())}...")
        print()
else:
    print("  [No element force sheets found]")
