"""Test the _has_data_for helper method logic for pushover tree structure."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, ResultSet, GlobalResultsCache, ElementResultsCache

# Connect to 711 project database
db_path = Path(r"data\projects\711\711.db")

engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Get pushover result set
result_set = session.query(ResultSet).filter(ResultSet.analysis_type == "Pushover").first()

print("Testing _has_data_for logic for 711Vic pushover results...")
print("=" * 80)
print(f"Result Set: {result_set.name} (ID: {result_set.id})")
print("=" * 80)

# Test the _has_data_for logic (this mimics what the tree browser does)
def has_data_for(result_set_id: int, result_type: str) -> bool:
    """Check if data exists in cache for a result type.

    This mimics the _has_data_for method in results_tree_browser.py
    """
    # Check global cache first
    global_entry = session.query(GlobalResultsCache).filter(
        GlobalResultsCache.result_set_id == result_set_id,
        GlobalResultsCache.result_type.like(f"{result_type}%")
    ).first()

    if global_entry:
        return True

    # Check element cache
    elem_entry = session.query(ElementResultsCache).filter(
        ElementResultsCache.result_set_id == result_set_id,
        ElementResultsCache.result_type.like(f"{result_type}%")
    ).first()

    return elem_entry is not None

print("\nChecking which sections would be shown:")
print("-" * 80)

# Test Walls section
has_wall_shears = has_data_for(result_set.id, "WallShears")
has_quad_rotations = has_data_for(result_set.id, "QuadRotations")
show_walls = has_wall_shears or has_quad_rotations

print(f"Walls Section:")
print(f"  - Wall Shears: {'YES' if has_wall_shears else 'NO'}")
print(f"  - Quad Rotations: {'YES' if has_quad_rotations else 'NO'}")
print(f"  > Show Walls Section: {'YES' if show_walls else 'NO'}")

# Test Columns section
has_column_rotations = has_data_for(result_set.id, "ColumnRotations")
show_columns = has_column_rotations

print(f"\nColumns Section:")
print(f"  - Column Rotations: {'YES' if has_column_rotations else 'NO'}")
print(f"  > Show Columns Section: {'YES' if show_columns else 'NO'}")

# Test Beams section
has_beam_rotations = has_data_for(result_set.id, "BeamRotations")
show_beams = has_beam_rotations

print(f"\nBeams Section:")
print(f"  - Beam Rotations: {'YES' if has_beam_rotations else 'NO'}")
print(f"  > Show Beams Section: {'YES' if show_beams else 'NO'}")

# Test Global Results
has_drifts = has_data_for(result_set.id, "Drifts")
has_forces = has_data_for(result_set.id, "Forces")
has_displacements = has_data_for(result_set.id, "Displacements")

print(f"\nGlobal Results:")
print(f"  - Story Drifts: {'YES' if has_drifts else 'NO'}")
print(f"  - Story Forces: {'YES' if has_forces else 'NO'}")
print(f"  - Floor Displacements: {'YES' if has_displacements else 'NO'}")

print("\n" + "=" * 80)
print("Expected Tree Structure:")
print("=" * 80)
print("""
DES (Pushover Result Set)
  +- Curves
  |   +- X Direction
  |   |   +- ... (if curves imported)
  |   +- Y Direction
  |       +- ... (if curves imported)
  +- Global Results
  |   +- Story Drifts
  |   |   +- X
  |   |   +- Y
  |   +- Story Forces
  |   |   +- X
  |   |   +- Y
  |   +- Floor Displacements
  |       +- X
  |       +- Y
  +- Elements
      +- Columns
      |   +- Rotations
      |       +- C1
      |       |   +- R2
      |       |   +- R3
      |       +- ... (84 total columns)
      +- Beams
          +- Rotations
              +- B1
              +- ... (18 total beams)
""")

session.close()
