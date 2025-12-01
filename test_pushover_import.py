"""Test script for pushover curve import functionality."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.base import Base
from database.models import Project
from database.repository import ProjectRepository, PushoverCaseRepository
from processing.pushover_importer import PushoverImporter


def test_pushover_import():
    """Test pushover import with sample file."""

    # Create test database
    test_db_path = Path("data/test_pushover.db")
    test_db_path.parent.mkdir(exist_ok=True)

    engine = create_engine(f"sqlite:///{test_db_path}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create test project
        project_repo = ProjectRepository(session)
        project = project_repo.create(
            name="160Will_Test",
            description="Test project for pushover import"
        )
        project.analysis_type = 'Pushover'
        session.commit()

        print(f"Created project: {project.name} (ID: {project.id})")

        # Import pushover curves
        sample_file = Path("Old_scripts/ETPS/ETPS_Library/160Will_Pushover.xlsx")
        if not sample_file.exists():
            print(f"ERROR: Sample file not found: {sample_file}")
            return

        print(f"\nImporting pushover curves from: {sample_file}")

        importer = PushoverImporter(session)

        # Get available stories
        stories = importer.get_available_stories(sample_file)
        print(f"Available stories: {stories}")

        # Use first story as base (or specify manually)
        base_story = stories[0] if stories else "L01"
        print(f"Using base story: {base_story}")

        # Import curves
        stats = importer.import_pushover_file(
            file_path=sample_file,
            project_id=project.id,
            result_set_name="PUSH_XY",
            base_story=base_story,
            overwrite=True
        )

        print(f"\nImport completed successfully!")
        print(f"  Result Set: {stats['result_set_name']} (ID: {stats['result_set_id']})")
        print(f"  Curves imported: {stats['curves_imported']}")
        print(f"  Total data points: {stats['total_points']}")

        # Verify data
        pushover_repo = PushoverCaseRepository(session)
        cases = pushover_repo.get_by_result_set(stats['result_set_id'])

        print(f"\nVerification:")
        for case in cases:
            curve_points = pushover_repo.get_curve_data(case.id)
            print(f"  {case.name} ({case.direction}): {len(curve_points)} points")
            if curve_points:
                first = curve_points[0]
                last = curve_points[-1]
                print(f"    Step {first.step_number}: disp={first.displacement:.2f}mm, shear={first.base_shear:.2f}kN")
                print(f"    Step {last.step_number}: disp={last.displacement:.2f}mm, shear={last.base_shear:.2f}kN")

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

    print(f"\nTest database saved to: {test_db_path}")


if __name__ == "__main__":
    test_pushover_import()
