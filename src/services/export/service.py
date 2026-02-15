"""Export service for RPS projects.

Provides export functionality for result data in Excel and CSV formats.
"""
import logging
from typing import Optional, Callable
from pathlib import Path
from dataclasses import dataclass
import pandas as pd

from utils.timing import PhaseTimer
from utils.error_handling import timed
from .utils import (
    extract_direction,
    extract_base_type,
    build_filename,
    get_result_config,
)
from .writer import ExportWriter
from .serialization import (
    serialize_absolute_maxmin_drifts,
    serialize_element_cache,
    serialize_global_cache,
    serialize_quad_rotations,
    serialize_story_accelerations,
    serialize_story_displacements,
    serialize_story_drifts,
    serialize_story_forces,
    serialize_wall_shears,
)
from database.models import GlobalResultsCache

from .excel_writer import ProjectExcelExporter
from .curve_exporter import CurveExporter

logger = logging.getLogger(__name__)


@dataclass
class ExportOptions:
    """Options for exporting result data (MVP: single result type)."""

    result_set_id: int
    result_type: str  # e.g., "Drifts_X", "QuadRotations"
    output_path: Path
    format: str = "excel"  # "excel" or "csv"
    include_maxmin: bool = False  # For future implementation


@dataclass
class ProjectExportExcelOptions:
    """Options for Excel project export."""
    output_path: Path
    include_all_results: bool = True
    result_set_ids: Optional[list[int]] = None  # None = all sets


