"""Test pushover element scanner

Tests that the scanner correctly detects all pushover file types:
- Global results
- Wall results (piers + quads)
- Column results (fiber hinges)
- Beam results (hinges)
"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_global_parser import PushoverGlobalParser
from processing.pushover_wall_parser import PushoverWallParser
from processing.pushover_column_parser import PushoverColumnParser
from processing.pushover_beam_parser import PushoverBeamParser

# Test folder
folder_path = Path(r"C:\SoftDev\RPS\Typical Pushover Results")

print("=" * 80)
print("PUSHOVER ELEMENT SCANNER TEST")
print("=" * 80)
print(f"Scanning folder: {folder_path}")
print()

# Find all Excel files
excel_files = list(folder_path.glob("*.xlsx")) + list(folder_path.glob("*.xls"))
print(f"Found {len(excel_files)} Excel files")
print()

# Initialize collections
global_files = []
wall_files = []
column_files = []
beam_files = []

all_load_cases_x = set()
all_load_cases_y = set()
all_piers = set()
all_columns = set()
all_beams = set()

# Scan each file
for file_path in excel_files:
    print(f"Scanning: {file_path.name}")

    # Try parsing as global results
    try:
        global_parser = PushoverGlobalParser(file_path)
        directions = global_parser.get_available_directions()

        if directions:
            print(f"  [OK] Global results detected: {directions}")
            global_files.append(file_path)

            # Extract load cases
            if 'X' in directions:
                cases_x = global_parser.get_output_cases('X')
                all_load_cases_x.update(cases_x)
            if 'Y' in directions:
                cases_y = global_parser.get_output_cases('Y')
                all_load_cases_y.update(cases_y)
    except Exception as e:
        print(f"  [--] Not global results")

    # Try parsing as wall results
    try:
        wall_parser = PushoverWallParser(file_path)
        directions = wall_parser.get_available_directions()

        if directions:
            print(f"  [OK] Wall results detected: {directions}")
            wall_files.append(file_path)

            # Extract load cases and piers
            if 'X' in directions:
                cases_x = wall_parser.get_output_cases('X')
                all_load_cases_x.update(cases_x)
            if 'Y' in directions:
                cases_y = wall_parser.get_output_cases('Y')
                all_load_cases_y.update(cases_y)

            piers = wall_parser.get_piers()
            all_piers.update(piers)
    except Exception as e:
        print(f"  [--] Not wall results")

    # Try parsing as column results
    try:
        column_parser = PushoverColumnParser(file_path)
        directions = column_parser.get_available_directions()

        if directions:
            print(f"  [OK] Column results detected: {directions}")
            column_files.append(file_path)

            # Extract load cases and columns
            if 'X' in directions:
                cases_x = column_parser.get_output_cases('X')
                all_load_cases_x.update(cases_x)
            if 'Y' in directions:
                cases_y = column_parser.get_output_cases('Y')
                all_load_cases_y.update(cases_y)

            columns = column_parser.get_columns()
            all_columns.update(columns)
    except Exception as e:
        print(f"  [--] Not column results")

    # Try parsing as beam results
    try:
        beam_parser = PushoverBeamParser(file_path)
        directions = beam_parser.get_available_directions()

        if directions:
            print(f"  [OK] Beam results detected: {directions}")
            beam_files.append(file_path)

            # Extract load cases and beams
            if 'X' in directions:
                cases_x = beam_parser.get_output_cases('X')
                all_load_cases_x.update(cases_x)
            if 'Y' in directions:
                cases_y = beam_parser.get_output_cases('Y')
                all_load_cases_y.update(cases_y)

            beams = beam_parser.get_beams()
            all_beams.update(beams)
    except Exception as e:
        print(f"  [--] Not beam results")

print()
print("=" * 80)
print("SCAN RESULTS")
print("=" * 80)

print(f"\nFiles detected:")
print(f"  Global: {len(global_files)}")
for f in global_files:
    print(f"    - {f.name}")

print(f"\n  Walls: {len(wall_files)}")
for f in wall_files:
    print(f"    - {f.name}")

print(f"\n  Columns: {len(column_files)}")
for f in column_files:
    print(f"    - {f.name}")

print(f"\n  Beams: {len(beam_files)}")
for f in beam_files:
    print(f"    - {f.name}")

print(f"\nLoad cases:")
print(f"  X direction ({len(all_load_cases_x)}): {sorted(all_load_cases_x)[:5]}")
if len(all_load_cases_x) > 5:
    print(f"    ... and {len(all_load_cases_x) - 5} more")
print(f"  Y direction ({len(all_load_cases_y)}): {sorted(all_load_cases_y)[:5]}")
if len(all_load_cases_y) > 5:
    print(f"    ... and {len(all_load_cases_y) - 5} more")

print(f"\nElements:")
if all_piers:
    print(f"  Piers ({len(all_piers)}): {sorted(all_piers)[:10]}")
    if len(all_piers) > 10:
        print(f"    ... and {len(all_piers) - 10} more")

if all_columns:
    print(f"  Columns ({len(all_columns)}): {sorted(all_columns)[:10]}")
    if len(all_columns) > 10:
        print(f"    ... and {len(all_columns) - 10} more")

if all_beams:
    print(f"  Beams ({len(all_beams)}): {sorted(all_beams)[:10]}")
    if len(all_beams) > 10:
        print(f"    ... and {len(all_beams) - 10} more")

print()
print("=" * 80)
print("TEST COMPLETE")
print("=" * 80)
