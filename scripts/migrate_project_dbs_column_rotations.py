"""Migrate existing project databases to add column_rotations table.

Run this script to add the column_rotations table to all existing project databases
that were created before this feature was added.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from sqlalchemy import create_engine, text, inspect
from database.models import Base, ColumnRotation

def check_table_exists(engine, table_name):
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def migrate_project_db(db_path: Path):
    """Add column_rotations table to a project database if it doesn't exist."""
    engine = create_engine(f"sqlite:///{db_path}")

    # Check if table already exists
    if check_table_exists(engine, "column_rotations"):
        print(f"  [OK] Already has column_rotations table")
        return False

    # Create only the column_rotations table
    ColumnRotation.__table__.create(bind=engine, checkfirst=True)
    print(f"  [OK] Added column_rotations table")
    return True

def main():
    """Migrate all project databases."""
    projects_dir = Path(__file__).parent.parent / "data" / "projects"

    if not projects_dir.exists():
        print(f"Projects directory not found: {projects_dir}")
        return

    print("Migrating Project Databases - Adding column_rotations Table")
    print("=" * 80)

    migrated_count = 0
    skipped_count = 0

    # Find all project databases
    for project_folder in projects_dir.iterdir():
        if not project_folder.is_dir():
            continue

        # Look for .db file with same name as folder
        db_file = project_folder / f"{project_folder.name}.db"
        if not db_file.exists():
            # Try old naming convention
            db_file = project_folder / "project.db"
            if not db_file.exists():
                continue

        print(f"\n{project_folder.name}:")
        print(f"  Database: {db_file.name}")

        try:
            if migrate_project_db(db_file):
                migrated_count += 1
            else:
                skipped_count += 1
        except Exception as e:
            print(f"  [ERROR] {e}")

    print("\n" + "=" * 80)
    print(f"Migration Complete:")
    print(f"  - Migrated: {migrated_count} projects")
    print(f"  - Skipped: {skipped_count} projects (already up to date)")
    print("\nYou can now import Column Rotation data from 'Fiber Hinge States' sheets.")

if __name__ == "__main__":
    main()
