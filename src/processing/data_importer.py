"""Import data from Excel files into database."""

from typing import Optional, List, Callable
from pathlib import Path

from sqlalchemy.orm import Session
from database.repository import (
    ProjectRepository,
    StoryRepository,
    ResultRepository,
    ResultSetRepository,
    ResultCategoryRepository,
    CacheRepository,
    AbsoluteMaxMinDriftRepository,
    ElementRepository,
    ElementCacheRepository,
)
from database.models import StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement, WallShear, ColumnShear, ColumnAxial, ColumnRotation, QuadRotation, BeamRotation

from .excel_parser import ExcelParser
from .result_processor import ResultProcessor
from .import_context import ResultImportHelper


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
        if session_factory is None:
            raise ValueError("DataImporter requires a session_factory")
        self._session_factory = session_factory

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
            "pier_forces": 0,
            "piers": 0,
            "column_forces": 0,
            "column_axials": 0,
            "column_rotations": 0,
            "columns": 0,
            "beam_rotations": 0,
            "beams": 0,
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

            print(f"\n[DEBUG DataImporter] file_path={self.file_path.name}")
            print(f"  result_types filter={self.result_types}")

            # Import story drifts if available
            if self._should_import("Story Drifts") and self.parser.validate_sheet_exists("Story Drifts"):
                drift_stats = self._import_story_drifts(session, project.id)
                stats["load_cases"] += drift_stats.get("load_cases", 0)
                stats["stories"] += drift_stats.get("stories", 0)
                stats["drifts"] += drift_stats.get("drifts", 0)

            # Import story accelerations if available (from Diaphragm Accelerations sheet)
            if self._should_import("Story Accelerations") and self.parser.validate_sheet_exists("Diaphragm Accelerations"):
                accel_stats = self._import_story_accelerations(session, project.id)
                stats["accelerations"] += accel_stats.get("accelerations", 0)

            # Import story forces if available
            if self._should_import("Story Forces") and self.parser.validate_sheet_exists("Story Forces"):
                force_stats = self._import_story_forces(session, project.id)
                stats["forces"] += force_stats.get("forces", 0)
            # Import floor displacements if available
            if self._should_import("Floors Displacements") and self.parser.validate_sheet_exists("Joint DisplacementsG"):
                disp_stats = self._import_joint_displacements(session, project.id)
                stats["displacements"] += disp_stats.get("displacements", 0)

            # Import pier forces if available
            if self._should_import("Pier Forces") and self.parser.validate_sheet_exists("Pier Forces"):
                pier_stats = self._import_pier_forces(session, project.id)
                stats["pier_forces"] += pier_stats.get("pier_forces", 0)
                stats["piers"] += pier_stats.get("piers", 0)

            # Import column forces if available
            if self._should_import("Column Forces") and self.parser.validate_sheet_exists("Element Forces - Columns"):
                column_stats = self._import_column_forces(session, project.id)
                stats["column_forces"] += column_stats.get("column_forces", 0)
                stats["columns"] += column_stats.get("columns", 0)

            # Import column axials if available (same sheet as column forces)
            if self._should_import("Column Axials") and self.parser.validate_sheet_exists("Element Forces - Columns"):
                axial_stats = self._import_column_axials(session, project.id)
                stats["column_axials"] += axial_stats.get("column_axials", 0)
                # Columns already counted from column forces

            # Import column rotations if available (from Fiber Hinge States sheet)
            if self._should_import("Column Rotations") and self.parser.validate_sheet_exists("Fiber Hinge States"):
                rotation_stats = self._import_column_rotations(session, project.id)
                stats["column_rotations"] += rotation_stats.get("column_rotations", 0)
                # Columns already counted

            # Import beam rotations if available (from Hinge States sheet)
            if self._should_import("Beam Rotations") and self.parser.validate_sheet_exists("Hinge States"):
                beam_stats = self._import_beam_rotations(session, project.id)
                stats["beam_rotations"] += beam_stats.get("beam_rotations", 0)
                stats["beams"] += beam_stats.get("beams", 0)

            # Import quad rotations if available
            if self._should_import("Quad Rotations") and self.parser.validate_sheet_exists("Quad Strain Gauge - Rotation"):
                quad_stats = self._import_quad_rotations(session, project.id)
                stats["quad_rotations"] = quad_stats.get("quad_rotations", 0)
                # Piers already counted from pier forces if both exist

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
            df, load_cases, stories = self.parser.get_story_drifts()
            helper = ResultImportHelper(session, project_id, stories)
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
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"], case_type="Time History")

                    # Create drift object
                    drift = StoryDrift(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        drift=row["Drift"],
                        max_drift=row.get("MaxDrift"),
                        min_drift=row.get("MinDrift"),
                        story_sort_order=helper._story_order.get(row["Story"]),
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
        """Import story acceleration data from Diaphragm Accelerations sheet."""
        stats = {"accelerations": 0}

        try:
            df, load_cases, stories = self.parser.get_story_accelerations()
            helper = ResultImportHelper(session, project_id, stories)
            result_repo = ResultRepository(session)

            # Process each direction
            for direction in ["UX", "UY"]:
                processed = ResultProcessor.process_story_accelerations(
                    df, load_cases, stories, direction
                )

                accel_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])

                    accel = StoryAcceleration(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        acceleration=row["Acceleration"],
                        max_acceleration=row.get("MaxAcceleration"),
                        min_acceleration=row.get("MinAcceleration"),
                        story_sort_order=helper._story_order.get(row["Story"]),
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
            df, load_cases, stories = self.parser.get_story_forces()
            helper = ResultImportHelper(session, project_id, stories)
            result_repo = ResultRepository(session)

            # Process each direction
            for direction in ["VX", "VY"]:
                processed = ResultProcessor.process_story_forces(
                    df, load_cases, stories, direction
                )

                force_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])

                    force = StoryForce(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        location=row.get("Location", "Bottom"),
                        force=row["Force"],
                        max_force=row.get("MaxForce"),
                        min_force=row.get("MinForce"),
                        story_sort_order=helper._story_order.get(row["Story"]),
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
            helper = ResultImportHelper(session, project_id, stories)

            if df.empty:
                return stats

            result_repo = ResultRepository(session)

            for direction in ["Ux", "Uy"]:
                processed = ResultProcessor.process_joint_displacements(
                    df, load_cases, stories, direction
                )

                displacement_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(
                        row["LoadCase"],
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
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    displacement_objects.append(displacement)

                result_repo.bulk_create_displacements(displacement_objects)
                stats["displacements"] += len(displacement_objects)

        except Exception as e:
            raise ValueError(f"Error importing joint displacements: {e}")

        return stats

    def _import_pier_forces(self, session, project_id: int) -> dict:
        """Import pier force data (element-level shear forces)."""
        stats = {"pier_forces": 0, "piers": 0}

        try:
            df, load_cases, stories, piers = self.parser.get_pier_forces()
            helper = ResultImportHelper(session, project_id, stories)
            element_repo = ElementRepository(session)

            # Get or create Element records for each pier
            pier_elements = {}
            for pier_name in piers:
                element = element_repo.get_or_create(
                    project_id=project_id,
                    element_type="Wall",
                    unique_name=pier_name,
                    name=pier_name,
                )
                pier_elements[pier_name] = element

            stats["piers"] = len(pier_elements)

            # Process each direction (V2, V3)
            for direction in ["V2", "V3"]:
                processed = ResultProcessor.process_pier_forces(
                    df, load_cases, stories, piers, direction
                )

                wall_shear_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = pier_elements[row["Pier"]]

                    wall_shear = WallShear(
                        element_id=element.id,
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        location=row.get("Location", "Bottom"),
                        force=row["Force"],
                        max_force=row.get("MaxForce"),
                        min_force=row.get("MinForce"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    wall_shear_objects.append(wall_shear)

                # Bulk insert
                session.bulk_save_objects(wall_shear_objects)
                session.commit()
                stats["pier_forces"] += len(wall_shear_objects)

        except Exception as e:
            raise ValueError(f"Error importing pier forces: {e}")

        return stats

    def _import_quad_rotations(self, session, project_id: int) -> dict:
        """Import quad strain gauge rotation data (element-level rotations)."""
        stats = {"quad_rotations": 0, "piers": 0}

        try:
            df, load_cases, stories, piers = self.parser.get_quad_rotations()
            helper = ResultImportHelper(session, project_id, stories)
            element_repo = ElementRepository(session)

            # Get or create Element records for each quad (different from wall piers!)
            pier_elements = {}
            for pier_name in piers:
                element = element_repo.get_or_create(
                    project_id=project_id,
                    element_type="Quad",  # Quads are separate from Wall shears
                    unique_name=pier_name,
                    name=pier_name,
                )
                pier_elements[pier_name] = element

            stats["piers"] = len(pier_elements)

            # Process quad rotations
            processed = ResultProcessor.process_quad_rotations(
                df, load_cases, stories, piers
            )

            quad_rotation_objects = []

            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = pier_elements[row["Pier"]]
                story_order = getattr(story, "sort_order", None)
                if story_order is None:
                    story_order = helper._story_order.get(row["Story"])

                quad_rotation = QuadRotation(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    result_category_id=self.result_category_id,
                    quad_name=row.get("QuadName"),
                    direction="Pier",  # Direction is typically 'Pier' in the data
                    rotation=row["Rotation"],
                    max_rotation=row.get("MaxRotation"),
                    min_rotation=row.get("MinRotation"),
                    story_sort_order=story_order,
                )
                quad_rotation_objects.append(quad_rotation)

            # Bulk insert
            session.bulk_save_objects(quad_rotation_objects)
            session.commit()
            stats["quad_rotations"] = len(quad_rotation_objects)

        except Exception as e:
            raise ValueError(f"Error importing quad rotations: {e}")

        return stats

    def _import_column_forces(self, session, project_id: int) -> dict:
        """Import column force data (element-level shear forces)."""
        stats = {"column_forces": 0, "columns": 0}

        try:
            df, load_cases, stories, columns = self.parser.get_column_forces()
            helper = ResultImportHelper(session, project_id, stories)
            element_repo = ElementRepository(session)

            # Get or create Element records for each column
            column_elements = {}
            for column_name in columns:
                element = element_repo.get_or_create(
                    project_id=project_id,
                    element_type="Column",
                    unique_name=column_name,
                    name=column_name,
                )
                column_elements[column_name] = element

            stats["columns"] = len(column_elements)

            # Process each direction (V2, V3)
            for direction in ["V2", "V3"]:
                processed = ResultProcessor.process_column_forces(
                    df, load_cases, stories, columns, direction
                )

                column_shear_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = column_elements[row["Column"]]

                    column_shear = ColumnShear(
                        element_id=element.id,
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        location=row.get("Location"),
                        force=row["Force"],
                        max_force=row.get("MaxForce"),
                        min_force=row.get("MinForce"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    column_shear_objects.append(column_shear)

                # Bulk insert
                session.bulk_save_objects(column_shear_objects)
                session.commit()
                stats["column_forces"] += len(column_shear_objects)

        except Exception as e:
            raise ValueError(f"Error importing column forces: {e}")

        return stats

    def _import_column_axials(self, session, project_id: int) -> dict:
        """Import column axial force data (minimum P values)."""
        stats = {"column_axials": 0}

        try:
            df, load_cases, stories, columns = self.parser.get_column_forces()
            helper = ResultImportHelper(session, project_id, stories)
            element_repo = ElementRepository(session)

            # Get or create Element records for each column (reuse from column forces)
            column_elements = {}
            for column_name in columns:
                element = element_repo.get_or_create(
                    project_id=project_id,
                    element_type="Column",
                    unique_name=column_name,
                    name=column_name,
                )
                column_elements[column_name] = element

            # Process column axials (minimum P values)
            processed = ResultProcessor.process_column_axials(
                df, load_cases, stories, columns
            )

            column_axial_objects = []

            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = column_elements[row["Column"]]

                column_axial = ColumnAxial(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    result_category_id=self.result_category_id,
                    location=row.get("Location"),
                    min_axial=row["MinAxial"],
                    story_sort_order=helper._story_order.get(row["Story"]),
                )
                column_axial_objects.append(column_axial)

            # Bulk insert
            session.bulk_save_objects(column_axial_objects)
            session.commit()
            stats["column_axials"] += len(column_axial_objects)

        except Exception as e:
            raise ValueError(f"Error importing column axials: {e}")

        return stats

    def _import_column_rotations(self, session, project_id: int) -> dict:
        """Import column rotation data from Fiber Hinge States (R2 and R3 rotations)."""
        stats = {"column_rotations": 0, "columns": 0}

        try:
            df, load_cases, stories, columns = self.parser.get_fiber_hinge_states()
            helper = ResultImportHelper(session, project_id, stories)
            element_repo = ElementRepository(session)

            # Get or create Element records for each column
            column_elements = {}
            for column_name in columns:
                element = element_repo.get_or_create(
                    project_id=project_id,
                    element_type="Column",
                    unique_name=column_name,
                    name=column_name,
                )
                column_elements[column_name] = element

            stats["columns"] = len(column_elements)

            # Process each direction (R2, R3)
            for direction in ["R2", "R3"]:
                processed = ResultProcessor.process_column_rotations(
                    df, load_cases, stories, columns, direction
                )

                column_rotation_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = column_elements[row["Column"]]

                    column_rotation = ColumnRotation(
                        element_id=element.id,
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        rotation=row["Rotation"],
                        max_rotation=row.get("MaxRotation"),
                        min_rotation=row.get("MinRotation"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    column_rotation_objects.append(column_rotation)

                # Bulk insert
                session.bulk_save_objects(column_rotation_objects)
                session.commit()
                stats["column_rotations"] += len(column_rotation_objects)

        except Exception as e:
            raise ValueError(f"Error importing column rotations: {e}")

        return stats

    def _import_beam_rotations(self, session, project_id: int) -> dict:
        """Import beam rotation data from Hinge States (R3 Plastic rotations)."""
        stats = {"beam_rotations": 0, "beams": 0}

        try:
            df, load_cases, stories, beams = self.parser.get_hinge_states()
            helper = ResultImportHelper(session, project_id, stories)
            element_repo = ElementRepository(session)

            # Get or create Element records for each beam
            beam_elements = {}
            for beam_name in beams:
                element = element_repo.get_or_create(
                    project_id=project_id,
                    element_type="Beam",
                    unique_name=beam_name,
                    name=beam_name,
                )
                beam_elements[beam_name] = element

            stats["beams"] = len(beam_elements)

            # Process beam rotations (single direction: R3 Plastic)
            processed = ResultProcessor.process_beam_rotations(
                df, load_cases, stories, beams
            )

            beam_rotation_objects = []

            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = beam_elements[row["Beam"]]

                beam_rotation = BeamRotation(
                    element_id=element.id,
                    story_id=story.id,
                    load_case_id=load_case.id,
                    result_category_id=self.result_category_id,
                    hinge=row.get("Hinge"),
                    generated_hinge=row.get("GeneratedHinge"),
                    rel_dist=row.get("RelDist"),
                    r3_plastic=row["R3Plastic"],
                    max_r3_plastic=row.get("MaxR3Plastic"),
                    min_r3_plastic=row.get("MinR3Plastic"),
                    story_sort_order=helper._story_order.get(row["Story"]),
                )
                beam_rotation_objects.append(beam_rotation)

            # Bulk insert
            session.bulk_save_objects(beam_rotation_objects)
            session.commit()
            stats["beam_rotations"] += len(beam_rotation_objects)

        except Exception as e:
            raise ValueError(f"Error importing beam rotations: {e}")

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
        self._cache_pier_forces(session, project_id, result_set_id, stories)
        self._cache_column_shears(session, project_id, result_set_id, stories)
        self._cache_min_axials(session, project_id, result_set_id, stories)
        self._cache_column_rotations(session, project_id, result_set_id, stories)
        self._cache_beam_rotations(session, project_id, result_set_id, stories)
        self._cache_quad_rotations(session, project_id, result_set_id, stories)
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

        # Group by story and build wide-format matrix, track story_sort_order
        story_matrices = {}
        story_sort_orders = {}
        for drift, load_case_name in drifts:
            story_id = drift.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                # Capture story_sort_order from first drift for this story
                story_sort_orders[story_id] = drift.story_sort_order

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
                story_sort_order=story_sort_orders.get(story_id),
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
        story_sort_orders = {}
        for accel, load_case_name in accels:
            story_id = accel.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                story_sort_orders[story_id] = accel.story_sort_order

            key = f"{load_case_name}_{accel.direction}"
            story_matrices[story_id][key] = accel.acceleration

        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Accelerations",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
                story_sort_order=story_sort_orders.get(story_id),
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
        story_sort_orders = {}
        for force, load_case_name in forces:
            story_id = force.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                story_sort_orders[story_id] = force.story_sort_order

            key = f"{load_case_name}_{force.direction}"
            story_matrices[story_id][key] = force.force

        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Forces",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
                story_sort_order=story_sort_orders.get(story_id),
            )

    def _cache_pier_forces(self, session, project_id: int, result_set_id: int, stories):
        """Generate cache for pier forces (element-level shears)."""
        from sqlalchemy import and_
        from database.models import WallShear, LoadCase, Story, Element

        element_repo = ElementRepository(session)
        element_cache_repo = ElementCacheRepository(session)

        # Get all pier elements for this project
        piers = element_repo.get_by_project(project_id, element_type="Wall")

        # For each pier and each direction, generate cache
        for pier in piers:
            for direction in ["V2", "V3"]:
                result_type = f"WallShears_{direction}"

                # Query wall shears for this pier and direction
                shears = (
                    session.query(WallShear, LoadCase.name, Story)
                    .join(LoadCase, WallShear.load_case_id == LoadCase.id)
                    .join(Story, WallShear.story_id == Story.id)
                    .filter(WallShear.element_id == pier.id)
                    .filter(WallShear.direction == direction)
                    .filter(WallShear.result_category_id == self.result_category_id)
                    .all()
                )

                # Build wide-format cache per story, track story_sort_order per element
                story_data = {}
                story_sort_orders = {}
                for shear, case_name, story in shears:
                    if story.id not in story_data:
                        story_data[story.id] = {}
                        # Capture story_sort_order from first shear for this element+story
                        story_sort_orders[story.id] = shear.story_sort_order
                    story_data[story.id][case_name] = shear.force

                # Upsert cache entries
                for story_id, results_matrix in story_data.items():
                    element_cache_repo.upsert_cache_entry(
                        project_id=project_id,
                        element_id=pier.id,
                        story_id=story_id,
                        result_type=result_type,
                        results_matrix=results_matrix,
                        result_set_id=result_set_id,
                        story_sort_order=story_sort_orders.get(story_id),
                    )

    def _cache_column_shears(self, session, project_id: int, result_set_id: int, stories):
        """Generate cache for column shears (element-level shear forces)."""
        from sqlalchemy import and_
        from database.models import ColumnShear, LoadCase, Story, Element

        element_repo = ElementRepository(session)
        element_cache_repo = ElementCacheRepository(session)

        # Get all column elements for this project
        columns = element_repo.get_by_project(project_id, element_type="Column")

        # For each column and each direction, generate cache
        for column in columns:
            for direction in ["V2", "V3"]:
                result_type = f"ColumnShears_{direction}"

                # Query column shears for this column and direction
                shears = (
                    session.query(ColumnShear, LoadCase.name, Story)
                    .join(LoadCase, ColumnShear.load_case_id == LoadCase.id)
                    .join(Story, ColumnShear.story_id == Story.id)
                    .filter(ColumnShear.element_id == column.id)
                    .filter(ColumnShear.direction == direction)
                    .filter(ColumnShear.result_category_id == self.result_category_id)
                    .all()
                )

                # Build wide-format cache per story, track story_sort_order per element
                story_data = {}
                story_sort_orders = {}
                for shear, case_name, story in shears:
                    if story.id not in story_data:
                        story_data[story.id] = {}
                        # Capture story_sort_order from first shear for this element+story
                        story_sort_orders[story.id] = shear.story_sort_order
                    story_data[story.id][case_name] = shear.force

                # Upsert cache entries
                for story_id, results_matrix in story_data.items():
                    element_cache_repo.upsert_cache_entry(
                        project_id=project_id,
                        element_id=column.id,
                        story_id=story_id,
                        result_type=result_type,
                        results_matrix=results_matrix,
                        result_set_id=result_set_id,
                        story_sort_order=story_sort_orders.get(story_id),
                    )

    def _cache_min_axials(self, session, project_id: int, result_set_id: int, stories):
        """Generate cache for minimum axial forces (element-level compression)."""
        from sqlalchemy import and_
        from database.models import ColumnAxial, LoadCase, Story, Element

        element_repo = ElementRepository(session)
        element_cache_repo = ElementCacheRepository(session)

        # Get all column elements for this project
        columns = element_repo.get_by_project(project_id, element_type="Column")

        # For each column, generate cache
        for column in columns:
            result_type = "MinAxial"

            # Query column axials for this column
            axials = (
                session.query(ColumnAxial, LoadCase.name, Story)
                .join(LoadCase, ColumnAxial.load_case_id == LoadCase.id)
                .join(Story, ColumnAxial.story_id == Story.id)
                .filter(ColumnAxial.element_id == column.id)
                .filter(ColumnAxial.result_category_id == self.result_category_id)
                .all()
            )

            # Build wide-format cache per story, track story_sort_order per element
            story_data = {}
            story_sort_orders = {}
            for axial, case_name, story in axials:
                if story.id not in story_data:
                    story_data[story.id] = {}
                    # Capture story_sort_order from first axial for this element+story
                    story_sort_orders[story.id] = axial.story_sort_order
                story_data[story.id][case_name] = axial.min_axial

            # Upsert cache entries
            for story_id, results_matrix in story_data.items():
                element_cache_repo.upsert_cache_entry(
                    project_id=project_id,
                    element_id=column.id,
                    story_id=story_id,
                    result_type=result_type,
                    results_matrix=results_matrix,
                    result_set_id=result_set_id,
                    story_sort_order=story_sort_orders.get(story_id),
                )

    def _cache_quad_rotations(self, session, project_id: int, result_set_id: int, stories):
        """Generate cache for quad rotations (element-level rotations displayed as %)."""
        from sqlalchemy import and_
        from database.models import QuadRotation, LoadCase, Story, Element

        element_repo = ElementRepository(session)
        element_cache_repo = ElementCacheRepository(session)

        # Get all quad elements for this project
        quads = element_repo.get_by_project(project_id, element_type="Quad")

        # For each quad, generate cache for rotations
        for quad in quads:
            result_type = "QuadRotations"

            # Query quad rotations for this quad element
            rotations = (
                session.query(QuadRotation, LoadCase.name, Story)
                .join(LoadCase, QuadRotation.load_case_id == LoadCase.id)
                .join(Story, QuadRotation.story_id == Story.id)
                .filter(QuadRotation.element_id == quad.id)
                .filter(QuadRotation.result_category_id == self.result_category_id)
                .all()
            )

            # Build wide-format cache per story, track story_sort_order per element
            story_data = {}
            story_sort_orders = {}
            for rotation, case_name, story in rotations:
                if story.id not in story_data:
                    story_data[story.id] = {}
                    canonical_order = story.sort_order
                    if canonical_order is None:
                        canonical_order = rotation.story_sort_order
                    # Capture story_sort_order from first rotation for this element+story
                    story_sort_orders[story.id] = canonical_order
                # Convert radians to percentage (* 100) for display
                story_data[story.id][case_name] = rotation.rotation * 100.0

            # Upsert cache entries
            for story_id, results_matrix in story_data.items():
                element_cache_repo.upsert_cache_entry(
                    project_id=project_id,
                    element_id=quad.id,
                    story_id=story_id,
                    result_type=result_type,
                    results_matrix=results_matrix,
                    result_set_id=result_set_id,
                    story_sort_order=story_sort_orders.get(story_id),
                )

    def _cache_column_rotations(self, session, project_id: int, result_set_id: int, stories):
        """Generate cache for column rotations (element-level rotations displayed as %)."""
        from sqlalchemy import and_
        from database.models import ColumnRotation, LoadCase, Story, Element

        element_repo = ElementRepository(session)
        element_cache_repo = ElementCacheRepository(session)

        # Get all column elements for this project
        columns = element_repo.get_by_project(project_id, element_type="Column")

        # For each column and each direction, generate cache
        for column in columns:
            for direction in ["R2", "R3"]:
                result_type = f"ColumnRotations_{direction}"

                # Query column rotations for this column and direction
                rotations = (
                    session.query(ColumnRotation, LoadCase.name, Story)
                    .join(LoadCase, ColumnRotation.load_case_id == LoadCase.id)
                    .join(Story, ColumnRotation.story_id == Story.id)
                    .filter(ColumnRotation.element_id == column.id)
                    .filter(ColumnRotation.direction == direction)
                    .filter(ColumnRotation.result_category_id == self.result_category_id)
                    .all()
                )

                # Build wide-format cache per story, track story_sort_order per element
                story_data = {}
                story_sort_orders = {}
                for rotation, case_name, story in rotations:
                    if story.id not in story_data:
                        story_data[story.id] = {}
                        # Capture story_sort_order from first rotation for this element+story
                        story_sort_orders[story.id] = rotation.story_sort_order
                    # Convert radians to percentage (* 100) for display
                    story_data[story.id][case_name] = rotation.rotation * 100.0

                # Upsert cache entries
                for story_id, results_matrix in story_data.items():
                    element_cache_repo.upsert_cache_entry(
                        project_id=project_id,
                        element_id=column.id,
                        story_id=story_id,
                        result_type=result_type,
                        results_matrix=results_matrix,
                        result_set_id=result_set_id,
                        story_sort_order=story_sort_orders.get(story_id),
                    )

    def _cache_beam_rotations(self, session, project_id: int, result_set_id: int, stories):
        """Generate cache for beam rotations (element-level R3 Plastic rotations displayed as %)."""
        from sqlalchemy import and_
        from database.models import BeamRotation, LoadCase, Story, Element

        element_repo = ElementRepository(session)
        element_cache_repo = ElementCacheRepository(session)

        # Get all beam elements for this project
        beams = element_repo.get_by_project(project_id, element_type="Beam")

        # For each beam, generate cache for R3 Plastic rotations
        for beam in beams:
            result_type = "BeamRotations_R3Plastic"

            # Query beam rotations for this beam
            rotations = (
                session.query(BeamRotation, LoadCase.name, Story)
                .join(LoadCase, BeamRotation.load_case_id == LoadCase.id)
                .join(Story, BeamRotation.story_id == Story.id)
                .filter(BeamRotation.element_id == beam.id)
                .filter(BeamRotation.result_category_id == self.result_category_id)
                .all()
            )

            # Build wide-format cache per story, track story_sort_order per element
            story_data = {}
            story_sort_orders = {}
            for rotation, case_name, story in rotations:
                if story.id not in story_data:
                    story_data[story.id] = {}
                    # Capture story_sort_order from first rotation for this element+story
                    story_sort_orders[story.id] = rotation.story_sort_order
                # Convert radians to percentage (* 100) for display
                story_data[story.id][case_name] = rotation.r3_plastic * 100.0

            # Upsert cache entries
            for story_id, results_matrix in story_data.items():
                element_cache_repo.upsert_cache_entry(
                    project_id=project_id,
                    element_id=beam.id,
                    story_id=story_id,
                    result_type=result_type,
                    results_matrix=results_matrix,
                    result_set_id=result_set_id,
                    story_sort_order=story_sort_orders.get(story_id),
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
        story_sort_orders = {}
        for displacement, load_case_name in displacements:
            story_id = displacement.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                story_sort_orders[story_id] = displacement.story_sort_order

            key = f"{load_case_name}_{displacement.direction}"
            story_matrices[story_id][key] = displacement.displacement

        for story_id, results_matrix in story_matrices.items():
            cache_repo.upsert_cache_entry(
                project_id=project_id,
                story_id=story_id,
                result_type="Displacements",
                results_matrix=results_matrix,
                result_set_id=result_set_id,
                story_sort_order=story_sort_orders.get(story_id),
            )
