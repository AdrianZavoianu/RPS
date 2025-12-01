"""Test pushover shorthand mapping for 711 project load cases."""

from src.utils.pushover_utils import create_pushover_shorthand_mapping

# 711 project load cases
load_cases_711 = [
    "Push Modal X",
    "Push Modal Y",
    "Push Uniform X",
    "Push Uniform Y"
]

print("Testing pushover shorthand mapping for 711 project...")
print("=" * 80)

print("\nInput load cases:")
for case in load_cases_711:
    print(f"  - {case}")

print("\nCreating mapping...")
mapping = create_pushover_shorthand_mapping(load_cases_711)

print("\n" + "=" * 80)
print("MAPPING RESULTS:")
print("=" * 80)
for full_name, shorthand in sorted(mapping.items()):
    print(f"  {shorthand:<6} = {full_name}")

print("\n" + "=" * 80)
print("Expected mappings:")
print("  Px1    = Push Modal X")
print("  Px2    = Push Uniform X")
print("  Py1    = Push Modal Y")
print("  Py2    = Push Uniform Y")
