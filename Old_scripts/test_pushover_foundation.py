"""
Test script for pushover foundation results (soil pressures and vertical displacements)
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from processing.pushover_soil_pressure_parser import PushoverSoilPressureParser
from processing.pushover_vert_displacement_parser import PushoverVertDisplacementParser

def test_soil_pressure_parser():
    """Test soil pressure parser with pushover Excel file."""
    file_path = Path(r"Typical Pushover Results\711Vic_Push_DES_All.xlsx")

    if not file_path.exists():
        print(f"[FAIL] Test file not found: {file_path}")
        return False

    print("\n" + "="*80)
    print("Testing Pushover Soil Pressure Parser")
    print("="*80)

    try:
        parser = PushoverSoilPressureParser(file_path)

        # Check available directions
        directions = parser.get_available_directions()
        print(f"\n[OK] Available directions: {directions}")

        if not directions:
            print("[FAIL] No directions found")
            return False

        # Test X direction
        if 'X' in directions:
            print("\n--- Testing X Direction ---")

            # Get output cases
            cases = parser.get_output_cases('X')
            print(f"[OK] Output cases for X ({len(cases)}): {cases[:3]}...")

            # Parse data
            results = parser.parse('X')

            if results.soil_pressures is not None:
                df = results.soil_pressures
                print(f"[OK] Parsed soil pressures: {df.shape[0]} elements x {df.shape[1]-2} load cases")
                print(f"  Columns: {list(df.columns[:5])}...")
                print(f"\n  Sample data:")
                print(df.head())
            else:
                print("[FAIL] No soil pressure data parsed")
                return False

        # Test Y direction
        if 'Y' in directions:
            print("\n--- Testing Y Direction ---")

            # Get output cases
            cases = parser.get_output_cases('Y')
            print(f"[OK] Output cases for Y ({len(cases)}): {cases[:3]}...")

            # Parse data
            results = parser.parse('Y')

            if results.soil_pressures is not None:
                df = results.soil_pressures
                print(f"[OK] Parsed soil pressures: {df.shape[0]} elements x {df.shape[1]-2} load cases")
            else:
                print("[FAIL] No soil pressure data parsed")
                return False

        print("\n[PASS] Soil pressure parser test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Soil pressure parser test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vert_displacement_parser():
    """Test vertical displacement parser with pushover Excel file."""
    file_path = Path(r"Typical Pushover Results\711Vic_Push_DES_All.xlsx")

    if not file_path.exists():
        print(f"[FAIL] Test file not found: {file_path}")
        return False

    print("\n" + "="*80)
    print("Testing Pushover Vertical Displacement Parser")
    print("="*80)

    try:
        parser = PushoverVertDisplacementParser(file_path)

        # Check foundation joints
        foundation_joints = parser.get_foundation_joints()
        print(f"\n[OK] Foundation joints from Fou sheet ({len(foundation_joints)}): {foundation_joints[:10]}...")

        if not foundation_joints:
            print("[FAIL] No foundation joints found")
            return False

        # Check available directions
        directions = parser.get_available_directions()
        print(f"[OK] Available directions: {directions}")

        if not directions:
            print("[FAIL] No directions found")
            return False

        # Test X direction
        if 'X' in directions:
            print("\n--- Testing X Direction ---")

            # Get output cases
            cases = parser.get_output_cases('X')
            print(f"[OK] Output cases for X ({len(cases)}): {cases[:3]}...")

            # Parse data
            results = parser.parse('X')

            if results.vert_displacements is not None:
                df = results.vert_displacements
                print(f"[OK] Parsed vertical displacements: {df.shape[0]} joints x {df.shape[1]-3} load cases")
                print(f"  Columns: {list(df.columns[:6])}...")
                print(f"\n  Sample data:")
                print(df.head())
            else:
                print("[FAIL] No vertical displacement data parsed")
                return False

        # Test Y direction
        if 'Y' in directions:
            print("\n--- Testing Y Direction ---")

            # Get output cases
            cases = parser.get_output_cases('Y')
            print(f"[OK] Output cases for Y ({len(cases)}): {cases[:3]}...")

            # Parse data
            results = parser.parse('Y')

            if results.vert_displacements is not None:
                df = results.vert_displacements
                print(f"[OK] Parsed vertical displacements: {df.shape[0]} joints x {df.shape[1]-3} load cases")
            else:
                print("[FAIL] No vertical displacement data parsed")
                return False

        print("\n[PASS] Vertical displacement parser test PASSED")
        return True

    except Exception as e:
        print(f"\n[FAIL] Vertical displacement parser test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("PUSHOVER FOUNDATION RESULTS TEST SUITE")
    print("="*80)

    results = []

    # Test soil pressure parser
    results.append(("Soil Pressure Parser", test_soil_pressure_parser()))

    # Test vertical displacement parser
    results.append(("Vertical Displacement Parser", test_vert_displacement_parser()))

    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"{test_name}: {status}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n*** All tests PASSED! ***")
    else:
        print("\n*** Some tests FAILED ***")

    print("="*80 + "\n")
