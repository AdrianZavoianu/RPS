"""Import data from Excel files into database."""

from typing import Optional, List, Callable
from pathlib import Path

from sqlalchemy.orm import Session

from database.base import get_session
from database.repository import (
    ProjectRepository,
    LoadCaseRepository,
    StoryRepository,
    ResultRepository,
    ResultSetRepository,
    ResultCategoryRepository,
    CacheRepository,
    AbsoluteMaxMinDriftRepository,
)
from database.models import StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement

from .excel_parser import ExcelParser
from .result_processor import ResultProcessor


class DataImporter:
    """Import structural analysis results from Excel into database."""

    def __init__(
        self,
        file_path: str,
        project_name: str,
        result_set_name: str,
        analysis_type: Optional[str] = None,
        result_types: Optional[List[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
    ):
        """Initialize importer.

        Args:
            file_path: Path to Excel file
            project_name: Name of the project
            result_set_name: Name for this result set (e.g., DES, MCE, SLE)
            analysis_type: Optional analysis type (e.g., 'DERG', 'MCR')
        """
        self.file_path = Path(file_path)
        self.project_name = project_name
        self.result_set_name = result_set_name
        self.analysis_type = analysis_type or "General"
        self.parser = ExcelParser(file_path)
        self.result_types = {rt.strip().lower() for rt in result_types} if result_types else None
        self._session_factory = session_factory or get_session

    def import_all(self) -> dict:
        """Import all available data from Excel file.

        Returns:
            Dictionary with import statistics
        """
        session = self._session_factory()
        stats = {
            "project": None,
            "load_cases": 0,
            "stories": 0,
            "drifts": 0,
            "accelerations": 0,
            "forces": 0,
            "displacements": 0,
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

            # Create or get result set
            result_set_repo = ResultSetRepository(session)
            result_set = result_set_repo.get_or_create(
                project_id=project.id,
                name=self.result_set_name,
            )

            # Create result category (Envelopes → Global)
            category_repo = ResultCategoryRepository(session)
            result_category = category_repo.get_or_create(
                result_set_id=result_set.id,
                category_name="Envelopes",
                category_type="Global",
            )

            # Store for use in import methods
            self.result_category_id = result_category.id
            self.result_set_id = result_set.id

            # Import story drifts if available
            if self._should_import("Story Drifts") and self.parser.validate_sheet_exists("Story Drifts"):
                drift_stats = self._import_story_drifts(session, project.id)
                stats["load_cases"] += drift_stats.get("load_cases", 0)
                stats["stories"] += drift_stats.get("stories", 0)
                stats["drifts"] += drift_stats.get("drifts", 0)

            # Import story accelerations if available
            if self._should_import("Story Accelerations") and self.parser.validate_sheet_exists("Story Accelerations"):
                accel_stats = self._import_story_accelerations(session, project.id)
                stats["accelerations"] += accel_stats.get("accelerations", 0)

            # Import story forces if available
            if self._should_import("Story Forces") and self.parser.validate_sheet_exists("Story Forces"):
                force_stats = self._import_story_forces(session, project.id)
                stats["forces"] += force_stats.get("forces", 0)
            # Import joint displacements if available
            if self._should_import("Joint Displacements (Global)") and self.parser.validate_sheet_exists("Joint DisplacementsG"):
                disp_stats = self._import_joint_displacements(session, project.id)
                stats["displacements"] += disp_stats.get("displacements", 0)

            # Generate cache for fast display after all imports
            self._generate_cache(session, project.id, self.result_set_id)

            session.commit()

        except Exception as e:
            session.rollback()
            stats["errors"].append(str(e))
            raise
        finally:
            session.close()

        return stats

    def _should_import(self, result_label: str) -> bool:
        """Return True when the given result type should be imported."""
        if not self.result_types:
            return True
        return result_label.strip().lower() in self.result_types

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
                        result_category_id=self.result_category_id,
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
                        result_category_id=self.result_category_id,
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
                        result_category_id=self.result_category_id,
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

    def _import_joint_displacements(self, session, project_id: int) -> dict:
        """Import joint displacement data (global story displacements)."""
        stats = {"displacements": 0}

        try:
            df, load_cases, stories = self.parser.get_joint_displacements()

            if df.empty:
                return stats

            case_repo = LoadCaseRepository(session)
            story_repo = StoryRepository(session)
            result_repo = ResultRepository(session)

            for direction in ["Ux", "Uy"]:
                processed = ResultProcessor.process_joint_displacements(
                    df, load_cases, stories, direction
                )

                displacement_objects = []

                for _, row in processed.iterrows():
                    story = story_repo.get_or_create(
                        project_id=project_id,
                        name=row["Story"],
                        sort_order=stories.index(row["Story"]) if row["Story"] in stories else None,
                    )

                    load_case = case_repo.get_or_create(
                        project_id=project_id,
                        name=row["LoadCase"],
                        case_type="Time History",
                    )

                    displacement = StoryDisplacement(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=row["Direction"],
                        displacement=row["Displacement"],
                        max_displacement=row.get("MaxDisplacement"),
                        min_displacement=row.get("MinDisplacement"),
                    )
                    displacement_objects.append(displacement)

                result_repo.bulk_create_displacements(displacement_objects)
                stats["displacements"] += len(displacement_objects)

        except Exception as e:
            raise ValueError(f"Error importing joint displacements: {e}")

        return stats

    def _generate_cache(self, session, project_id: int, result_set_id: int):
        """Generate wide-format cache tables for fast tabular display."""
        story_repo = StoryRepository(session)
        cache_repo = CacheRepository(session)
        result_repo = ResultRepository(session)
        abs_repo = AbsoluteMaxMinDriftRepository(session)

        # Get all stories for this project
        stories = story_repo.get_by_project(project_id)

        # Generate cache for each result type
        self._cache_drifts(session, project_id, result_set_id, stories, cache_repo, result_repo)
        self._cache_accelerations(session, project_id, result_set_id, stories, cache_repo, result_repo)
        self._cache_forces(session, project_id, result_set_id, stories, cache_repo, result_repo)
        self._cache_displacements(session, project_id, result_set_id, stories, cache_repo, result_repo)
        self._calculate_absolute_maxmin(session, project_id, result_set_id, abs_repo)
        self._cache_displacements(session, project_id, result_set_id, stories, cache_repo, result_repo)
        self._calculate_absolute_maxmin(session, project_id, result_set_id, abs_repo)
        self._cache_displacements(session, project_id, result_set_id, stories, cache_repo, result_repo)
        self._calculate_absolute_maxmin(session, project_id, result_set_id, abs_repo)

    def _cache_drifts(self, session, project_id: int, result_set_id: int, stories, cache_repo, result_repo):
        """Generate cache for story drifts."""
        from sqlalchemy import and_
        from database.models import StoryDrift, LoadCase, Story

        # Get all drifts for this project and result set
        drifts = (
            session.query(StoryDrift, LoadCase.name)
            .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
            .join(Story, StoryDrift.story_id == Story.id)
            .filter(Story.project_id == project_id)
            .filter(StoryDrift.result_category_id == self.result_category_id)
            .all()
        )

        # Group by story and build wide-format matrix
        story_matrices = {}
        for drift, load_case_name in drifts:
            story_id = drift.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}

            # Key format: LoadCase_Direction (e.g., TH01_X)
            key = f"{load_case_name}_{drift.direction}"
            story_matrices[story_id][key] = drift.drift

        # Upsert cache entries
        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Drifts",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
            )

    def _cache_accelerations(self, session, project_id: int, result_set_id: int, stories, cache_repo, result_repo):
        """Generate cache for story accelerations."""
        from database.models import StoryAcceleration, LoadCase, Story

        accels = (
            session.query(StoryAcceleration, LoadCase.name)
            .join(LoadCase, StoryAcceleration.load_case_id == LoadCase.id)
            .join(Story, StoryAcceleration.story_id == Story.id)
            .filter(Story.project_id == project_id)
            .filter(StoryAcceleration.result_category_id == self.result_category_id)
            .all()
        )

        story_matrices = {}
        for accel, load_case_name in accels:
            story_id = accel.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}

            key = f"{load_case_name}_{accel.direction}"
            story_matrices[story_id][key] = accel.acceleration

        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Accelerations",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
            )

    def _cache_forces(self, session, project_id: int, result_set_id: int, stories, cache_repo, result_repo):
        """Generate cache for story forces."""
        from database.models import StoryForce, LoadCase, Story

        forces = (
            session.query(StoryForce, LoadCase.name)
            .join(LoadCase, StoryForce.load_case_id == LoadCase.id)
            .join(Story, StoryForce.story_id == Story.id)
            .filter(Story.project_id == project_id)
            .filter(StoryForce.result_category_id == self.result_category_id)
            .all()
        )

        story_matrices = {}
        for force, load_case_name in forces:
            story_id = force.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}

            key = f"{load_case_name}_{force.direction}"
            story_matrices[story_id][key] = force.force

        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Forces",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
            )

    def _calculate_absolute_maxmin(self, session, project_id: int, result_set_id: int, abs_repo):
        """Compute and persist absolute max/min drifts per load case and direction."""
        from sqlalchemy import and_
        from database.models import StoryDrift, LoadCase, Story

        drifts = (
            session.query(StoryDrift, LoadCase, Story)
            .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
            .join(Story, StoryDrift.story_id == Story.id)
            .filter(
                and_(
                    Story.project_id == project_id,
                    StoryDrift.result_category_id == self.result_category_id,
                )
            )
            .all()
        )

        abs_repo.delete_by_result_set(project_id, result_set_id)

        if not drifts:
            return

        records = []
        for drift, load_case, story in drifts:
            max_val = drift.max_drift if drift.max_drift is not None else drift.drift
            min_val = drift.min_drift if drift.min_drift is not None else drift.drift

            if abs(max_val) >= abs(min_val):
                abs_val = abs(max_val)
                sign = "positive" if max_val >= 0 else "negative"
            else:
                abs_val = abs(min_val)
                sign = "positive" if min_val >= 0 else "negative"

            records.append({
                "project_id": project_id,
                "result_set_id": result_set_id,
                "story_id": story.id,
                "load_case_id": load_case.id,
                "direction": drift.direction,
                "absolute_max_drift": abs_val,
                "sign": sign,
                "original_max": max_val,
                "original_min": min_val,
            })

        if records:
            abs_repo.bulk_create(records)

    def _cache_displacements(self, session, project_id: int, result_set_id: int, stories, cache_repo, result_repo):
        """Generate cache for joint displacements (global)."""
        from database.models import StoryDisplacement, LoadCase, Story

        displacements = (
            session.query(StoryDisplacement, LoadCase.name)
            .join(LoadCase, StoryDisplacement.load_case_id == LoadCase.id)
            .join(Story, StoryDisplacement.story_id == Story.id)
            .filter(Story.project_id == project_id)
            .filter(StoryDisplacement.result_category_id == self.result_category_id)
            .all()
        )

        story_matrices = {}
        for displacement, load_case_name in displacements:
            story_id = displacement.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}

            key = f"{load_case_name}_{displacement.direction}"
            story_matrices[story_id][key] = displacement.displacement

        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Displacements",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
            )
