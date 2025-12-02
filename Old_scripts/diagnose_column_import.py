"""Diagnose column import issues"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_column_parser import PushoverColumnParser

column_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Column Hinges.xlsx")

print("=" * 80)
print("COLUMN IMPORT DIAGNOSTICS")
print("=" * 80)

parser = PushoverColumnParser(column_file)

print("\n1. Parser Initialization:")
print(f"   File: {column_file.name}")
print(f"   Exists: {column_file.exists()}")

print("\n2. Available Directions:")
directions = parser.get_available_directions()
print(f"   {directions}")

print("\n3. Columns Detected:")
columns = parser.get_columns()
print(f"   Count: {len(columns)}")
print(f"   Names: {columns}")

print("\n4. Output Cases (X):")
x_cases = parser.get_output_cases('X')
print(f"   Count: {len(x_cases)}")
for case in x_cases:
    print(f"   - {case}")

print("\n5. Parsing X Direction:")
try:
    x_results = parser.parse('X')
    print(f"   [OK] Parse successful")
    print(f"   R2 rotations: {x_results.rotations_r2.shape if x_results.rotations_r2 is not None else 'None'}")
    print(f"   R3 rotations: {x_results.rotations_r3.shape if x_results.rotations_r3 is not None else 'None'}")

    if x_results.rotations_r2 is not None:
        print(f"\n6. Sample R2 Data:")
        sample = x_results.rotations_r2.head(3)
        print(f"   Columns: {sample.columns.tolist()}")
        print(f"   First 3 rows:")
        for idx, row in sample.iterrows():
            col_name = row[sample.columns[0]]  # Frame/Wall
            unique_name = row[sample.columns[1]]  # Unique Name
            first_case = row[sample.columns[2]] if len(sample.columns) > 2 else None
            print(f"      Row {idx}: Column={col_name}, UniqueName={unique_name}, FirstCase={first_case}")

except Exception as e:
    print(f"   [FAIL] Parse failed: {e}")
    import traceback
    traceback.print_exc()

print("\n7. Unique Name to Story Mapping:")
try:
    import pandas as pd
    raw_df = pd.read_excel(parser.excel_data, sheet_name='Fiber Hinge States', header=1)
    raw_df = raw_df.drop(0)

    unique_story_map = {}
    for _, row in raw_df.iterrows():
        unique_name = str(int(float(row['Unique Name'])))
        story_name = str(row['Story'])
        if unique_name not in unique_story_map:
            unique_story_map[unique_name] = story_name

    print(f"   Total mappings: {len(unique_story_map)}")
    print(f"   Sample mappings:")
    for idx, (un, story) in enumerate(list(unique_story_map.items())[:5]):
        print(f"      {un} -> {story}")

    print(f"\n   Unique stories: {sorted(set(unique_story_map.values()))}")

except Exception as e:
    print(f"   [FAIL] Mapping failed: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("Diagnosis complete.")
print("=" * 80)
print("\nIf all steps show [OK] and data looks correct, the issue is likely in:")
print("  - Database session/transaction")
print("  - Story/Element creation")
print("  - Cache building")
print("\nCheck the application logs for errors during import.")
