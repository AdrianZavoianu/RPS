"""Test column import to debug issues"""
import sys
sys.path.insert(0, 'src')

from pathlib import Path
from processing.pushover_column_parser import PushoverColumnParser
from processing.pushover_column_importer import PushoverColumnImporter
from database.session_manager import get_session
from database.models import ResultSet, Project

# Test file
column_file = Path(r"C:\SoftDev\RPS\Typical Pushover Results\160Will_Column Hinges.xlsx")

print("=" * 80)
print("COLUMN IMPORT TEST")
print("=" * 80)

# Test parser first
print("\n1. Testing Parser...")
parser = PushoverColumnParser(column_file)

directions = parser.get_available_directions()
print(f"   Directions: {directions}")

columns = parser.get_columns()
print(f"   Columns ({len(columns)}): {columns}")

x_cases = parser.get_output_cases('X')
print(f"   X cases ({len(x_cases)}): {x_cases[:3]}...")

# Parse X direction
x_results = parser.parse('X')
print(f"\n   X Results:")
print(f"   - R2 rotations: {x_results.rotations_r2.shape if x_results.rotations_r2 is not None else 'None'}")
print(f"   - R3 rotations: {x_results.rotations_r3.shape if x_results.rotations_r3 is not None else 'None'}")

if x_results.rotations_r2 is not None:
    print(f"\n   R2 sample:")
    print(x_results.rotations_r2.head(3))

# Test importer
print("\n2. Testing Importer...")
session = get_session()

try:
    # Get or create test project
    project = session.query(Project).filter(Project.name == "TEST_COLUMN").first()
    if not project:
        project = Project(name="TEST_COLUMN", description="Test column import")
        session.add(project)
        session.flush()

    # Get or create result set
    result_set = session.query(ResultSet).filter(
        ResultSet.project_id == project.id,
        ResultSet.name == "TEST_PUSH"
    ).first()

    if not result_set:
        result_set = ResultSet(
            project_id=project.id,
            name="TEST_PUSH",
            analysis_type="Pushover"
        )
        session.add(result_set)
        session.flush()

    print(f"   Project ID: {project.id}")
    print(f"   Result Set ID: {result_set.id}")

    # Create importer
    importer = PushoverColumnImporter(
        project_id=project.id,
        session=session,
        result_set_id=result_set.id,
        file_path=column_file,
        selected_load_cases_x=x_cases,
        selected_load_cases_y=[],
    )

    print(f"\n   Importing...")
    stats = importer.import_all()

    print(f"\n   Import Stats:")
    print(f"   - X R2 rotations: {stats.get('x_r2_rotations', 0)}")
    print(f"   - X R3 rotations: {stats.get('x_r3_rotations', 0)}")

    # Check database
    from database.models import ColumnRotation, ElementResultsCache

    rotation_count = session.query(ColumnRotation).filter(
        ColumnRotation.load_case_id.in_([lc.id for lc in importer.load_cases_cache.values()])
    ).count()

    cache_count = session.query(ElementResultsCache).filter(
        ElementResultsCache.result_set_id == result_set.id,
        ElementResultsCache.result_type.in_(['ColumnRotations_R2', 'ColumnRotations_R3'])
    ).count()

    print(f"\n   Database Verification:")
    print(f"   - ColumnRotation records: {rotation_count}")
    print(f"   - Cache entries: {cache_count}")

    session.rollback()  # Don't save test data
    print(f"\n   ✓ Test completed (rolled back)")

except Exception as e:
    session.rollback()
    print(f"\n   ✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    session.close()

print("\n" + "=" * 80)
