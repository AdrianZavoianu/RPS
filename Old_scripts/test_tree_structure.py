"""Test that the pushover tree structure is correctly built for 711 project."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, ResultSet, Element
from src.database.repository import CacheRepository, ElementCacheRepository

# Connect to 711 project database
db_path = Path(r"data\projects\711\711.db")

if not db_path.exists():
    print(f"[ERROR] Database not found: {db_path}")
    print("Please ensure the 711Vic project exists and has imported pushover results.")
    exit(1)

engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

print("Testing pushover tree structure for 711Vic project...")
print("=" * 80)

# Get all result sets
result_sets = session.query(ResultSet).all()

print(f"\nFound {len(result_sets)} result set(s):")
for rs in result_sets:
    print(f"  - {rs.name} (ID: {rs.id}, Type: {rs.analysis_type})")

# Get pushover result sets
pushover_sets = [rs for rs in result_sets if rs.analysis_type == "Pushover"]

if not pushover_sets:
    print("\n[ERROR] No pushover result sets found!")
    print("Please import pushover results for 711Vic first.")
    session.close()
    exit(1)

# Test with first pushover result set
rs = pushover_sets[0]
print(f"\n{'=' * 80}")
print(f"Testing Result Set: {rs.name} (ID: {rs.id})")
print(f"{'=' * 80}")

# Check cache for different result types
cache_repo = CacheRepository(session)
elem_cache_repo = ElementCacheRepository(session)

print("\n1. GLOBAL RESULTS CACHE:")
print("-" * 80)
# Query all cache entries for this result set
from src.database.models import GlobalResultsCache
global_cache = session.query(GlobalResultsCache).filter(
    GlobalResultsCache.result_set_id == rs.id
).all()
global_types = {}
for entry in global_cache:
    if entry.result_type not in global_types:
        global_types[entry.result_type] = []
    # Extract direction from result_type if present (e.g., Drifts_X -> X)
    if '_' in entry.result_type:
        direction = entry.result_type.split('_')[-1]
        base_type = '_'.join(entry.result_type.split('_')[:-1])
        if base_type not in global_types:
            global_types[base_type] = []
        global_types[base_type].append(direction)
    else:
        global_types[entry.result_type].append('')

if global_types:
    for result_type, directions in sorted(global_types.items()):
        unique_dirs = sorted(set(d for d in directions if d))
        if unique_dirs:
            print(f"  {result_type}: {', '.join(unique_dirs)}")
        else:
            print(f"  {result_type}")
else:
    print("  [No global results in cache]")

print("\n2. ELEMENT RESULTS CACHE:")
print("-" * 80)
# Query all element cache entries for this result set
from src.database.models import ElementResultsCache
elem_cache = session.query(ElementResultsCache).filter(
    ElementResultsCache.result_set_id == rs.id
).all()
elem_types = {}
for entry in elem_cache:
    if entry.result_type not in elem_types:
        elem_types[entry.result_type] = set()
    elem_types[entry.result_type].add(entry.element_id)

if elem_types:
    for result_type, element_ids in sorted(elem_types.items()):
        print(f"  {result_type}: {len(element_ids)} elements")

        # Get element details
        elements = session.query(Element).filter(Element.id.in_(element_ids)).all()
        elem_by_type = {}
        for elem in elements:
            if elem.element_type not in elem_by_type:
                elem_by_type[elem.element_type] = []
            elem_by_type[elem.element_type].append(elem.name)

        for elem_type, names in sorted(elem_by_type.items()):
            print(f"    - {elem_type}s: {', '.join(sorted(names)[:5])}{'...' if len(names) > 5 else ''}")
else:
    print("  [No element results in cache]")

print("\n3. ELEMENTS IN PROJECT:")
print("-" * 80)
all_elements = session.query(Element).all()
elem_by_type = {}
for elem in all_elements:
    if elem.element_type not in elem_by_type:
        elem_by_type[elem.element_type] = []
    elem_by_type[elem.element_type].append(elem.name)

for elem_type, names in sorted(elem_by_type.items()):
    print(f"  {elem_type}s ({len(names)}): {', '.join(sorted(names)[:5])}{'...' if len(names) > 5 else ''}")

print("\n" + "=" * 80)
print("Tree structure test complete!")
print("=" * 80)

session.close()
