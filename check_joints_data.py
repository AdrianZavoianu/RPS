"""
Quick check for joints data in database
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from database.base import get_project_session
from database.models import JointResultsCache, ResultSet

# Get all projects
projects_dir = Path("data/projects")
if not projects_dir.exists():
    print(f"[FAIL] Projects directory not found: {projects_dir}")
    sys.exit(1)

project_dbs = list(projects_dir.glob("*/*.db"))
print(f"Found {len(project_dbs)} project databases\n")

for db_path in project_dbs:
    project_name = db_path.parent.name

    session = get_project_session(db_path)

    # Get result sets
    result_sets = session.query(ResultSet).all()

    if not result_sets:
        continue

    print(f"=== Project: {project_name} ===")

    for rs in result_sets:
        print(f"\nResult Set: {rs.name} (ID={rs.id}, Type={rs.analysis_type})")

        # Check for joint results
        joint_results = session.query(JointResultsCache).filter(
            JointResultsCache.result_set_id == rs.id
        ).all()

        if joint_results:
            # Group by result type
            by_type = {}
            for jr in joint_results:
                result_type = jr.result_type
                if result_type not in by_type:
                    by_type[result_type] = 0
                by_type[result_type] += 1

            print(f"  Joint Results:")
            for result_type, count in sorted(by_type.items()):
                print(f"    - {result_type}: {count} entries")
        else:
            print(f"  No joint results found")

    session.close()
    print()
