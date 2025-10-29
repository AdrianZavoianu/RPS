"""Migration script to rename project databases from project.db to {slug}.db.

This script:
1. Finds all project folders with project.db files
2. Renames them to {slug}.db
3. Updates the catalog to reflect the new paths

IMPORTANT: Close the RPS application before running this script to avoid
file locking issues on Windows.

Run this once to migrate existing projects to the new naming scheme.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.catalog_base import init_catalog_db, get_catalog_session
from database.catalog_repository import CatalogProjectRepository
import shutil

def migrate_database_names():
    """Migrate all project databases from project.db to {slug}.db."""
    print(f"\n{'='*60}")
    print("Database Name Migration")
    print(f"{'='*60}\n")

    print("IMPORTANT: Make sure the RPS application is closed before running this script!\n")
    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("Migration cancelled.")
        return

    print()

    # Initialize catalog
    init_catalog_db()
    session = get_catalog_session()
    repo = CatalogProjectRepository(session)

    # Get all projects
    projects = repo.get_all()
    print(f"Found {len(projects)} projects in catalog\n")

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    for project in projects:
        old_db_path = Path(project.db_path)
        project_folder = old_db_path.parent
        slug = project.slug

        # New database path
        new_db_path = project_folder / f"{slug}.db"

        print(f"Project: {project.name} (slug: {slug})")
        print(f"  Old path: {old_db_path}")
        print(f"  New path: {new_db_path}")

        # Check if old database exists
        if not old_db_path.exists():
            print(f"  SKIP: Old database doesn't exist")
            skipped_count += 1
            print()
            continue

        # Check if already renamed
        if old_db_path == new_db_path:
            print(f"  SKIP: Database already using new naming scheme")
            skipped_count += 1
            print()
            continue

        # Check if new database already exists
        if new_db_path.exists():
            print(f"  ERROR: New database path already exists!")
            error_count += 1
            print()
            continue

        try:
            # Rename the database file
            shutil.move(str(old_db_path), str(new_db_path))

            # Update catalog entry
            project.db_path = str(new_db_path)
            session.commit()

            print(f"  SUCCESS: Renamed to {new_db_path.name}")
            migrated_count += 1

        except Exception as e:
            error_msg = str(e)
            if "being used by another process" in error_msg:
                print(f"  ERROR: Database file is locked (is the application still running?)")
            else:
                print(f"  ERROR: {e}")
            error_count += 1
            session.rollback()

        print()

    session.close()

    # Summary
    print(f"\n{'='*60}")
    print("Migration Summary")
    print(f"{'='*60}")
    print(f"Total projects: {len(projects)}")
    print(f"Migrated: {migrated_count}")
    print(f"Skipped: {skipped_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*60}\n")

    if error_count > 0:
        print("WARNING: Some projects failed to migrate. Review errors above.")
    elif migrated_count > 0:
        print("SUCCESS: All databases migrated successfully!")
    else:
        print("INFO: No databases needed migration.")

if __name__ == "__main__":
    migrate_database_names()
