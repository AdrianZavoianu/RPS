"""Test script to trace import flow for debugging."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from processing.folder_importer import TARGET_SHEETS

print("TARGET_SHEETS mapping:")
for sheet, labels in TARGET_SHEETS.items():
    print(f"  {sheet} -> {labels}")

print("\n" + "="*60 + "\n")

# Check what result_types would be passed
# Simulate the flow in EnhancedFolderImporter
print("Simulating EnhancedFolderImporter logic:")
print("Assuming sheet 'Joint DisplacementsG' is available in Excel...")

sheet = "Joint DisplacementsG"
if sheet in TARGET_SHEETS:
    labels = TARGET_SHEETS[sheet]
    print(f"  Found labels: {labels}")
    print(f"  Lowercase: {[l.strip().lower() for l in labels]}")
else:
    print(f"  Sheet '{sheet}' NOT in TARGET_SHEETS!")

print("\n" + "="*60 + "\n")

# Check what DataImporter._should_import() would see
print("DataImporter._should_import() logic:")
print("  Checks if 'Floors Displacements'.strip().lower() in result_types")
print(f"  That is: '{'floors displacements'.lower()}' in result_types")
print(f"  Result types from TARGET_SHEETS: {[l.strip().lower() for l in TARGET_SHEETS.get('Joint DisplacementsG', [])]}")

# Check element sheets
print("\n" + "="*60 + "\n")
print("Element result sheets:")
element_sheets = ["Pier Forces", "Element Forces - Columns", "Fiber Hinge States", "Hinge States", "Quad Strain Gauge - Rotation"]
for sheet in element_sheets:
    if sheet in TARGET_SHEETS:
        print(f"  ✓ {sheet} -> {TARGET_SHEETS[sheet]}")
    else:
        print(f"  ✗ {sheet} NOT IN TARGET_SHEETS")
