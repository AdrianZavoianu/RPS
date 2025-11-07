"""Test selective import to see what result_types filtering does."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

# Test _should_import logic
class MockImporter:
    def __init__(self, result_types):
        self.result_types = result_types

    def _should_import(self, label: str) -> bool:
        """Check if result type should be imported."""
        if not self.result_types:
            return True
        return label.strip().lower() in self.result_types

# Test 1: None result_types (should import all)
print("Test 1: result_types = None")
importer = MockImporter(None)
test_labels = [
    "Story Drifts",
    "Story Accelerations",
    "Story Forces",
    "Floors Displacements",
    "Pier Forces",
    "Column Forces",
    "Column Axials",
    "Column Rotations",
    "Beam Rotations",
    "Quad Rotations"
]

for label in test_labels:
    should = importer._should_import(label)
    print(f"  {label}: {should}")

print("\n" + "="*60 + "\n")

# Test 2: Specific result_types (like user might have selected)
print("Test 2: result_types = {'story drifts', 'floors displacements', 'pier forces'}")
importer = MockImporter({'story drifts', 'floors displacements', 'pier forces'})

for label in test_labels:
    should = importer._should_import(label)
    print(f"  {label}: {should}")

print("\n" + "="*60 + "\n")

# Test 3: Empty set (should import nothing)
print("Test 3: result_types = set()")
importer = MockImporter(set())

for label in test_labels:
    should = importer._should_import(label)
    print(f"  {label}: {should}")
