"""Test pushover beam parser"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_beam_parser import PushoverBeamParser

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Beam Hinges.xlsx")

print("=" * 80)
print("Testing PushoverBeamParser")
print("=" * 80)

parser = PushoverBeamParser(excel_file)

# Check available directions
directions = parser.get_available_directions()
print(f"\nAvailable directions: {directions}")

# Check beams
beams = parser.get_beams()
print(f"\nBeams ({len(beams)}): {beams}")

# Parse X direction
print(f"\n" + "=" * 80)
print("Parsing X Direction")
print("=" * 80)

x_cases = parser.get_output_cases('X')
print(f"\nX output cases ({len(x_cases)}): {x_cases}")

x_results = parser.parse('X')
print(f"\nX Results:")
print(f"  - Rotations (R3 Plastic): {x_results.rotations.shape if x_results.rotations is not None else 'None'}")

if x_results.rotations is not None:
    print(f"\nRotations sample (first 10 rows):")
    print(x_results.rotations.head(10))

# Parse Y direction
print(f"\n" + "=" * 80)
print("Parsing Y Direction")
print("=" * 80)

y_cases = parser.get_output_cases('Y')
print(f"\nY output cases ({len(y_cases)}): {y_cases}")

y_results = parser.parse('Y')
print(f"\nY Results:")
print(f"  - Rotations (R3 Plastic): {y_results.rotations.shape if y_results.rotations is not None else 'None'}")

if y_results.rotations is not None:
    print(f"\nRotations sample (first 10 rows):")
    print(y_results.rotations.head(10))

print("\n" + "=" * 80)
