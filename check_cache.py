"""Diagnostic script to check what's in the cache after import."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import GlobalResultsCache, ElementResultsCache
from database.catalog_models import CatalogProject

# Get the catalog
catalog_db = Path("data/catalog.db")
if not catalog_db.exists():
    print("No catalog.db found")
    sys.exit(1)

catalog_engine = create_engine(f"sqlite:///{catalog_db}")
CatalogSession = sessionmaker(bind=catalog_engine)
catalog_session = CatalogSession()

projects = catalog_session.query(CatalogProject).all()
print(f"Found {len(projects)} project(s):\n")

for proj in projects:
    print(f"Project: {proj.name}")
    print(f"  Slug: {proj.slug}")

    # Build database path from slug
    db_path = Path(f"data/projects/{proj.slug}/{proj.slug}.db")
    print(f"  DB: {db_path}")

    # Connect to project database
    project_engine = create_engine(f"sqlite:///{db_path}")
    ProjectSession = sessionmaker(bind=project_engine)
    project_session = ProjectSession()

    # Check GlobalResultsCache
    global_types = project_session.query(GlobalResultsCache.result_type).distinct().all()
    print(f"\n  GlobalResultsCache types ({len(global_types)}):")
    for (rt,) in global_types:
        count = project_session.query(GlobalResultsCache).filter(
            GlobalResultsCache.result_type == rt
        ).count()
        print(f"    - {rt}: {count} entries")

    # Check ElementResultsCache
    element_types = project_session.query(ElementResultsCache.result_type).distinct().all()
    print(f"\n  ElementResultsCache types ({len(element_types)}):")
    for (rt,) in element_types:
        count = project_session.query(ElementResultsCache).filter(
            ElementResultsCache.result_type == rt
        ).count()
        print(f"    - {rt}: {count} entries")

    # Check raw tables
    from database.models import (
        StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement,
        WallShear, ColumnShear, ColumnAxial, ColumnRotation, BeamRotation, QuadRotation
    )

    print(f"\n  Raw table counts:")
    print(f"    - StoryDrift: {project_session.query(StoryDrift).count()}")
    print(f"    - StoryAcceleration: {project_session.query(StoryAcceleration).count()}")
    print(f"    - StoryForce: {project_session.query(StoryForce).count()}")
    print(f"    - StoryDisplacement: {project_session.query(StoryDisplacement).count()}")
    print(f"    - WallShear: {project_session.query(WallShear).count()}")
    print(f"    - ColumnShear: {project_session.query(ColumnShear).count()}")
    print(f"    - ColumnAxial: {project_session.query(ColumnAxial).count()}")
    print(f"    - ColumnRotation: {project_session.query(ColumnRotation).count()}")
    print(f"    - BeamRotation: {project_session.query(BeamRotation).count()}")
    print(f"    - QuadRotation: {project_session.query(QuadRotation).count()}")

    project_session.close()
    print("\n" + "="*60 + "\n")

catalog_session.close()
