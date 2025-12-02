"""Test pushover column parser"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_column_parser import PushoverColumnParser

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Column Hinges.xlsx")

print("=" * 80)
print("Testing PushoverColumnParser")
print("=" * 80)

parser = PushoverColumnParser(excel_file)

# Check available directions
directions = parser.get_available_directions()
print(f"\nAvailable directions: {directions}")

# Check columns
columns = parser.get_columns()
print(f"\nColumns ({len(columns)}): {columns}")

# Parse X direction
print(f"\n" + "=" * 80)
print("Parsing X Direction")
print("=" * 80)

x_cases = parser.get_output_cases('X')
print(f"\nX output cases ({len(x_cases)}): {x_cases}")

x_results = parser.parse('X')
print(f"\nX Results:")
print(f"  - Rotations R2: {x_results.rotations_r2.shape if x_results.rotations_r2 is not None else 'None'}")
print(f"  - Rotations R3: {x_results.rotations_r3.shape if x_results.rotations_r3 is not None else 'None'}")

if x_results.rotations_r2 is not None:
    print(f"\nR2 Rotations sample (first 10 rows):")
    print(x_results.rotations_r2.head(10))

# Parse Y direction
print(f"\n" + "=" * 80)
print("Parsing Y Direction")
print("=" * 80)

y_cases = parser.get_output_cases('Y')
print(f"\nY output cases ({len(y_cases)}): {y_cases}")

y_results = parser.parse('Y')
print(f"\nY Results:")
print(f"  - Rotations R2: {y_results.rotations_r2.shape if y_results.rotations_r2 is not None else 'None'}")
print(f"  - Rotations R3: {y_results.rotations_r3.shape if y_results.rotations_r3 is not None else 'None'}")

if y_results.rotations_r2 is not None:
    print(f"\nR2 Rotations sample (first 10 rows):")
    print(y_results.rotations_r2.head(10))

print("\n" + "=" * 80)
