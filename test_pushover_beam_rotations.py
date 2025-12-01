"""Test the Beam Rotations views for pushover data."""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base, ResultSet
from processing.result_service.service import ResultDataService

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

print(f"Testing Beam Rotations for: {result_set.name} (ID: {result_set.id})")
print("=" * 80)

# Get project_id
project_id = result_set.project_id

# Initialize repositories
from database.repository import CacheRepository, StoryRepository, LoadCaseRepository, ElementCacheRepository, ElementRepository

cache_repo = CacheRepository(session)
story_repo = StoryRepository(session)
load_case_repo = LoadCaseRepository(session)
element_cache_repo = ElementCacheRepository(session)
element_repo = ElementRepository(session)

# Initialize result service
result_service = ResultDataService(
    project_id=project_id,
    cache_repo=cache_repo,
    story_repo=story_repo,
    load_case_repo=load_case_repo,
    element_cache_repo=element_cache_repo,
    element_repo=element_repo,
    session=session
)

# Test 1: All Beam Rotations (Plot view)
print("\n1. Testing All Beam Rotations (Plot view)...")
print("-" * 80)

df_max = result_service.get_all_beam_rotations_dataset(result_set.id, "Max")
df_min = result_service.get_all_beam_rotations_dataset(result_set.id, "Min")

if df_max is not None and not df_max.empty:
    print(f"Max dataset: {len(df_max)} rows")
    print(f"  Columns: {list(df_max.columns)}")
    print(f"  Unique elements: {df_max['Element'].nunique()}")
    print(f"  Unique stories: {df_max['Story'].nunique()}")
    print(f"  Unique load cases: {df_max['LoadCase'].nunique()}")
    print(f"\nSample data (first 5 rows):")
    print(df_max.head().to_string())
else:
    print("Max dataset: EMPTY")

print()

if df_min is not None and not df_min.empty:
    print(f"Min dataset: {len(df_min)} rows")
    print(f"  This should be empty for pushover data!")
else:
    print("Min dataset: EMPTY (as expected for pushover)")

# Test 2: Beam Rotations Table (Table view)
print("\n" + "=" * 80)
print("2. Testing Beam Rotations Table (Table view)...")
print("-" * 80)

df_table = result_service.get_beam_rotations_table_dataset(result_set.id)

if df_table is not None and not df_table.empty:
    print(f"Table dataset: {len(df_table)} rows x {len(df_table.columns)} columns")
    print(f"  Columns: {list(df_table.columns)[:10]}...")  # Show first 10
    print(f"\nSample data (first 3 rows, first 8 columns):")
    print(df_table.iloc[:3, :8].to_string())
else:
    print("Table dataset: EMPTY")

print("\n" + "=" * 80)
print("Expected behavior:")
print("  - Plot view: Max dataset should contain all rotation data points")
print("  - Plot view: Min dataset should be empty (pushover has no Max/Min split)")
print("  - Table view: Wide-format table with all beams and load cases")
print("  - Data should show beams x stories x load cases (R3 Plastic)")
print("=" * 80)

session.close()
