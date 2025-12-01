"""Test pushover wall rotation parser"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_wall_parser import PushoverWallParser

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Walls.xlsx")

print("=" * 80)
print("Testing PushoverWallParser - Rotations")
print("=" * 80)

parser = PushoverWallParser(excel_file)

# Check quads
quads = parser.get_quads()
print(f"\nQuads ({len(quads)}): {quads[:10]}...")  # Show first 10

# Parse X direction
print(f"\n" + "=" * 80)
print("Parsing X Direction - Rotations")
print("=" * 80)

x_results = parser.parse('X')
print(f"\nX Results:")
print(f"  - Shears V2: {x_results.shears_v2.shape if x_results.shears_v2 is not None else 'None'}")
print(f"  - Shears V3: {x_results.shears_v3.shape if x_results.shears_v3 is not None else 'None'}")
print(f"  - Rotations: {x_results.rotations.shape if x_results.rotations is not None else 'None'}")

if x_results.rotations is not None:
    print(f"\nRotations sample (first 10 rows):")
    print(x_results.rotations.head(10))

# Parse Y direction
print(f"\n" + "=" * 80)
print("Parsing Y Direction - Rotations")
print("=" * 80)

y_results = parser.parse('Y')
print(f"\nY Results:")
print(f"  - Shears V2: {y_results.shears_v2.shape if y_results.shears_v2 is not None else 'None'}")
print(f"  - Shears V3: {y_results.shears_v3.shape if y_results.shears_v3 is not None else 'None'}")
print(f"  - Rotations: {y_results.rotations.shape if y_results.rotations is not None else 'None'}")

if y_results.rotations is not None:
    print(f"\nRotations sample (first 10 rows):")
    print(y_results.rotations.head(10))

print("\n" + "=" * 80)
