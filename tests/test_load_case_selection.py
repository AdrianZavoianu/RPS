"""
Test script for load case selection and conflict resolution.

This demonstrates the new EnhancedFolderImporter workflow with GUI dialogs.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import pytest

from PyQt6.QtWidgets import QApplication, QMessageBox
from processing.enhanced_folder_importer import EnhancedFolderImporter
from services.project_service import get_session


@pytest.mark.skip(reason="Interactive manual test requires user input")
def test_enhanced_import():
    """Test the enhanced folder import with load case selection."""

    # Example usage
    folder_path = input("Enter folder path with Excel files: ").strip()

    if not folder_path or not Path(folder_path).exists():
        print("Invalid folder path")
        return

    project_name = input("Enter project name (e.g., TestProject): ").strip()
    if not project_name:
        project_name = "TestProject"

    result_set_name = input("Enter result set name (e.g., DES): ").strip()
    if not result_set_name:
        result_set_name = "TestResultSet"

    print(f"\nStarting enhanced import...")
    print(f"  Folder: {folder_path}")
    print(f"  Project: {project_name}")
    print(f"  Result Set: {result_set_name}")
    print()

    # Progress callback
    def progress_callback(message: str, current: int, total: int):
        if total > 0:
            percent = (current / total) * 100
            print(f"[{percent:5.1f}%] {message}")
        else:
            print(f"[ ... ] {message}")

    try:
        # Create importer
        importer = EnhancedFolderImporter(
            folder_path=folder_path,
            project_name=project_name,
            result_set_name=result_set_name,
            session_factory=get_session,
            progress_callback=progress_callback,
            parent_widget=None,  # No parent in console mode
        )

        # Run import (will show dialogs)
        stats = importer.import_all()

        # Display results
        print("\n" + "="*60)
        print("Import Complete!")
        print("="*60)
        print(f"Project: {stats.get('project', 'N/A')}")
        print(f"Files processed: {stats['files_processed']} / {stats['files_total']}")
        print(f"Load cases imported: {stats['load_cases']}")
        print(f"Load cases skipped: {stats.get('load_cases_skipped', 0)}")
        print(f"Stories: {stats['stories']}")
        print(f"Story drifts: {stats.get('drifts', 0)}")
        print(f"Accelerations: {stats.get('accelerations', 0)}")
        print(f"Forces: {stats.get('forces', 0)}")
        print(f"Pier forces: {stats.get('pier_forces', 0)}")
        print(f"Column forces: {stats.get('column_forces', 0)}")

        if stats.get('errors'):
            print(f"\nErrors:")
            for error in stats['errors']:
                print(f"  - {error}")

        print()

    except Exception as e:
        print(f"\nError during import: {e}")
        import traceback
        traceback.print_exc()


def test_dialogs_only():
    """Test just the dialogs without actual import."""
    from gui.load_case_selection_dialog import LoadCaseSelectionDialog
    from gui.load_case_conflict_dialog import LoadCaseConflictDialog

    print("Testing LoadCaseSelectionDialog...")

    # Mock data
    all_load_cases = {
        "DES_X", "DES_Y", "MCE_X", "MCE_Y",
        "SLE_X", "SLE_Y",
        "WIND_0", "WIND_45", "WIND_90",
        "TEST_1", "TEST_2",
        "PRELIM_A"
    }

    load_case_sources = {
        "DES_X": [("file1.xlsx", "Story Drifts"), ("file1.xlsx", "Story Forces")],
        "DES_Y": [("file1.xlsx", "Story Drifts"), ("file1.xlsx", "Story Forces")],
        "MCE_X": [("file1.xlsx", "Story Drifts")],
        "MCE_Y": [("file1.xlsx", "Story Drifts")],
        "SLE_X": [("file2.xlsx", "Story Drifts")],
        "SLE_Y": [("file2.xlsx", "Story Drifts")],
        "WIND_0": [("file3.xlsx", "Story Drifts"), ("file3.xlsx", "Pier Forces")],
        "WIND_45": [("file3.xlsx", "Story Drifts"), ("file3.xlsx", "Pier Forces")],
        "WIND_90": [("file3.xlsx", "Story Drifts")],
        "TEST_1": [("file1.xlsx", "Story Drifts")],
        "TEST_2": [("file1.xlsx", "Story Drifts")],
        "PRELIM_A": [("file2.xlsx", "Story Drifts")],
    }

    app = QApplication(sys.argv)

    # Test selection dialog
    selection_dialog = LoadCaseSelectionDialog(
        all_load_cases=all_load_cases,
        load_case_sources=load_case_sources,
        result_set_name="DES",
        parent=None
    )

    if selection_dialog.exec():
        selected = selection_dialog.get_selected_load_cases()
        print(f"\nUser selected {len(selected)} load cases:")
        for lc in sorted(selected):
            print(f"  - {lc}")

        # Test conflict dialog (simulate conflict)
        conflicts = {
            "DES_X": {
                "Story Drifts": ["file1.xlsx", "file2.xlsx"],
                "Story Forces": ["file1.xlsx", "file2.xlsx"]
            },
            "MCE_X": {
                "Story Drifts": ["file1.xlsx", "file3.xlsx"]
            }
        }

        print("\nTesting LoadCaseConflictDialog...")
        conflict_dialog = LoadCaseConflictDialog(
            conflicts=conflicts,
            parent=None
        )

        if conflict_dialog.exec():
            resolution = conflict_dialog.get_resolution()
            print(f"\nUser resolution:")
            for lc, file in resolution.items():
                if file:
                    print(f"  {lc}: Use {file}")
                else:
                    print(f"  {lc}: Skip")
        else:
            print("\nConflict resolution cancelled")
    else:
        print("\nLoad case selection cancelled")


if __name__ == "__main__":
    print("="*60)
    print("Enhanced Load Case Selection - Test Script")
    print("="*60)
    print()
    print("Choose test mode:")
    print("  1. Test dialogs only (no actual import)")
    print("  2. Test full enhanced import (requires valid Excel files)")
    print()

    choice = input("Enter choice (1 or 2): ").strip()

    if choice == "1":
        app = QApplication(sys.argv)
        test_dialogs_only()
    elif choice == "2":
        # Need QApplication for dialogs even in enhanced import
        app = QApplication(sys.argv)
        test_enhanced_import()
    else:
        print("Invalid choice")
