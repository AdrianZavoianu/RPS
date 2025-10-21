"""Import data from Excel files into database."""

from typing import Optional
from pathlib import Path

from database.base import get_session
from database.repository import (
    ProjectRepository,
    LoadCaseRepository,
    StoryRepository,
    ResultRepository,
)
from database.models import StoryDrift, StoryAcceleration, StoryForce

from .excel_parser import ExcelParser
from .result_processor import ResultProcessor


class DataImporter:
    """Import structural analysis results from Excel into database."""

    def __init__(self, file_path: str, project_name: str, analysis_type: Optional[str] = None):
        """Initialize importer.

        Args:
            file_path: Path to Excel file
            project_name: Name of the project
            analysis_type: Optional analysis type (e.g., 'DERG', 'MCR')
        """
        self.file_path = Path(file_path)
        self.project_name = project_name
        self.analysis_type = analysis_type or "General"
        self.parser = ExcelParser(file_path)

    def import_all(self) -> dict:
        """Import all available data from Excel file.

        Returns:
            Dictionary with import statistics
        """
        session = get_session()
        stats = {
            "project": None,
            "load_cases": 0,
            "stories": 0,
            "drifts": 0,
            "accelerations": 0,
            "forces": 0,
            "errors": [],
        }

        try:
            # Create or get project
            project_repo = ProjectRepository(session)
            project = project_repo.get_by_name(self.project_name)

            if not project:
                project = project_repo.create(
                    name=self.project_name,
                    description=f"Imported from {self.file_path.name}",
                )
            stats["project"] = project.name

            # Import story drifts if available
            if self.parser.validate_sheet_exists("Story Drifts"):
                drift_stats = self._import_story_drifts(session, project.id)
                stats.update(drift_stats)

            # Import story accelerations if available
            if self.parser.validate_sheet_exists("Story Accelerations"):
                accel_stats = self._import_story_accelerations(session, project.id)
                stats["accelerations"] += accel_stats.get("accelerations", 0)

            # Import story forces if available
            if self.parser.validate_sheet_exists("Story Forces"):
                force_stats = self._import_story_forces(session, project.id)
                stats["forces"] += force_stats.get("forces", 0)

            session.commit()

        except Exception as e:
            session.rollback()
            stats["errors"].append(str(e))
            raise
        finally:
            session.close()

        return stats

    def _import_story_drifts(self, session, project_id: int) -> dict:
        """Import story drift data."""
        stats = {"load_cases": 0, "stories": 0, "drifts": 0}

        try:
            # Parse data
            df, load_cases, stories = self.parser.get_story_drifts()

            # Create/get load cases
            case_repo = LoadCaseRepository(session)
            story_repo = StoryRepository(session)
            result_repo = ResultRepository(session)

            # Process each direction
            for direction in ["X", "Y"]:
                # Process data
                processed = ResultProcessor.process_story_drifts(
                    df, load_cases, stories, direction
                )

                # Store in database
                drift_objects = []

                for _, row in processed.iterrows():
                    # Get or create story
                    story = story_repo.get_or_create(
                        project_id=project_id,
                        name=row["Story"],
                        sort_order=stories.index(row["Story"]) if row["Story"] in stories else None,
                    )

                    # Get or create load case
                    load_case = case_repo.get_or_create(
                        project_id=project_id,
                        name=row["LoadCase"],
                        case_type="Time History",
                    )

                    # Create drift object
                    drift = StoryDrift(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        direction=direction,
                        drift=row["Drift"],
                        max_drift=row.get("MaxDrift"),
                        min_drift=row.get("MinDrift"),
                    )
                    drift_objects.append(drift)

                # Bulk insert
                result_repo.bulk_create_drifts(drift_objects)
                stats["drifts"] += len(drift_objects)

            stats["load_cases"] = len(load_cases)
            stats["stories"] = len(stories)

        except Exception as e:
            raise ValueError(f"Error importing story drifts: {e}")

        return stats

    def _import_story_accelerations(self, session, project_id: int) -> dict:
        """Import story acceleration data."""
        stats = {"accelerations": 0}

        try:
            # Parse data
            df, load_cases, stories = self.parser.get_story_accelerations()

            case_repo = LoadCaseRepository(session)
            story_repo = StoryRepository(session)
            result_repo = ResultRepository(session)

            # Process each direction
            for direction in ["UX", "UY"]:
                processed = ResultProcessor.process_story_accelerations(
                    df, load_cases, stories, direction
                )

                accel_objects = []

                for _, row in processed.iterrows():
                    story = story_repo.get_or_create(
                        project_id=project_id, name=row["Story"]
                    )
                    load_case = case_repo.get_or_create(
                        project_id=project_id, name=row["LoadCase"]
                    )

                    accel = StoryAcceleration(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        direction=direction,
                        acceleration=row["Acceleration"],
                        max_acceleration=row.get("MaxAcceleration"),
                        min_acceleration=row.get("MinAcceleration"),
                    )
                    accel_objects.append(accel)

                result_repo.bulk_create_accelerations(accel_objects)
                stats["accelerations"] += len(accel_objects)

        except Exception as e:
            raise ValueError(f"Error importing story accelerations: {e}")

        return stats

    def _import_story_forces(self, session, project_id: int) -> dict:
        """Import story force data."""
        stats = {"forces": 0}

        try:
            # Parse data
            df, load_cases, stories = self.parser.get_story_forces()

            case_repo = LoadCaseRepository(session)
            story_repo = StoryRepository(session)
            result_repo = ResultRepository(session)

            # Process each direction
            for direction in ["VX", "VY"]:
                processed = ResultProcessor.process_story_forces(
                    df, load_cases, stories, direction
                )

                force_objects = []

                for _, row in processed.iterrows():
                    story = story_repo.get_or_create(
                        project_id=project_id, name=row["Story"]
                    )
                    load_case = case_repo.get_or_create(
                        project_id=project_id, name=row["LoadCase"]
                    )

                    force = StoryForce(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        direction=direction,
                        location=row.get("Location", "Bottom"),
                        force=row["Force"],
                        max_force=row.get("MaxForce"),
                        min_force=row.get("MinForce"),
                    )
                    force_objects.append(force)

                result_repo.bulk_create_forces(force_objects)
                stats["forces"] += len(force_objects)

        except Exception as e:
            raise ValueError(f"Error importing story forces: {e}")

        return stats
