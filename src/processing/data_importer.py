"""Import data from Excel files into database."""

import logging
from pathlib import Path
from typing import Optional, List, Callable, TYPE_CHECKING, Set

from sqlalchemy.orm import Session

from .excel_parser import ExcelParser
from .base_importer import BaseImporter
from .import_tasks import DEFAULT_IMPORT_TASKS, ImportTask
from utils.timing import PhaseTimer
from utils.error_handling import timed
from .metadata_importer import MetadataImporter
from .import_runner import run_import_tasks, task_sheets_available, merge_task_stats
from .import_logging import (
    log_import_complete,
    log_import_failure,
    log_phase_timings,
    log_import_start,
)
from .import_utils import sheet_available

if TYPE_CHECKING:
    from .import_preparation import FilePrescanSummary


logger = logging.getLogger(__name__)


class DataImporter(BaseImporter):
    """Import structural analysis results from Excel into database."""

    def __init__(
        self,
        file_path: str,
        project_name: str,
        result_set_name: str,
        analysis_type: Optional[str] = None,
        result_types: Optional[List[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
        file_summary: Optional["FilePrescanSummary"] = None,
        generate_cache: bool = True,
    ):
        """Initialize importer.

        Args:
            file_path: Path to Excel file
            project_name: Name of the project
            result_set_name: Name for this result set (e.g., DES, MCE, SLE)
            analysis_type: Optional analysis type (e.g., 'DERG', 'MCR')
        """
        super().__init__(result_types=result_types, session_factory=session_factory)
        self.file_path = Path(file_path)
        self.project_name = project_name
        self.result_set_name = result_set_name
        self.analysis_type = analysis_type or "General"
        self.parser = ExcelParser(file_path)
        self.file_summary = file_summary
        self._available_sheets_hint: Optional[Set[str]] = (
            set(file_summary.available_sheets) if file_summary else None
        )
        self._phase_timer = PhaseTimer({"file": self.file_path.name})
        self._generate_cache_after_import = generate_cache
        self._cache_generated = False
        self._project_id: Optional[int] = None
        self._import_tasks: tuple[ImportTask, ...] = DEFAULT_IMPORT_TASKS

    def _sheet_available(self, sheet_name: str) -> bool:
        """Check sheet availability using prescan data when available."""
        if self._available_sheets_hint is not None:
            return sheet_name in self._available_sheets_hint
        return sheet_available(sheet_name, self.parser.validate_sheet_exists)

    @timed
    def import_all(self) -> dict:
        """Import all available data from Excel file.

        Returns:
            Dictionary with import statistics
        """
        stats = {"errors": []}

        log_import_start(
            logger=logger,
            project_name=self.project_name,
            result_set_name=self.result_set_name,
            file_name=self.file_path.name,
            result_types=self.result_types if hasattr(self, "result_types") else None,
        )

        try:
            with self.session_scope() as session:
                meta_importer = MetadataImporter(
                    session=session,
                    project_name=self.project_name,
                    result_set_name=self.result_set_name,
                )
                stats, project_id, category_id = meta_importer.ensure_project_and_result_set()

                self._project_id = project_id
                self.result_category_id = category_id
                self.result_set_id = stats["result_set_id"]

                self._run_import_tasks(session, project_id, stats)

                # Generate cache for fast display after all imports (optional)
                if self._generate_cache_after_import:
                    with self._phase_timer.measure("cache_generation"):
                        self._generate_cache(session, project_id, self.result_set_id)
                        self._cache_generated = True

        except Exception as e:
            stats.setdefault("errors", []).append(str(e))
            log_import_failure(
                logger=logger,
                project_name=self.project_name,
                result_set_name=self.result_set_name,
                file_name=self.file_path.name,
                error=e,
            )
            raise
        finally:
            stats["phase_timings"] = self._phase_timer.as_list()
            log_phase_timings(
                logger=logger,
                project_name=self.project_name,
                result_set_name=self.result_set_name,
                file_name=self.file_path.name,
                phase_timings=stats["phase_timings"],
            )

        log_import_complete(
            logger=logger,
            project_name=self.project_name,
            result_set_name=self.result_set_name,
            file_name=self.file_path.name,
            stats=stats,
        )

        return stats

    def _run_import_tasks(self, session, project_id: int, stats: dict) -> None:
        run_import_tasks(
            tasks=self._import_tasks,
            should_import=self._should_import,
            sheet_available=self._sheet_available,
            get_handler=lambda name: getattr(self, name, None),
            phase_timer=self._phase_timer,
            session=session,
            project_id=project_id,
            stats=stats,
            file_name=self.file_path.name,
        )

    def _task_sheets_available(self, task: ImportTask) -> bool:
        return task_sheets_available(task, self._sheet_available)

    @staticmethod
    def _merge_task_stats(stats: dict, task_stats: Optional[dict]) -> None:
        merge_task_stats(stats, task_stats)

    def _import_story_drifts(self, session, project_id: int) -> dict:
        """Import story drift data."""
        try:
            from .global_importer import GlobalImporter

            importer = GlobalImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_story_drifts()
        except Exception as e:
            raise ValueError(f"Error importing story drifts: {e}")

    def _import_story_accelerations(self, session, project_id: int) -> dict:
        """Import story acceleration data from Diaphragm Accelerations sheet."""
        try:
            from .global_importer import GlobalImporter

            importer = GlobalImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_story_accelerations()
        except Exception as e:
            raise ValueError(f"Error importing story accelerations: {e}")

    def _import_story_forces(self, session, project_id: int) -> dict:
        """Import story force data."""
        try:
            from .global_importer import GlobalImporter

            importer = GlobalImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_story_forces()
        except Exception as e:
            raise ValueError(f"Error importing story forces: {e}")

    def _import_joint_displacements(self, session, project_id: int) -> dict:
        """Import joint displacement data (global story displacements)."""
        try:
            from .global_importer import GlobalImporter

            importer = GlobalImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_joint_displacements()
        except Exception as e:
            raise ValueError(f"Error importing joint displacements: {e}")

    def _import_pier_forces(self, session, project_id: int) -> dict:
        """Import pier force data (element-level shear forces)."""
        from .element_importer import ElementImporter

        try:
            importer = ElementImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_pier_forces()
        except Exception as e:
            raise ValueError(f"Error importing pier forces: {e}")

    def _import_quad_rotations(self, session, project_id: int) -> dict:
        """Import quad strain gauge rotation data (element-level rotations)."""
        from .element_importer import ElementImporter

        try:
            importer = ElementImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_quad_rotations()
        except Exception as e:
            raise ValueError(f"Error importing quad rotations: {e}")

    def _import_column_forces(self, session, project_id: int) -> dict:
        """Import column force data (element-level shear forces)."""
        from .element_importer import ElementImporter

        try:
            importer = ElementImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_column_forces()
        except Exception as e:
            raise ValueError(f"Error importing column forces: {e}")

    def _import_column_axials(self, session, project_id: int) -> dict:
        """Import column axial force data (minimum P values)."""
        from .element_importer import ElementImporter

        try:
            importer = ElementImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_column_axials()
        except Exception as e:
            raise ValueError(f"Error importing column axials: {e}")

    def _import_column_rotations(self, session, project_id: int) -> dict:
        """Import column rotation data from Fiber Hinge States (R2 and R3 rotations)."""
        from .element_importer import ElementImporter

        try:
            importer = ElementImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_column_rotations()
        except Exception as e:
            raise ValueError(f"Error importing column rotations: {e}")

    def _import_beam_rotations(self, session, project_id: int) -> dict:
        """Import beam rotation data from Hinge States (R3 Plastic rotations)."""
        from .element_importer import ElementImporter

        try:
            importer = ElementImporter(
                session=session,
                parser=self.parser,
                project_id=project_id,
                result_category_id=self.result_category_id,
            )
            return importer.import_beam_rotations()
        except Exception as e:
            raise ValueError(f"Error importing beam rotations: {e}")

    def _import_soil_pressures(self, session, project_id: int) -> dict:
        """Delegate soil pressure import to foundation importer."""
        from .foundation_importer import FoundationImporter

        importer = FoundationImporter(
            session=session,
            parser=self.parser,
            project_id=project_id,
            result_set_id=self.result_set_id,
        )
        return importer.import_soil_pressures()

    def _import_vertical_displacements(self, session, project_id: int) -> dict:
        """Delegate vertical displacement import to foundation importer."""
        from .foundation_importer import FoundationImporter

        importer = FoundationImporter(
            session=session,
            parser=self.parser,
            project_id=project_id,
            result_set_id=self.result_set_id,
        )
        return importer.import_vertical_displacements()

    def _generate_cache(self, session, project_id: int, result_set_id: int):
        """Generate wide-format cache tables for fast tabular display."""
        from .cache_builder import CacheBuilder

        builder = CacheBuilder(
            session=session,
            project_id=project_id,
            result_set_id=result_set_id,
            result_category_id=self.result_category_id,
        )
        builder.generate_all()

    def generate_cache_if_needed(self) -> None:
        """Run cache generation once if deferred."""
        if self._cache_generated or self._project_id is None or self.result_set_id is None:
            return
        with self.session_scope() as session:
            self._generate_cache(session, self._project_id, self.result_set_id)
            self._cache_generated = True
