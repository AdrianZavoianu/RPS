"""Check if column shear data exists in pushover results."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, ResultSet, ElementResultsCache

# Connect to 711 project database
db_path = Path(r"data\projects\711\711.db")

engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Get pushover result set
result_set = session.query(ResultSet).filter(ResultSet.analysis_type == "Pushover").first()

print("Checking for column shear data in pushover results...")
print("=" * 80)
print(f"Result Set: {result_set.name} (ID: {result_set.id})")
print("=" * 80)

# Get all element cache entries for this result set
elem_cache = session.query(ElementResultsCache).filter(
    ElementResultsCache.result_set_id == result_set.id
).all()

# Group by result_type
result_types = {}
for entry in elem_cache:
    if entry.result_type not in result_types:
        result_types[entry.result_type] = set()
    result_types[entry.result_type].add(entry.element_id)

print("\nElement Result Types Found:")
print("-" * 80)
for result_type in sorted(result_types.keys()):
    element_count = len(result_types[result_type])
    print(f"  {result_type}: {element_count} elements")

# Check specifically for column shears
column_shear_types = [rt for rt in result_types.keys() if 'ColumnShear' in rt or 'Column' in rt and 'Shear' in rt]

print("\nColumn-related Result Types:")
print("-" * 80)
if column_shear_types:
    for rt in column_shear_types:
        print(f"  {rt}: {len(result_types[rt])} elements")
else:
    print("  [No column shear data found]")

# Check what other column types exist
column_types = [rt for rt in result_types.keys() if 'Column' in rt]
print("\nAll Column Result Types:")
print("-" * 80)
for rt in column_types:
    print(f"  {rt}: {len(result_types[rt])} elements")

session.close()
