"""Diagnostic script to inspect 711Vic pushover file load case names."""

import pandas as pd
from pathlib import Path

file_path = Path(r"Typical Pushover Results\711Vic_Push_DES_All.xlsx")

if not file_path.exists():
    print(f"File not found: {file_path}")
    exit(1)

print(f"Inspecting: {file_path}")
print("=" * 80)

# Try to read as Excel file
try:
    excel_file = pd.ExcelFile(file_path)
    print(f"\nAvailable sheets: {excel_file.sheet_names}")
except Exception as e:
    print(f"Error reading Excel file: {e}")
    exit(1)

# Check for pushover sheets
pushover_sheets = {
    'Joint Displacements': 'Global',
    'Story Drifts': 'Global',
    'Story Forces': 'Global',
    'Pier Forces': 'Wall',
    'Fiber Hinge States': 'Column',
    'Hinge States': 'Beam',
    'Quad Strain Gauge - Rotation': 'Wall (Quads)'
}

print("\n" + "=" * 80)
print("SHEET DETECTION:")
print("=" * 80)
for sheet, type_ in pushover_sheets.items():
    if sheet in excel_file.sheet_names:
        print(f"[YES] {sheet:<35} ({type_})")
    else:
        print(f"[NO]  {sheet:<35} (MISSING)")

# For each found sheet, check load case names
print("\n" + "=" * 80)
print("LOAD CASE NAMES:")
print("=" * 80)

for sheet in excel_file.sheet_names:
    if sheet in pushover_sheets:
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet, header=1)
            df = df.drop(0)  # Drop units row

            if 'Output Case' in df.columns:
                output_cases = df['Output Case'].dropna().unique()
                print(f"\n{sheet}:")
                print(f"  Found {len(output_cases)} unique load cases:")
                for case in sorted(output_cases):
                    print(f"    - {case}")
            else:
                print(f"\n{sheet}: No 'Output Case' column found")

        except Exception as e:
            print(f"\n{sheet}: Error reading - {e}")

print("\n" + "=" * 80)
print("REGEX PATTERN MATCHING TEST:")
print("=" * 80)

import re

# Test our detection patterns
patterns = {
    'XY Bi-directional': r'[_/](XY|YX)[+-]',
    'X Uni-directional': r'[_/]X[+-]',
    'Y Uni-directional': r'[_/]Y[+-]'
}

# Get a sample of output cases from first available sheet
sample_cases = []
for sheet in excel_file.sheet_names:
    if sheet in pushover_sheets:
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet, header=1)
            df = df.drop(0)
            if 'Output Case' in df.columns:
                sample_cases = df['Output Case'].dropna().unique()[:5]  # First 5
                break
        except:
            pass

if sample_cases.any():
    print(f"\nTesting patterns on sample cases:")
    for case in sample_cases:
        print(f"\n  Case: '{case}'")
        for pattern_name, pattern in patterns.items():
            match = re.search(pattern, str(case), re.IGNORECASE)
            if match:
                print(f"    [YES] {pattern_name}: MATCH (matched: {match.group()})")
            else:
                print(f"    [NO]  {pattern_name}: NO MATCH")

        # Test simple X/Y presence
        has_x = 'X' in str(case).upper()
        has_y = 'Y' in str(case).upper()
        print(f"    Simple check: X={has_x}, Y={has_y}")
else:
    print("\nNo output cases found for testing")
