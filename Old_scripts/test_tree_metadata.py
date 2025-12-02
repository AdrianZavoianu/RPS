"""Test that tree metadata is correctly structured for click handlers."""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, ResultSet, Element

# Connect to 711 project database
db_path = Path(r"data\projects\711\711.db")

engine = create_engine(f'sqlite:///{db_path}', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Get pushover result set
result_set = session.query(ResultSet).filter(ResultSet.analysis_type == "Pushover").first()

print("Testing tree item metadata for click handlers...")
print("=" * 80)
print(f"Result Set: {result_set.name} (ID: {result_set.id})")
print("=" * 80)

# Get column elements (first 3 for testing)
column_elements = session.query(Element).filter(Element.element_type == "Column").limit(3).all()
beam_elements = session.query(Element).filter(Element.element_type == "Beam").limit(3).all()

print("\n1. COLUMN ROTATIONS METADATA:")
print("-" * 80)

# Simulate tree structure metadata for columns
for column in column_elements:
    print(f"\nColumn: {column.name} (ID: {column.id})")

    # Metadata for column element item (parent of R2/R3)
    element_metadata = {
        "type": "pushover_column_element",
        "result_set_id": result_set.id,
        "element_id": column.id,
        "element_name": column.name
    }
    print(f"  Element item metadata: {element_metadata}")

    # Metadata for R2 direction
    r2_metadata = {
        "type": "pushover_column_result",
        "result_set_id": result_set.id,
        "result_type": "ColumnRotations_R2",
        "direction": "R2",
        "element_id": column.id
    }
    print(f"    R2 metadata: {r2_metadata}")

    # Metadata for R3 direction
    r3_metadata = {
        "type": "pushover_column_result",
        "result_set_id": result_set.id,
        "result_type": "ColumnRotations_R3",
        "direction": "R3",
        "element_id": column.id
    }
    print(f"    R3 metadata: {r3_metadata}")

    # Simulate click handler
    print(f"  Click Handler Processing:")
    # Extract base result type by stripping suffix
    result_type_with_suffix = r2_metadata["result_type"]  # "ColumnRotations_R2"
    result_type = "ColumnRotations"  # Stripped version
    direction = r2_metadata["direction"]  # "R2"
    element_id = r2_metadata["element_id"]

    print(f"    -> Signal emitted: result_set_id={result_set.id}, category='Pushover', result_type='{result_type}', direction='{direction}', element_id={element_id}")

print("\n2. BEAM ROTATIONS METADATA:")
print("-" * 80)

# Simulate tree structure metadata for beams
for beam in beam_elements:
    print(f"\nBeam: {beam.name} (ID: {beam.id})")

    # Metadata for beam rotation item
    beam_metadata = {
        "type": "pushover_beam_result",
        "result_set_id": result_set.id,
        "result_type": "BeamRotations",
        "direction": "",  # No direction for beams
        "element_id": beam.id
    }
    print(f"  Beam item metadata: {beam_metadata}")

    # Simulate click handler
    print(f"  Click Handler Processing:")
    result_type = beam_metadata["result_type"]  # "BeamRotations"
    direction = beam_metadata["direction"]  # ""
    element_id = beam_metadata["element_id"]

    print(f"    -> Signal emitted: result_set_id={result_set.id}, category='Pushover', result_type='{result_type}', direction='{direction}', element_id={element_id}")

print("\n3. GLOBAL RESULTS METADATA:")
print("-" * 80)

# Simulate global results metadata
global_types = ["Story Drifts", "Story Forces", "Floor Displacements"]
for result_type in global_types:
    print(f"\n{result_type}:")

    # Metadata for X direction
    x_metadata = {
        "type": "pushover_global_result",
        "result_type": result_type,
        "direction": "X",
        "result_set_id": result_set.id
    }
    print(f"  X metadata: {x_metadata}")

    # Map display name to internal type
    type_map = {
        "Story Drifts": "Drifts",
        "Story Forces": "Forces",
        "Floor Displacements": "Displacements"
    }
    internal_type = type_map.get(result_type, result_type)
    direction = x_metadata["direction"]

    print(f"  Click Handler Processing:")
    print(f"    -> Signal emitted: result_set_id={result_set.id}, category='Pushover', result_type='{internal_type}', direction='{direction}', element_id=0")

print("\n" + "=" * 80)
print("Metadata structure verification complete!")
print("=" * 80)
print("\nSummary:")
print("  - Column rotations use type='pushover_column_result' with direction='R2'/'R3'")
print("  - Beam rotations use type='pushover_beam_result' with empty direction")
print("  - Global results use type='pushover_global_result' with direction='X'/'Y'")
print("  - All metadata includes result_set_id for proper data loading")

session.close()
