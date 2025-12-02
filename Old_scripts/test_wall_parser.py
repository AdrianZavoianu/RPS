"""Test pushover wall parser"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_wall_parser import PushoverWallParser

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Walls.xlsx")

print("=" * 80)
print("Testing PushoverWallParser")
print("=" * 80)

parser = PushoverWallParser(excel_file)

# Check available directions
directions = parser.get_available_directions()
print(f"\nAvailable directions: {directions}")

# Check piers
piers = parser.get_piers()
print(f"\nPiers: {piers}")

# Parse X direction
print(f"\n" + "=" * 80)
print("Parsing X Direction")
print("=" * 80)

x_cases = parser.get_output_cases('X')
print(f"\nX output cases ({len(x_cases)}): {x_cases}")

x_results = parser.parse('X')
print(f"\nX Results:")
print(f"  - Shears V2: {x_results.shears_v2.shape if x_results.shears_v2 is not None else 'None'}")
print(f"  - Shears V3: {x_results.shears_v3.shape if x_results.shears_v3 is not None else 'None'}")

if x_results.shears_v2 is not None:
    print(f"\nV2 Shears sample (first 10 rows):")
    print(x_results.shears_v2.head(10))

# Parse Y direction
print(f"\n" + "=" * 80)
print("Parsing Y Direction")
print("=" * 80)

y_cases = parser.get_output_cases('Y')
print(f"\nY output cases ({len(y_cases)}): {y_cases}")

y_results = parser.parse('Y')
print(f"\nY Results:")
print(f"  - Shears V2: {y_results.shears_v2.shape if y_results.shears_v2 is not None else 'None'}")
print(f"  - Shears V3: {y_results.shears_v3.shape if y_results.shears_v3 is not None else 'None'}")

if y_results.shears_v2 is not None:
    print(f"\nV2 Shears sample (first 10 rows):")
    print(y_results.shears_v2.head(10))

print("\n" + "=" * 80)