class ExportService:
    """Service for exporting result data.

    MVP Implementation: Exports single result type to Excel or CSV.

    Args:
        project_context: ProjectContext instance with session access
        result_service: ResultDataService instance for data retrieval
    """

    APP_VERSION = "2.7"

    def __init__(self, project_context, result_service):
        """Initialize export service.

        Args:
            project_context: ProjectContext with session() and session_factory()
            result_service: ResultDataService for retrieving datasets
        """
        self.context = project_context
        self.result_service = result_service
        self._raw_value_types = {"Drifts", "QuadRotations", "ColumnRotations", "BeamRotations"}

    def prepare_dataset_for_export(self, dataset, result_type: str):
        """Return a copy of dataset data with percentage multipliers removed for export."""
        if dataset is None or dataset.data is None:
            return None

        base_type = extract_base_type(result_type)
        if base_type not in self._raw_value_types:
            return dataset.data

        multiplier = getattr(getattr(dataset, "config", None), "multiplier", 1.0) or 1.0
        if multiplier in (0, 1.0):
            return dataset.data

        df = dataset.data.copy(deep=True)
        numeric_cols = df.select_dtypes(include="number").columns
        if len(numeric_cols) > 0:
            df[numeric_cols] = df[numeric_cols] / multiplier
        return df

    @timed
    def export_result_type(
        self,
        options: ExportOptions,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """Export single result type to file.

        Args:
            options: Export options specifying what and where to export
            progress_callback: Optional callback(message, current, total) for progress updates

        Raises:
            ValueError: If result_type is unknown
            IOError: If file cannot be written
        """
        timer = PhaseTimer(
            {"result_type": options.result_type, "result_set_id": options.result_set_id}
        )
        writer = ExportWriter(progress_callback)

        # Step 1: Validate result type and get configuration
        config = get_result_config(options.result_type)

        # Step 2: Extract direction and base type (handles directionless results)
        direction = extract_direction(options.result_type, config)
        base_type = extract_base_type(options.result_type)

        writer.progress_callback("Loading data...", 1, 3)

        # Step 3: Get dataset using correct ResultDataService API (no element_id parameter!)
        with timer.measure("load_dataset"):
            dataset = self.result_service.get_standard_dataset(
                result_type=base_type,
                direction=direction,
                result_set_id=options.result_set_id
            )

        with timer.measure("write_output"):
            df_to_write = self.prepare_dataset_for_export(dataset, options.result_type)
            if df_to_write is None:
                df_to_write = dataset.data
            writer.write_dataset(df_to_write, options.output_path, options.format)

        logger.info(
            "export_result_type.complete",
            extra={
                "output_path": str(options.output_path),
                "timings": timer.as_list(),
            },
        )

    def get_available_result_types(self, result_set_id: int) -> list[str]:
        """Get list of available result types for a result set.

        Queries the cache to determine which result types have data.

        Args:
            result_set_id: ID of result set to query

        Returns:
            Sorted list of result type names with data
        """
        available = []

        # Use context.session() to create session (correct pattern)
        with self.context.session() as session:
            # Query GlobalResultsCache for available types
            global_types = session.query(GlobalResultsCache.result_type).filter(
                GlobalResultsCache.result_set_id == result_set_id
            ).distinct().all()

            available.extend([rt[0] for rt in global_types])

        return sorted(set(available))

    def build_filename(self, result_type: str, format: str) -> str:
        """Build filename matching Old_scripts naming convention."""
        return build_filename(result_type, format)

    def _get_result_config(self, result_type: str):
        """Get result config for a result type."""
        return get_result_config(result_type)

    def get_element_export_dataframe(self, result_type: str, result_set_id: int, is_pushover: bool = False):
        """Get combined DataFrame for all elements of a result type.

        Args:
            result_type: Full result type (e.g., "WallShears_V2", "QuadRotations", "BeamRotations")
            result_set_id: Result set ID
            is_pushover: If True, skip summary columns (Average, Maximum, Minimum)

        Returns:
            pd.DataFrame with all elements combined, or None if no data
        """
        import pandas as pd
        from database.models import ElementResultsCache, Element, Story
        from database.repositories import ElementCacheRepository

        # Special handling for BeamRotations - use wide format with all source rows
        if result_type.startswith("BeamRotations"):
            return self._get_beam_rotations_wide_dataframe(result_set_id, is_pushover)

        # Get all elements with data for this result type
        with self.context.session() as session:
            element_cache_repo = ElementCacheRepository(session)

            # Query all cache entries for this result type
            # Order by cache entry id to preserve source Excel order
            entries = session.query(
                ElementResultsCache, Element, Story
            ).join(
                Element, ElementResultsCache.element_id == Element.id
            ).join(
                Story, ElementResultsCache.story_id == Story.id
            ).filter(
                ElementResultsCache.result_set_id == result_set_id,
                ElementResultsCache.result_type == result_type
            ).order_by(
                ElementResultsCache.id
            ).all()

            if not entries:
                return None

            # Build rows
            rows = []
            for cache_entry, element, story in entries:
                row = {"Element": element.name, "Story": story.name}
                # Merge results_matrix (load case columns)
                if cache_entry.results_matrix:
                    row.update(cache_entry.results_matrix)
                rows.append(row)

            df = pd.DataFrame(rows)

            # Add summary columns (Average, Maximum, Minimum) - only for NLTHA, not Pushover
            if not df.empty and not is_pushover:
                non_data_cols = ["Element", "Story"]
                load_case_columns = [col for col in df.columns if col not in non_data_cols]

                if load_case_columns:
                    df["Average"] = df[load_case_columns].mean(axis=1)
                    df["Maximum"] = df[load_case_columns].max(axis=1)
                    df["Minimum"] = df[load_case_columns].min(axis=1)

            return df

    def _get_beam_rotations_wide_dataframe(self, result_set_id: int, is_pushover: bool = False):
        """Get beam rotations in wide format matching ETDB_Functions.get_beams_plastic_hinges.

        Format: Story | Frame/Wall | Unique Name | Step Type | Hinge | Hinge ID | Rel Dist | <LC1> | <LC2> | ... | Avg | Max | Min
        Preserves all source rows including both Max/Min step types and both Rel Dist 0/1.
        """
        import pandas as pd
        from sqlalchemy import text
        from database.models import BeamRotation, Element, Story, LoadCase, ResultCategory

        with self.context.session() as session:
            # Check if step_type column exists (for backward compatibility with old DBs)
            try:
                has_step_type = True
                session.execute(text("SELECT step_type FROM beam_rotations LIMIT 1"))
            except Exception:
                has_step_type = False

            # Query all beam rotations for this result set, ordered by BeamRotation.id to preserve source order
            query = session.query(
                BeamRotation, Element, Story, LoadCase
            ).join(
                Element, BeamRotation.element_id == Element.id
            ).join(
                Story, BeamRotation.story_id == Story.id
            ).join(
                LoadCase, BeamRotation.load_case_id == LoadCase.id
            ).join(
                ResultCategory, BeamRotation.result_category_id == ResultCategory.id
            ).filter(
                ResultCategory.result_set_id == result_set_id
            ).order_by(
                BeamRotation.id  # Use record ID to preserve insertion order
            )

            results = query.all()
            if not results:
                return None

            # Get unique load cases in lexicographical order (TH01, TH02, ...)
            load_cases = sorted({lc.name for br, elem, story, lc in results})

            if not load_cases:
                return None

            # Build row data using composite key (element, story, hinge, rel_dist, step_type)
            # This groups by unique hinge location
            row_data = {}  # {row_key: {col_name: value, ...}}
            row_order = []  # Track order of first appearance

            for br, elem, story, lc in results:
                step_type_val = ""
                if has_step_type:
                    try:
                        step_type_val = br.step_type or ""
                    except Exception:
                        pass

                # Create composite key for unique row identification
                row_key = (
                    elem.id,
                    story.id,
                    br.hinge or "",
                    br.generated_hinge or "",
                    br.rel_dist if br.rel_dist is not None else 0.0,
                    step_type_val
                )

                if row_key not in row_data:
                    row_order.append(row_key)
                    row_data[row_key] = {
                        "Story": story.name,
                        "Frame/Wall": elem.name,
                        "Unique Name": br.generated_hinge or "",
                        "Step Type": step_type_val,
                        "Hinge": br.hinge or "",
                        "Hinge ID": br.generated_hinge or "",
                        "Rel Dist": br.rel_dist if br.rel_dist is not None else 0.0,
                    }

                row_data[row_key][lc.name] = br.r3_plastic

            if not row_data:
                return None

            # Build DataFrame in order of first appearance
            rows = []
            for key in row_order:
                rows.append(row_data[key])

            df = pd.DataFrame(rows)

            # Reorder columns: metadata first, then load cases, then summary
            meta_cols = ["Story", "Frame/Wall", "Unique Name", "Step Type", "Hinge", "Hinge ID", "Rel Dist"]
            lc_cols = [c for c in load_cases if c in df.columns]
            df = df[[c for c in meta_cols if c in df.columns] + lc_cols]

            # Add summary columns
            if lc_cols:
                df["Avg"] = df[lc_cols].mean(axis=1)
                df["Max"] = df[lc_cols].max(axis=1)
                df["Min"] = df[lc_cols].min(axis=1)

            return df

    # ===== PROJECT EXPORT TO EXCEL =====

    @timed
    def export_project_excel(
        self,
        options: ProjectExportExcelOptions,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """Export complete project to Excel workbook with metadata."""
        exporter = ProjectExcelExporter(self.context, self.result_service, self.APP_VERSION)
        exporter.export_project_excel(options, progress_callback)

    def _gather_project_metadata(self) -> dict:
        """Gather all project metadata for export."""
        from database.session import get_catalog_session
        from database.catalog_repository import CatalogProjectRepository
        from services.project_service import get_project_summary
        from database.models import ResultSet, ResultCategory, LoadCase, Story, Element

        # Get catalog entry
        catalog_session = get_catalog_session()
        try:
            catalog_repo = CatalogProjectRepository(catalog_session)
            catalog_project = catalog_repo.get_by_slug(self.context.slug)
            if not catalog_project:
                raise ValueError(f"Project '{self.context.slug}' not found in catalog")
        finally:
            catalog_session.close()

        # Get project summary
        summary = get_project_summary(self.context)

        # Query project database
        with self.context.session() as session:
            # Result sets
            result_sets = session.query(ResultSet).filter(
                ResultSet.project_id == self.result_service.project_id
            ).all()

            # Result categories (no project_id, linked via result_set_id)
            result_set_ids = [rs.id for rs in result_sets]
            result_categories = session.query(ResultCategory).filter(
                ResultCategory.result_set_id.in_(result_set_ids)
            ).all() if result_set_ids else []

            # Load cases
            load_cases = session.query(LoadCase).filter(
                LoadCase.project_id == self.result_service.project_id
            ).all()

            # Stories
            stories = session.query(Story).filter(
                Story.project_id == self.result_service.project_id
            ).order_by(Story.sort_order).all()

            # Elements
            elements = session.query(Element).filter(
                Element.project_id == self.result_service.project_id
            ).order_by(Element.element_type, Element.name).all()

            return {
                'catalog_project': catalog_project,
                'summary': summary,
                'result_sets': result_sets,
                'result_categories': result_categories,
                'load_cases': load_cases,
                'stories': stories,
                'elements': elements,
            }

    def _get_normalized_drift_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        """Get drift data from story_drifts table."""
        from database.models import StoryDrift, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label('Story'),
            LoadCase.name.label('LoadCase'),
            StoryDrift.drift
        ).join(
            Story, StoryDrift.story_id == Story.id
        ).join(
            LoadCase, StoryDrift.load_case_id == LoadCase.id
        ).join(
            ResultCategory, StoryDrift.result_category_id == ResultCategory.id
        ).filter(
            StoryDrift.direction == direction,
            ResultCategory.result_set_id == result_set_id
        ).order_by(
            StoryDrift.story_sort_order,
            LoadCase.name
        )

        results = query.all()
        if not results:
            return None

        # Pivot to wide format: Story | LC1 | LC2 | ...
        data = {}
        for story, load_case, value in results:
            if story not in data:
                data[story] = {'Story': story}
            data[story][load_case] = value

        return pd.DataFrame(list(data.values()))

    def _get_normalized_acceleration_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        """Get acceleration data from story_accelerations table."""
        from database.models import StoryAcceleration, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label('Story'),
            LoadCase.name.label('LoadCase'),
            StoryAcceleration.acceleration
        ).join(
            Story, StoryAcceleration.story_id == Story.id
        ).join(
            LoadCase, StoryAcceleration.load_case_id == LoadCase.id
        ).join(
            ResultCategory, StoryAcceleration.result_category_id == ResultCategory.id
        ).filter(
            StoryAcceleration.direction == direction,
            ResultCategory.result_set_id == result_set_id
        ).order_by(
            StoryAcceleration.story_sort_order,
            LoadCase.name
        )

        results = query.all()
        if not results:
            return None

        # Pivot to wide format
        data = {}
        for story, load_case, value in results:
            if story not in data:
                data[story] = {'Story': story}
            data[story][load_case] = value

        return pd.DataFrame(list(data.values()))

    def _get_normalized_force_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        """Get force data from story_forces table."""
        from database.models import StoryForce, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label('Story'),
            LoadCase.name.label('LoadCase'),
            StoryForce.force
        ).join(
            Story, StoryForce.story_id == Story.id
        ).join(
            LoadCase, StoryForce.load_case_id == LoadCase.id
        ).join(
            ResultCategory, StoryForce.result_category_id == ResultCategory.id
        ).filter(
            StoryForce.direction == direction,
            ResultCategory.result_set_id == result_set_id
        ).order_by(
            StoryForce.story_sort_order,
            LoadCase.name
        )

        results = query.all()
        if not results:
            return None

        # Pivot to wide format
        data = {}
        for story, load_case, value in results:
            if story not in data:
                data[story] = {'Story': story}
            data[story][load_case] = value

        return pd.DataFrame(list(data.values()))

    def _get_normalized_displacement_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        """Get displacement data from story_displacements table."""
        from database.models import StoryDisplacement, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label('Story'),
            LoadCase.name.label('LoadCase'),
            StoryDisplacement.displacement
        ).join(
            Story, StoryDisplacement.story_id == Story.id
        ).join(
            LoadCase, StoryDisplacement.load_case_id == LoadCase.id
        ).join(
            ResultCategory, StoryDisplacement.result_category_id == ResultCategory.id
        ).filter(
            StoryDisplacement.direction == direction,
            ResultCategory.result_set_id == result_set_id
        ).order_by(
            StoryDisplacement.story_sort_order,
            LoadCase.name
        )

        results = query.all()
        if not results:
            return None

        # Pivot to wide format
        data = {}
        for story, load_case, value in results:
            if story not in data:
                data[story] = {'Story': story}
            data[story][load_case] = value

        return pd.DataFrame(list(data.values()))


    def _serialize_story_drifts(self, session) -> list:
        """Serialize all story_drifts table data."""
        return serialize_story_drifts(session)

    def _serialize_story_accelerations(self, session) -> list:
        """Serialize all story_accelerations table data."""
        return serialize_story_accelerations(session)

    def _serialize_story_forces(self, session) -> list:
        """Serialize all story_forces table data."""
        return serialize_story_forces(session)

    def _serialize_story_displacements(self, session) -> list:
        """Serialize all story_displacements table data."""
        return serialize_story_displacements(session)

    def _serialize_absolute_maxmin_drifts(self, session) -> list:
        """Serialize all absolute_maxmin_drifts table data."""
        return serialize_absolute_maxmin_drifts(session)

    def _serialize_quad_rotations(self, session) -> list:
        """Serialize all quad_rotations table data."""
        return serialize_quad_rotations(session)

    def _serialize_wall_shears(self, session) -> list:
        """Serialize all wall_shears table data."""
        return serialize_wall_shears(session)

    def _serialize_global_cache(self, session) -> list:
        """Serialize all global_results_cache table data."""
        return serialize_global_cache(session)

    def _serialize_element_cache(self, session) -> list:
        """Serialize all element_results_cache table data."""
        return serialize_element_cache(session)

    # ===== PUSHOVER CURVES EXPORT =====

    def export_pushover_curves(
        self,
        result_set_id: int,
        output_path: Path,
        progress_callback: Optional[Callable[[str, int, int], None]] = None
    ) -> None:
        """Export all pushover curves for a result set to Excel."""
        CurveExporter(self.context).export_pushover_curves(result_set_id, output_path, progress_callback)
