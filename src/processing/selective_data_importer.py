"""Data importer with load case filtering support."""

from __future__ import annotations

from typing import Optional, List, Callable, Set, TYPE_CHECKING

from sqlalchemy.orm import Session

from .data_importer import DataImporter

if TYPE_CHECKING:
    from .import_preparation import FilePrescanSummary


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

    def _build_global_importer(self, session: Session, project_id: int):
        from .global_importer import GlobalImporter

        return GlobalImporter(
            session=session,
            parser=self.parser,
            project_id=project_id,
            result_category_id=self.result_category_id,
            allowed_load_cases=self.allowed_load_cases,
        )

    def _build_element_importer(self, session: Session, project_id: int):
        from .element_importer import ElementImporter

        return ElementImporter(
            session=session,
            parser=self.parser,
            project_id=project_id,
            result_category_id=self.result_category_id,
            allowed_load_cases=self.allowed_load_cases,
        )

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
            if self._sheet_available("Joint Displacements") and not self._sheet_available("Fou"):
                try:
                    with self._phase_timer.measure(
                        "vertical_displacements",
                        {"source": "shared_foundation"},
                    ):
                        with self.session_scope() as session:
                            # Get project from stats (already created by parent)
                            from database.repositories import ProjectRepository

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
        stats = {"load_cases": 0, "stories": 0, "drifts": 0}
        if not self._sheet_has_allowed_load_cases("Story Drifts"):
            return stats
        try:
            importer = self._build_global_importer(session, project_id)
            return importer.import_story_drifts()
        except Exception as e:
            raise ValueError(f"Error importing story drifts: {e}")

    def _import_story_accelerations(self, session, project_id: int) -> dict:
        """Import story accelerations with load case filtering."""
        stats = {"accelerations": 0}
        if not self._sheet_has_allowed_load_cases("Diaphragm Accelerations"):
            return stats
        try:
            importer = self._build_global_importer(session, project_id)
            return importer.import_story_accelerations()
        except Exception as e:
            raise ValueError(f"Error importing story accelerations: {e}")

    def _import_story_forces(self, session, project_id: int) -> dict:
        """Import story forces with load case filtering."""
        stats = {"forces": 0}
        if not self._sheet_has_allowed_load_cases("Story Forces"):
            return stats
        try:
            importer = self._build_global_importer(session, project_id)
            return importer.import_story_forces()
        except Exception as e:
            raise ValueError(f"Error importing story forces: {e}")

    def _import_joint_displacements(self, session, project_id: int) -> dict:
        """Import joint displacements with load case filtering."""
        stats = {"displacements": 0}
        if not self._sheet_has_allowed_load_cases("Joint Displacements"):
            return stats
        try:
            importer = self._build_global_importer(session, project_id)
            return importer.import_joint_displacements()
        except Exception as e:
            raise ValueError(f"Error importing joint displacements: {e}")

    def _import_pier_forces(self, session, project_id: int) -> dict:
        """Import pier forces (wall shears) with load case filtering."""
        stats = {"pier_forces": 0, "piers": 0}
        if not self._sheet_has_allowed_load_cases("Pier Forces"):
            return stats
        try:
            importer = self._build_element_importer(session, project_id)
            return importer.import_pier_forces()
        except Exception as e:
            raise ValueError(f"Error importing pier forces: {e}")

    def _import_column_forces(self, session, project_id: int) -> dict:
        """Import column forces (shears) with load case filtering."""
        stats = {"column_forces": 0, "columns": 0}
        if not self._sheet_has_allowed_load_cases("Element Forces - Columns"):
            return stats
        try:
            importer = self._build_element_importer(session, project_id)
            return importer.import_column_forces()
        except Exception as e:
            raise ValueError(f"Error importing column forces: {e}")

    def _import_column_axials(self, session, project_id: int) -> dict:
        """Import column axial forces with load case filtering (min and max)."""
        stats = {"column_axials": 0}
        if not self._sheet_has_allowed_load_cases("Element Forces - Columns"):
            return stats
        try:
            importer = self._build_element_importer(session, project_id)
            return importer.import_column_axials()
        except Exception as e:
            raise ValueError(f"Error importing column axial forces: {e}")

    def _import_column_rotations(self, session, project_id: int) -> dict:
        """Import column rotations with load case filtering."""
        stats = {"column_rotations": 0}
        if not self._sheet_has_allowed_load_cases("Fiber Hinge States"):
            return stats
        try:
            importer = self._build_element_importer(session, project_id)
            return importer.import_column_rotations()
        except Exception as e:
            raise ValueError(f"Error importing column rotations: {e}")

    def _import_beam_rotations(self, session, project_id: int) -> dict:
        """Import beam rotations with load case filtering."""
        stats = {"beam_rotations": 0, "beams": 0}
        if not self._sheet_has_allowed_load_cases("Hinge States"):
            return stats
        try:
            importer = self._build_element_importer(session, project_id)
            return importer.import_beam_rotations()
        except Exception as e:
            raise ValueError(f"Error importing beam rotations: {e}")

    def _import_quad_rotations(self, session, project_id: int) -> dict:
        """Import quad rotations with load case filtering."""
        stats = {"quad_rotations": 0}
        if not self._sheet_has_allowed_load_cases("Quad Strain Gauge - Rotation"):
            return stats
        try:
            importer = self._build_element_importer(session, project_id)
            return importer.import_quad_rotations()
        except Exception as e:
            raise ValueError(f"Error importing quad rotations: {e}")

    def _import_vertical_displacements(self, session, project_id: int) -> dict:
        """Import vertical displacements with load case filtering and foundation joints from Fou sheet."""
        from database.repositories import ResultCategoryRepository
        from database.models import VerticalDisplacement
        from .import_context import ResultImportHelper
        from .import_filtering import filter_cases_and_dataframe

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

            filtered_load_cases, df = filter_cases_and_dataframe(
                df,
                load_cases,
                self.allowed_load_cases,
                column="Output Case",
            )
            if not filtered_load_cases:
                return stats

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
