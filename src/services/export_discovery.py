"""Result discovery/query helpers for export."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
from sqlalchemy.orm import Session
from types import SimpleNamespace
from database.repository import ProjectRepository, ResultSetRepository
from database.models import GlobalResultsCache, ElementResultsCache, JointResultsCache, PushoverCase


class ExportDiscovery:
    """Discovers available result types and builds DataFrames for export."""

    def __init__(self, session_factory, context):
        self._session_factory = session_factory
        self.context = context

    def discover_and_write(
        self,
        writer,
        result_set_id: int,
        result_sets: list,
        progress_callback,
    ) -> Dict[str, List[str]]:
        from database.models import (
            StoryDrift,
            StoryAcceleration,
            StoryForce,
            StoryDisplacement,
            ElementResultsCache,
        )

        result_sheets: Dict[str, List[str]] = {"global": [], "element": []}

        with self.context.session() as session:
            self._export_global_tables(session, writer, result_set_id, result_sheets, progress_callback)
            self._export_element_tables(session, writer, result_set_id, result_sheets, progress_callback)

        return result_sheets

    def _export_global_tables(
        self,
        session: Session,
        writer,
        result_set_id: int,
        result_sheets: Dict[str, List[str]],
        progress_callback,
    ) -> None:
        from database.models import StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement, ResultCategory

        # Query directions filtered by result_set_id through ResultCategory
        directions = session.query(StoryDrift.direction).join(
            ResultCategory, StoryDrift.result_category_id == ResultCategory.id
        ).filter(ResultCategory.result_set_id == result_set_id).distinct().all()
        for direction, in directions:
            config_key = f"Drifts_{direction}"
            df = self._get_normalized_drift_dataframe(session, result_set_id, direction)
            if df is not None and not df.empty:
                sheet_name = config_key[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                result_sheets["global"].append(config_key)
                if progress_callback:
                    progress_callback(f"Exported {config_key}", 0, 1)

        directions = session.query(StoryAcceleration.direction).join(
            ResultCategory, StoryAcceleration.result_category_id == ResultCategory.id
        ).filter(ResultCategory.result_set_id == result_set_id).distinct().all()
        for direction, in directions:
            config_key = f"Accelerations_{direction}"
            df = self._get_normalized_acceleration_dataframe(session, result_set_id, direction)
            if df is not None and not df.empty:
                sheet_name = config_key[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                result_sheets["global"].append(config_key)
                if progress_callback:
                    progress_callback(f"Exported {config_key}", 0, 1)

        directions = session.query(StoryForce.direction).join(
            ResultCategory, StoryForce.result_category_id == ResultCategory.id
        ).filter(ResultCategory.result_set_id == result_set_id).distinct().all()
        for direction, in directions:
            config_key = f"Forces_{direction}"
            df = self._get_normalized_force_dataframe(session, result_set_id, direction)
            if df is not None and not df.empty:
                sheet_name = config_key[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                result_sheets["global"].append(config_key)
                if progress_callback:
                    progress_callback(f"Exported {config_key}", 0, 1)

        directions = session.query(StoryDisplacement.direction).join(
            ResultCategory, StoryDisplacement.result_category_id == ResultCategory.id
        ).filter(ResultCategory.result_set_id == result_set_id).distinct().all()
        for direction, in directions:
            config_key = f"Displacements_{direction}"
            df = self._get_normalized_displacement_dataframe(session, result_set_id, direction)
            if df is not None and not df.empty:
                sheet_name = config_key[:31]
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                result_sheets["global"].append(config_key)
                if progress_callback:
                    progress_callback(f"Exported {config_key}", 0, 1)

    def _export_element_tables(
        self,
        session: Session,
        writer,
        result_set_id: int,
        result_sheets: Dict[str, List[str]],
        progress_callback,
    ) -> None:
        from database.models import ElementResultsCache, Element, Story, ResultSet
        from database.repository import ElementCacheRepository

        # Check if this is a Pushover result set
        result_set = session.query(ResultSet).filter(ResultSet.id == result_set_id).first()
        is_pushover = result_set and result_set.analysis_type == 'Pushover'

        # Export BeamRotations with special wide-format handling
        self._export_beam_rotations_wide(session, writer, result_set_id, result_sheets, is_pushover, progress_callback)

        element_types = session.query(ElementResultsCache.result_type).filter(
            ElementResultsCache.result_set_id == result_set_id
        ).distinct().all()

        element_cache_repo = ElementCacheRepository(session)

        for result_type, in element_types:
            # Skip BeamRotations - already exported above
            if result_type.startswith("BeamRotations"):
                continue

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
                continue

            rows = []
            for cache_entry, element, story in entries:
                row = {"Element": element.name, "Story": story.name}
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

            sheet_name = result_type[:31]
            df.to_excel(writer, sheet_name=sheet_name, index=False)
            result_sheets["element"].append(result_type)
            if progress_callback:
                progress_callback(f"Exported {result_type}", 0, 1)

    def _export_beam_rotations_wide(
        self,
        session: Session,
        writer,
        result_set_id: int,
        result_sheets: Dict[str, List[str]],
        is_pushover: bool,
        progress_callback,
    ) -> None:
        """Export beam rotations in wide format matching ETDB_Functions.get_beams_plastic_hinges.

        Format: Story | Frame/Wall | Unique Name | Step Type | Hinge | Hinge ID | Rel Dist | <LC1> | <LC2> | ... | Avg | Max | Min
        Preserves all source rows including both Max/Min step types and both Rel Dist 0/1.
        """
        from database.models import BeamRotation, Element, Story, LoadCase, ResultCategory

        # Query all beam rotations for this result set, ordered by source order
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
            BeamRotation.story_sort_order,  # Preserves source Excel row order
            LoadCase.name
        )

        results = query.all()
        if not results:
            return

        # Get unique load cases in order
        load_cases = []
        seen_lc = set()
        for br, elem, story, lc in results:
            if lc.name not in seen_lc:
                load_cases.append(lc.name)
                seen_lc.add(lc.name)

        # Build row key to identify unique rows (same as old script uses first load case as template)
        # Key: (story_sort_order) to preserve exact source order
        first_lc = load_cases[0] if load_cases else None
        if not first_lc:
            return

        # Get template rows from first load case
        template_rows = []
        row_data = {}  # {row_key: {lc_name: value, ...}}

        for br, elem, story, lc in results:
            row_key = br.story_sort_order  # This is the source row index

            if row_key not in row_data:
                row_data[row_key] = {
                    "Story": story.name,
                    "Frame/Wall": elem.name,
                    "Unique Name": br.generated_hinge or "",
                    "Step Type": br.step_type or "",
                    "Hinge": br.hinge or "",
                    "Hinge ID": br.generated_hinge or "",
                    "Rel Dist": br.rel_dist if br.rel_dist is not None else 0.0,
                }

            row_data[row_key][lc.name] = br.r3_plastic

        if not row_data:
            return

        # Sort by row key (source order)
        sorted_keys = sorted(row_data.keys())

        # Build DataFrame
        rows = []
        for key in sorted_keys:
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

        sheet_name = "BeamRotations_R3Plastic"[:31]
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        result_sheets["element"].append("BeamRotations_R3Plastic")
        if progress_callback:
            progress_callback("Exported BeamRotations_R3Plastic", 0, 1)

    def _get_normalized_drift_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        from database.models import StoryDrift, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label("Story"),
            LoadCase.name.label("LoadCase"),
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

        data = {}
        for story, load_case, value in results:
            data.setdefault(story, {"Story": story})[load_case] = value
        return pd.DataFrame(list(data.values()))


    def _get_normalized_acceleration_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        from database.models import StoryAcceleration, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label("Story"),
            LoadCase.name.label("LoadCase"),
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

        data = {}
        for story, load_case, value in results:
            data.setdefault(story, {"Story": story})[load_case] = value
        return pd.DataFrame(list(data.values()))


    def _get_normalized_force_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        from database.models import StoryForce, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label("Story"),
            LoadCase.name.label("LoadCase"),
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

        data = {}
        for story, load_case, value in results:
            data.setdefault(story, {"Story": story})[load_case] = value
        return pd.DataFrame(list(data.values()))

    def _get_normalized_displacement_dataframe(self, session, result_set_id: int, direction: str) -> pd.DataFrame:
        from database.models import StoryDisplacement, Story, LoadCase, ResultCategory

        query = session.query(
            Story.name.label("Story"),
            LoadCase.name.label("LoadCase"),
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

        data = {}
        for story, load_case, value in results:
            data.setdefault(story, {"Story": story})[load_case] = value
        return pd.DataFrame(list(data.values()))


# Backward compatibility for older tests/imports
ExportDiscoveryService = ExportDiscovery
__all__ = ["ExportDiscovery", "ExportDiscoveryService"]


class ExportDiscoveryService:
    """Backward-compatible discovery service used by legacy tests."""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def discover_result_sets(self, project_name: str, analysis_context: str):
        session = self.session_factory()
        try:
            project_repo = ProjectRepository(session)
            result_set_repo = ResultSetRepository(session)
            project = project_repo.get_by_name(project_name)
            if not project:
                return []
            sets = result_set_repo.get_by_project(project.id)
            return [
                rs for rs in sets
                if (rs.analysis_type or "NLTHA") == analysis_context
            ]
        finally:
            session.close()

    def discover_result_types(self, result_set_ids: List[int], analysis_context: str):
        session = self.session_factory()
        try:
            global_types = set(
                rt for (rt,) in session.query(GlobalResultsCache.result_type)
                .filter(GlobalResultsCache.result_set_id.in_(result_set_ids))
                .distinct()
                .all()
            )

            element_types_raw = set(
                rt for (rt,) in session.query(ElementResultsCache.result_type)
                .filter(ElementResultsCache.result_set_id.in_(result_set_ids))
                .distinct()
                .all()
            )
            element_types = {rt.split("_")[0] for rt in element_types_raw}

            joint_types_raw = set(
                rt for (rt,) in session.query(JointResultsCache.result_type)
                .filter(JointResultsCache.result_set_id.in_(result_set_ids))
                .distinct()
                .all()
            )
            joint_types = {rt.split("_")[0] for rt in joint_types_raw}

            if analysis_context == "Pushover":
                # If pushover cases exist, add Curves to global types
                has_curves = session.query(PushoverCase.id).filter(
                    PushoverCase.result_set_id.in_(result_set_ids)
                ).first()
                if has_curves:
                    global_types.add("Curves")

            return SimpleNamespace(
                global_types=sorted(global_types),
                element_types=sorted(element_types),
                joint_types=sorted(joint_types),
            )
        finally:
            session.close()
