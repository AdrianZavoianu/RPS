"""Import column shears for T1 project."""

import sys
from pathlib import Path

# Add src directory to Python path (same as main.py does)
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, ResultSet
from processing.pushover_column_shear_importer import PushoverColumnShearImporter
from processing.pushover_column_shear_parser import PushoverColumnShearParser

# Connect to T1 project database
db_path = Path(r"data\projects\t1\t1.db")

if not db_path.exists():
    print(f"[ERROR] T1 database not found: {db_path}")
    exit(1)

engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Get pushover result set
result_set = session.query(ResultSet).filter(ResultSet.analysis_type == "Pushover").first()

if not result_set:
    print("[ERROR] No pushover result set found in T1!")
    session.close()
    exit(1)

print(f"Importing column shears for result set: {result_set.name} (ID: {result_set.id})")
print("=" * 80)

# Find the Excel file
excel_files = list(Path('Typical Pushover Results').glob('*Push_DES_All.xlsx'))

if not excel_files:
    print("[ERROR] No pushover Excel files found in 'Typical Pushover Results'!")
    print("Looking for files matching pattern: *Push_DES_All.xlsx")
    session.close()
    exit(1)

file_path = excel_files[0]
print(f"Using file: {file_path.name}")

# Parse to get available load cases
parser = PushoverColumnShearParser(file_path)
directions = parser.get_available_directions()
print(f"\nAvailable directions: {directions}")

# Get load cases for X and Y
x_cases = parser.get_output_cases('X') if 'X' in directions else []
y_cases = parser.get_output_cases('Y') if 'Y' in directions else []

print(f"\nX direction load cases ({len(x_cases)}):")
for case in x_cases:
    print(f"  - {case}")

print(f"\nY direction load cases ({len(y_cases)}):")
for case in y_cases:
    print(f"  - {case}")

# Import column shears
print("\n" + "=" * 80)
print("Starting import...")
print("=" * 80)

importer = PushoverColumnShearImporter(
    project_id=result_set.project_id,
    session=session,
    result_set_id=result_set.id,
    file_path=file_path,
    selected_load_cases_x=x_cases,
    selected_load_cases_y=y_cases,
    progress_callback=lambda msg, curr, total: print(f"[{curr}/{total}] {msg}")
)

try:
    stats = importer.import_all()

    print("\n" + "=" * 80)
    print("IMPORT COMPLETE!")
    print("=" * 80)
    print(f"\nStatistics:")
    print(f"  X direction V2 shears: {stats.get('x_v2_shears', 0)}")
    print(f"  X direction V3 shears: {stats.get('x_v3_shears', 0)}")
    print(f"  Y direction V2 shears: {stats.get('y_v2_shears', 0)}")
    print(f"  Y direction V3 shears: {stats.get('y_v3_shears', 0)}")

    total_shears = sum([
        stats.get('x_v2_shears', 0),
        stats.get('x_v3_shears', 0),
        stats.get('y_v2_shears', 0),
        stats.get('y_v3_shears', 0)
    ])
    print(f"  Total shear records: {total_shears}")

except Exception as e:
    print(f"\n[ERROR] Import failed: {e}")
    import traceback
    traceback.print_exc()
finally:
    session.close()

print("\n" + "=" * 80)
print("Done! Now reload the project in the app to see Column Shears in the tree.")
