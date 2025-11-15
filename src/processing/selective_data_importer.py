"""Data importer with load case filtering support."""

from __future__ import annotations

from typing import Optional, List, Callable, Set, TYPE_CHECKING
from pathlib import Path

from sqlalchemy.orm import Session

from database.repository import (
    StoryDriftDataRepository,
    StoryAccelerationDataRepository,
    StoryForceDataRepository,
    StoryDisplacementDataRepository,
)

from .data_importer import DataImporter

if TYPE_CHECKING:
    from services.import_preparation import FilePrescanSummary


class SelectiveDataImporter(DataImporter):
    def __init__(
        self,
        file_path: str,
        project_name: str,
        result_set_name: str,
        allowed_load_cases: Set[str],
        analysis_type: Optional[str] = None,
        result_types: Optional[List[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
        foundation_joints: Optional[List[str]] = None,
        file_summary: Optional["FilePrescanSummary"] = None,
        generate_cache: bool = True,
    ):
        """
        Initialize selective data importer.

        Args:
            file_path: Path to Excel file
            project_name: Name of the project
            result_set_name: Name for this result set
            allowed_load_cases: Set of load case names to import
            analysis_type: Optional analysis type
            result_types: Optional list of result types to filter
            session_factory: Factory function to create database sessions
            foundation_joints: Optional list of joint names from Fou sheet (for vertical displacements)
        """
        super().__init__(
            file_path=file_path,
            project_name=project_name,
            result_set_name=result_set_name,
            analysis_type=analysis_type,
            result_types=result_types,
            session_factory=session_factory,
            file_summary=file_summary,
            generate_cache=generate_cache,
        )
        self.allowed_load_cases = allowed_load_cases
        self.foundation_joints = foundation_joints or []

    def _filter_load_cases(self, load_cases: List[str]) -> List[str]:
        """
        Filter load cases to only allowed ones.

        Args:
            load_cases: List of all load cases from Excel

        Returns:
            Filtered list containing only allowed load cases
        """
        return [lc for lc in load_cases if lc in self.allowed_load_cases]

    def _sheet_has_allowed_load_cases(self, summary_key: str) -> bool:
        """
        Determine if a sheet contains any allowed load cases based on prescan data.
        """
        if not self.allowed_load_cases or not self.file_summary:
            return True

        sheet_cases = self.file_summary.load_cases_by_sheet.get(summary_key)
        if sheet_cases is None:
            return True  # Fallback to parser if sheet wasn't scanned

        return any(lc in self.allowed_load_cases for lc in sheet_cases)

    def import_all(self) -> dict:
        """
        Import all available data from Excel file with load case filtering.
        Overrides parent to handle vertical displacements with shared foundation joints.

        Returns:
            Dictionary with import statistics
        """
        # Call parent import_all first
        stats = super().import_all()

        # Add vertical displacement import if foundation joints are provided
        # This allows import even when this file doesn't have a Fou sheet
        if self.foundation_joints and self._should_import("Vertical Displacements"):
            if self._sheet_available("Joint Displacements"):
                try:
                    with self._phase_timer.measure(
                        "vertical_displacements",
                        {"source": "shared_foundation"},
                    ):
                        with self.session_scope() as session:
                            # Get project from stats (already created by parent)
                            from database.repository import ProjectRepository

                            project_repo = ProjectRepository(session)
                            project = project_repo.get_by_name(self.project_name)

                            if project:
                                vert_disp_stats = self._import_vertical_displacements(session, project.id)
                                stats["vertical_displacements"] = vert_disp_stats.get("vertical_displacements", 0)
                except Exception as e:
                    stats["errors"].append(f"Error importing vertical displacements: {str(e)}")

        return stats

    def _import_story_drifts(self, session, project_id: int) -> dict:
        """Import story drifts with load case filtering."""
        from database.models import StoryDrift
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"load_cases": 0, "stories": 0, "drifts": 0}

        if not self._sheet_has_allowed_load_cases("Story Drifts"):
            return stats

        try:
            df, load_cases, stories = self.parser.get_story_drifts()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats  # No load cases to import

            # Filter dataframe to only include allowed load cases
            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

            helper = ResultImportHelper(session, project_id, stories)
            drift_repo = StoryDriftDataRepository(session)

            # Process each direction
            for direction in ["X", "Y"]:
                processed = ResultProcessor.process_story_drifts(
                    df, filtered_load_cases, stories, direction
                )

                drift_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"], case_type="Time History")

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

                drift_repo.bulk_create(drift_objects)
                stats["drifts"] += len(drift_objects)

            stats["load_cases"] = len(filtered_load_cases)
            stats["stories"] = len(stories)

        except Exception as e:
            raise ValueError(f"Error importing story drifts: {e}")

        return stats

    def _import_story_accelerations(self, session, project_id: int) -> dict:
        """Import story accelerations with load case filtering."""
        from database.models import StoryAcceleration
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"accelerations": 0}

        if not self._sheet_has_allowed_load_cases("Diaphragm Accelerations"):
            return stats

        try:
            df, load_cases, stories = self.parser.get_story_accelerations()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

            helper = ResultImportHelper(session, project_id, stories)
            accel_repo = StoryAccelerationDataRepository(session)

            for direction in ["UX", "UY"]:
                processed = ResultProcessor.process_story_accelerations(
                    df, filtered_load_cases, stories, direction
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

                accel_repo.bulk_create(accel_objects)
                stats["accelerations"] += len(accel_objects)

        except Exception as e:
            raise ValueError(f"Error importing story accelerations: {e}")

        return stats

    def _import_story_forces(self, session, project_id: int) -> dict:
        """Import story forces with load case filtering."""
        from database.models import StoryForce
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"forces": 0}

        if not self._sheet_has_allowed_load_cases("Story Forces"):
            return stats

        try:
            df, load_cases, stories = self.parser.get_story_forces()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

            helper = ResultImportHelper(session, project_id, stories)
            force_repo = StoryForceDataRepository(session)

            for direction in ["VX", "VY"]:
                processed = ResultProcessor.process_story_forces(
                    df, filtered_load_cases, stories, direction
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
                        force=row["Force"],
                        max_force=row.get("MaxForce"),
                        min_force=row.get("MinForce"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    force_objects.append(force)

                force_repo.bulk_create(force_objects)
                stats["forces"] += len(force_objects)

        except Exception as e:
            raise ValueError(f"Error importing story forces: {e}")

        return stats

    def _import_joint_displacements(self, session, project_id: int) -> dict:
        """Import joint displacements with load case filtering."""
        from database.models import StoryDisplacement
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"displacements": 0}

        if not self._sheet_has_allowed_load_cases("Joint Displacements"):
            return stats

        try:
            with self._phase_timer.measure("floor_displacements_parse"):
                df, load_cases, stories = self.parser.get_joint_displacements()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

            helper = ResultImportHelper(session, project_id, stories)
            disp_repo = StoryDisplacementDataRepository(session)

            for direction, column_name in [("UX", "Ux"), ("UY", "Uy")]:
                with self._phase_timer.measure("floor_displacements_process"):
                    processed = ResultProcessor.process_joint_displacements(
                        df, filtered_load_cases, stories, column_name
                    )

                disp_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])

                    disp = StoryDisplacement(
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        displacement=row["Displacement"],
                        max_displacement=row.get("MaxDisplacement"),
                        min_displacement=row.get("MinDisplacement"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    disp_objects.append(disp)

                with self._phase_timer.measure("floor_displacements_db"):
                    disp_repo.bulk_create(disp_objects)
                stats["displacements"] += len(disp_objects)

        except Exception as e:
            raise ValueError(f"Error importing joint displacements: {e}")

        return stats

    def _import_pier_forces(self, session, project_id: int) -> dict:
        """Import pier forces (wall shears) with load case filtering."""
        from database.repository import ElementRepository, ElementCacheRepository
        from database.models import WallShear
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"pier_forces": 0, "piers": 0}

        if not self._sheet_has_allowed_load_cases("Pier Forces"):
            return stats

        try:
            df, load_cases, stories, piers = self.parser.get_pier_forces()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

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

            for direction in ["V2", "V3"]:
                processed = ResultProcessor.process_pier_forces(
                    df, filtered_load_cases, stories, piers, direction
                )

                shear_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = pier_elements[row["Pier"]]

                    shear = WallShear(
                        story_id=story.id,
                        element_id=element.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        force=row["Force"],
                        max_force=row.get("MaxForce"),
                        min_force=row.get("MinForce"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    shear_objects.append(shear)

                session.bulk_save_objects(shear_objects)
                session.commit()
                stats["pier_forces"] += len(shear_objects)

        except Exception as e:
            raise ValueError(f"Error importing pier forces: {e}")

        return stats

    def _import_column_forces(self, session, project_id: int) -> dict:
        """Import column forces (shears) with load case filtering."""
        from database.repository import ElementRepository
        from database.models import ColumnShear
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"column_forces": 0, "columns": 0}

        if not self._sheet_has_allowed_load_cases("Element Forces - Columns"):
            return stats

        try:
            df, load_cases, stories, columns = self.parser.get_column_forces()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

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

            for direction in ["V2", "V3"]:
                processed = ResultProcessor.process_column_forces(
                    df, filtered_load_cases, stories, columns, direction
                )

                shear_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = column_elements[row["Column"]]

                    shear = ColumnShear(
                        story_id=story.id,
                        element_id=element.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        location=row.get("Location"),
                        force=row["Force"],
                        max_force=row.get("MaxForce"),
                        min_force=row.get("MinForce"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    shear_objects.append(shear)

                session.bulk_save_objects(shear_objects)
                session.commit()
                stats["column_forces"] += len(shear_objects)

        except Exception as e:
            raise ValueError(f"Error importing column forces: {e}")

        return stats

    def _import_column_axials(self, session, project_id: int) -> dict:
        """Import column axial forces with load case filtering."""
        from database.repository import ElementRepository
        from database.models import ColumnAxial
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"column_axials": 0}

        if not self._sheet_has_allowed_load_cases("Element Forces - Columns"):
            return stats

        try:
            df, load_cases, stories, columns = self.parser.get_column_forces()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

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

            processed = ResultProcessor.process_column_axials(
                df, filtered_load_cases, stories, columns
            )

            axial_objects = []

            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = column_elements[row["Column"]]

                axial = ColumnAxial(
                    story_id=story.id,
                    element_id=element.id,
                    load_case_id=load_case.id,
                    result_category_id=self.result_category_id,
                    location=row.get("Location"),
                    min_axial=row["MinAxial"],
                    story_sort_order=helper._story_order.get(row["Story"]),
                )
                axial_objects.append(axial)

            session.bulk_save_objects(axial_objects)
            session.commit()
            stats["column_axials"] += len(axial_objects)

        except Exception as e:
            raise ValueError(f"Error importing column axial forces: {e}")

        return stats

    def _import_column_rotations(self, session, project_id: int) -> dict:
        """Import column rotations with load case filtering."""
        from database.repository import ElementRepository
        from database.models import ColumnRotation
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"column_rotations": 0}

        if not self._sheet_has_allowed_load_cases("Fiber Hinge States"):
            return stats

        try:
            df, load_cases, stories, columns = self.parser.get_fiber_hinge_states()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

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

            for direction in ["R2", "R3"]:
                processed = ResultProcessor.process_column_rotations(
                    df, filtered_load_cases, stories, columns, direction
                )

                rotation_objects = []

                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = column_elements[row["Column"]]

                    rotation = ColumnRotation(
                        story_id=story.id,
                        element_id=element.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        direction=direction,
                        rotation=row["Rotation"],
                        max_rotation=row.get("MaxRotation"),
                        min_rotation=row.get("MinRotation"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                    rotation_objects.append(rotation)

                session.bulk_save_objects(rotation_objects)
                session.commit()
                stats["column_rotations"] += len(rotation_objects)

        except Exception as e:
            raise ValueError(f"Error importing column rotations: {e}")

        return stats

    def _import_beam_rotations(self, session, project_id: int) -> dict:
        """Import beam rotations with load case filtering."""
        from database.repository import ElementRepository
        from database.models import BeamRotation
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"beam_rotations": 0, "beams": 0}

        if not self._sheet_has_allowed_load_cases("Hinge States"):
            return stats

        try:
            df, load_cases, stories, beams = self.parser.get_hinge_states()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

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

            processed = ResultProcessor.process_beam_rotations(
                df, filtered_load_cases, stories, beams
            )

            rotation_objects = []

            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = beam_elements[row["Beam"]]

                rotation = BeamRotation(
                    story_id=story.id,
                    element_id=element.id,
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
                rotation_objects.append(rotation)

            session.bulk_save_objects(rotation_objects)
            session.commit()
            stats["beam_rotations"] += len(rotation_objects)

        except Exception as e:
            raise ValueError(f"Error importing beam rotations: {e}")

        return stats

    def _import_quad_rotations(self, session, project_id: int) -> dict:
        """Import quad rotations with load case filtering."""
        from database.repository import ElementRepository
        from database.models import QuadRotation
        from .result_processor import ResultProcessor
        from .import_context import ResultImportHelper

        stats = {"quad_rotations": 0}

        if not self._sheet_has_allowed_load_cases("Quad Strain Gauge - Rotation"):
            return stats

        try:
            with self._phase_timer.measure("quad_rotations_parse"):
                df, load_cases, stories, piers = self.parser.get_quad_rotations()

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

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

            with self._phase_timer.measure("quad_rotations_process"):
                processed = ResultProcessor.process_quad_rotations(
                    df, filtered_load_cases, stories, piers
                )

            rotation_objects = []

            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = pier_elements[row["Pier"]]

                rotation = QuadRotation(
                    story_id=story.id,
                    element_id=element.id,
                    load_case_id=load_case.id,
                    result_category_id=self.result_category_id,
                    quad_name=row.get("QuadName"),
                    direction="Pier",  # Direction is typically 'Pier' in the data
                    rotation=row["Rotation"],
                    max_rotation=row.get("MaxRotation"),
                    min_rotation=row.get("MinRotation"),
                    # Note: Quad rotations use global story sort order
                    story_sort_order=story.sort_order,
                )
                rotation_objects.append(rotation)

            with self._phase_timer.measure("quad_rotations_db"):
                session.bulk_save_objects(rotation_objects)
                session.commit()
            stats["quad_rotations"] += len(rotation_objects)

        except Exception as e:
            raise ValueError(f"Error importing quad rotations: {e}")

        return stats

    def _import_vertical_displacements(self, session, project_id: int) -> dict:
        """Import vertical displacements with load case filtering and foundation joints from Fou sheet."""
        from database.repository import ResultCategoryRepository
        from database.models import VerticalDisplacement
        from .import_context import ResultImportHelper

        stats = {"vertical_displacements": 0}

        if not self._sheet_has_allowed_load_cases("Vertical Displacements"):
            return stats

        # Skip if no foundation joints provided
        if not self.foundation_joints:
            return stats

        try:
            with self._phase_timer.measure("vertical_displacements_parse"):
                df, load_cases, unique_joints = self.parser.get_vertical_displacements(
                    foundation_joints=self.foundation_joints
                )

            if df.empty:
                return stats

            # Filter to only allowed load cases
            filtered_load_cases = self._filter_load_cases(load_cases)

            if not filtered_load_cases:
                return stats

            df = df[df['Output Case'].isin(filtered_load_cases)].copy()

            helper = ResultImportHelper(session, project_id, [])  # No stories needed for joint results

            # Create or get load cases
            load_case_map = {}
            for case_name in filtered_load_cases:
                load_case = helper.get_load_case(case_name)
                load_case_map[case_name] = load_case

            # Create result category for Joints
            category_repo = ResultCategoryRepository(session)
            result_category = category_repo.get_or_create(
                result_set_id=self.result_set_id,
                category_name="Envelopes",
                category_type="Joints",
            )

            vert_disp_objects = []

            with self._phase_timer.measure("vertical_displacements_process"):
                for _, row in df.iterrows():
                    load_case = load_case_map[row["Output Case"]]

                    vert_disp = VerticalDisplacement(
                        project_id=project_id,
                        result_set_id=self.result_set_id,
                        result_category_id=result_category.id,
                        load_case_id=load_case.id,
                        story=row["Story"],
                        label=row["Label"],
                        unique_name=row["Unique Name"],
                        min_displacement=row["Min Uz"],
                    )
                    vert_disp_objects.append(vert_disp)

            # Bulk insert
            with self._phase_timer.measure("vertical_displacements_db"):
                session.bulk_save_objects(vert_disp_objects)
                session.commit()
            stats["vertical_displacements"] += len(vert_disp_objects)

        except Exception as e:
            raise ValueError(f"Error importing vertical displacements: {e}")

        return stats
