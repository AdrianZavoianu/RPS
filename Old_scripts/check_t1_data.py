"""Check what pushover data exists in T1 project."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, ResultSet, ElementResultsCache, GlobalResultsCache

# Find T1 database
db_paths = list(Path('data/projects').glob('**/t1.db'))
if not db_paths:
    db_paths = list(Path('data/projects').glob('**/T1.db'))

if not db_paths:
    print("[ERROR] T1 database not found!")
    print("\nAvailable project folders:")
    for folder in Path('data/projects').iterdir():
        if folder.is_dir():
            print(f"  - {folder.name}")
    exit(1)

db_path = db_paths[0]
print(f"Found T1 database: {db_path}")
print("=" * 80)

engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Get all result sets
result_sets = session.query(ResultSet).all()

print(f"\nFound {len(result_sets)} result set(s):")
for rs in result_sets:
    print(f"  - {rs.name} (ID: {rs.id}, Type: {rs.analysis_type})")

# Get pushover result sets
pushover_sets = [rs for rs in result_sets if rs.analysis_type == "Pushover"]

if not pushover_sets:
    print("\n[ERROR] No pushover result sets found in T1!")
    session.close()
    exit(1)

# Check data for first pushover set
rs = pushover_sets[0]
print(f"\n{'=' * 80}")
print(f"Checking Result Set: {rs.name} (ID: {rs.id})")
print(f"{'=' * 80}")

# Check global cache
print("\n1. GLOBAL RESULTS:")
print("-" * 80)
global_cache = session.query(GlobalResultsCache).filter(
    GlobalResultsCache.result_set_id == rs.id
).all()

global_types = {}
for entry in global_cache:
    base_type = entry.result_type.split('_')[0] if '_' in entry.result_type else entry.result_type
    if base_type not in global_types:
        global_types[base_type] = set()
    if '_' in entry.result_type:
        global_types[base_type].add(entry.result_type.split('_')[-1])

if global_types:
    for result_type, dirs in sorted(global_types.items()):
        if dirs:
            print(f"  {result_type}: {', '.join(sorted(dirs))}")
        else:
            print(f"  {result_type}")
else:
    print("  [No global results]")

# Check element cache
print("\n2. ELEMENT RESULTS:")
print("-" * 80)
elem_cache = session.query(ElementResultsCache).filter(
    ElementResultsCache.result_set_id == rs.id
).all()

elem_types = {}
for entry in elem_cache:
    if entry.result_type not in elem_types:
        elem_types[entry.result_type] = set()
    elem_types[entry.result_type].add(entry.element_id)

if elem_types:
    for result_type in sorted(elem_types.keys()):
        element_count = len(elem_types[result_type])
        print(f"  {result_type}: {element_count} elements")
else:
    print("  [No element results]")

# Check specifically for column data
print("\n3. COLUMN-SPECIFIC CHECK:")
print("-" * 80)
column_types = [rt for rt in elem_types.keys() if 'Column' in rt]
if column_types:
    for rt in column_types:
        print(f"  {rt}: {len(elem_types[rt])} elements")
else:
    print("  [No column data found]")

has_column_shears = any('ColumnShears' in rt for rt in elem_types.keys())
has_column_rotations = any('ColumnRotations' in rt for rt in elem_types.keys())

print(f"\n  Has ColumnShears data: {'YES' if has_column_shears else 'NO'}")
print(f"  Has ColumnRotations data: {'YES' if has_column_rotations else 'NO'}")

session.close()
