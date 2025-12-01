"""Test that 711Vic file is now detected by parsers."""

from pathlib import Path
from src.processing.pushover_global_parser import PushoverGlobalParser
from src.processing.pushover_column_parser import PushoverColumnParser
from src.processing.pushover_beam_parser import PushoverBeamParser

file_path = Path(r"Typical Pushover Results\711Vic_Push_DES_All.xlsx")

print("Testing pushover parsers with 711Vic file...")
print("=" * 80)

# Test global parser
print("\n1. Global Parser (Story Drifts, Forces, Displacements):")
try:
    global_parser = PushoverGlobalParser(file_path)
    directions = global_parser.get_available_directions()
    print(f"   Detected directions: {directions}")

    if directions:
        for direction in directions:
            cases = global_parser.get_output_cases(direction)
            print(f"   {direction} direction load cases: {cases}")
    else:
        print("   [ERROR] No directions detected!")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test column parser
print("\n2. Column Parser (Fiber Hinge States):")
try:
    column_parser = PushoverColumnParser(file_path)
    directions = column_parser.get_available_directions()
    print(f"   Detected directions: {directions}")

    if directions:
        for direction in directions:
            cases = column_parser.get_output_cases(direction)
            print(f"   {direction} direction load cases: {cases}")
    else:
        print("   [ERROR] No directions detected!")
except Exception as e:
    print(f"   [ERROR] {e}")

# Test beam parser
print("\n3. Beam Parser (Hinge States):")
try:
    beam_parser = PushoverBeamParser(file_path)
    directions = beam_parser.get_available_directions()
    print(f"   Detected directions: {directions}")

    if directions:
        for direction in directions:
            cases = beam_parser.get_output_cases(direction)
            print(f"   {direction} direction load cases: {cases}")
    else:
        print("   [ERROR] No directions detected!")
except Exception as e:
    print(f"   [ERROR] {e}")

print("\n" + "=" * 80)
print("Test complete! The file should now be recognized by all parsers.")
