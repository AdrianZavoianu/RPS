"""Test pushover joint parser"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_joint_parser import PushoverJointParser

excel_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Global_Resp.xlsx")

print("=" * 80)
print("Testing PushoverJointParser")
print("=" * 80)

parser = PushoverJointParser(excel_file)

# Check available directions
directions = parser.get_available_directions()
print(f"\nAvailable directions: {directions}")

# Check joints
joints = parser.get_joints()
print(f"\nJoints ({len(joints)}): {joints[:10]}")
if len(joints) > 10:
    print(f"  ... and {len(joints) - 10} more")

# Parse X direction
print(f"\n" + "=" * 80)
print("Parsing X Direction")
print("=" * 80)

x_cases = parser.get_output_cases('X')
print(f"\nX output cases ({len(x_cases)}): {x_cases}")

x_results = parser.parse('X')
print(f"\nX Results:")
print(f"  - Ux Displacements: {x_results.displacements_ux.shape if x_results.displacements_ux is not None else 'None'}")
print(f"  - Uy Displacements: {x_results.displacements_uy.shape if x_results.displacements_uy is not None else 'None'}")
print(f"  - Uz Displacements: {x_results.displacements_uz.shape if x_results.displacements_uz is not None else 'None'}")

if x_results.displacements_ux is not None:
    print(f"\nUx Displacements sample (first 10 rows):")
    print(x_results.displacements_ux.head(10))

# Parse Y direction
print(f"\n" + "=" * 80)
print("Parsing Y Direction")
print("=" * 80)

y_cases = parser.get_output_cases('Y')
print(f"\nY output cases ({len(y_cases)}): {y_cases}")

y_results = parser.parse('Y')
print(f"\nY Results:")
print(f"  - Ux Displacements: {y_results.displacements_ux.shape if y_results.displacements_ux is not None else 'None'}")
print(f"  - Uy Displacements: {y_results.displacements_uy.shape if y_results.displacements_uy is not None else 'None'}")
print(f"  - Uz Displacements: {y_results.displacements_uz.shape if y_results.displacements_uz is not None else 'None'}")

if y_results.displacements_uy is not None:
    print(f"\nUy Displacements sample (first 10 rows):")
    print(y_results.displacements_uy.head(10))

print("\n" + "=" * 80)
