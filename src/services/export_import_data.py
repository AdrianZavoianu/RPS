"""IMPORT_DATA sheet serialization helpers for export."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict

import pandas as pd


class ImportDataBuilder:
    """Builds the IMPORT_DATA sheet with normalized and cache data dumps."""

    def __init__(self, context, app_version: str) -> None:
        self.context = context
        self.app_version = app_version

    def write_import_data_sheet(self, writer, metadata: dict, result_sheets: dict) -> None:
        """Write IMPORT_DATA sheet with complete database dump."""
        with self.context.session() as session:
            import_data = {
                "version": self.app_version,
                "export_timestamp": datetime.now().isoformat(),
                "project": {
                    "name": metadata["catalog_project"].name,
                    "slug": metadata["catalog_project"].slug,
                    "description": metadata["catalog_project"].description or "",
                    "created_at": metadata["catalog_project"].created_at.isoformat(),
                },
                "result_sets": [
                    {
                        "name": rs.name,
                        "description": rs.description or "",
                        "created_at": rs.created_at.isoformat() if rs.created_at else None,
                    }
                    for rs in metadata["result_sets"]
                ],
                "result_categories": [
                    {
                        "category_name": rc.category_name,
                        "result_set_name": next(
                            (rs.name for rs in metadata["result_sets"] if rs.id == rc.result_set_id),
                            None,
                        ),
                        "category_type": rc.category_type,
                    }
                    for rc in metadata.get("result_categories", [])
                ],
                "load_cases": [
                    {"name": lc.name, "description": lc.description or ""}
                    for lc in metadata["load_cases"]
                ],
                "stories": [
                    {"name": s.name, "sort_order": s.sort_order, "elevation": s.elevation or 0.0}
                    for s in metadata["stories"]
                ],
                "elements": [
                    {"name": e.name, "unique_name": e.unique_name or "", "element_type": e.element_type}
                    for e in metadata["elements"]
                ],
                "result_sheet_mapping": result_sheets,
                "normalized_data": {
                    "story_drifts": self._serialize_story_drifts(session),
                    "story_accelerations": self._serialize_story_accelerations(session),
                    "story_forces": self._serialize_story_forces(session),
                    "story_displacements": self._serialize_story_displacements(session),
                    "absolute_maxmin_drifts": self._serialize_absolute_maxmin_drifts(session),
                    "quad_rotations": self._serialize_quad_rotations(session),
                    "wall_shears": self._serialize_wall_shears(session),
                },
                "cache_data": {
                    "global_results_cache": self._serialize_global_cache(session),
                    "element_results_cache": self._serialize_element_cache(session),
                },
            }

            json_str = json.dumps(import_data, separators=(",", ":"))
            chunk_size = 30000
            chunks = [json_str[i : i + chunk_size] for i in range(0, len(json_str), chunk_size)]
            df = pd.DataFrame(chunks, columns=["import_metadata"])
            df.to_excel(writer, sheet_name="IMPORT_DATA", index=False)

    def _serialize_story_drifts(self, session) -> list:
        from database.models import StoryDrift, Story, LoadCase

        results = (
            session.query(
                Story.name.label("story_name"),
                LoadCase.name.label("load_case_name"),
                StoryDrift.direction,
                StoryDrift.drift,
                StoryDrift.max_drift,
                StoryDrift.min_drift,
                StoryDrift.story_sort_order,
            )
            .join(Story, StoryDrift.story_id == Story.id)
            .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
            .all()
        )

        return [
            {
                "story_name": r.story_name,
                "load_case_name": r.load_case_name,
                "direction": r.direction,
                "drift": r.drift,
                "max_drift": r.max_drift,
                "min_drift": r.min_drift,
                "story_sort_order": r.story_sort_order,
            }
            for r in results
        ]

    def _serialize_story_accelerations(self, session) -> list:
        from database.models import StoryAcceleration, Story, LoadCase, ResultCategory, ResultSet

        results = (
            session.query(
                Story.name.label("story_name"),
                LoadCase.name.label("load_case_name"),
                ResultSet.name.label("result_set_name"),
                ResultCategory.category_name.label("result_category_name"),
                StoryAcceleration.direction,
                StoryAcceleration.acceleration,
                StoryAcceleration.max_acceleration,
                StoryAcceleration.min_acceleration,
                StoryAcceleration.story_sort_order,
            )
            .join(Story, StoryAcceleration.story_id == Story.id)
            .join(LoadCase, StoryAcceleration.load_case_id == LoadCase.id)
            .join(ResultCategory, StoryAcceleration.result_category_id == ResultCategory.id)
            .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
            .all()
        )

        return [
            {
                "story_name": r.story_name,
                "load_case_name": r.load_case_name,
                "result_set_name": r.result_set_name,
                "result_category_name": r.result_category_name,
                "direction": r.direction,
                "acceleration": r.acceleration,
                "max_acceleration": r.max_acceleration,
                "min_acceleration": r.min_acceleration,
                "story_sort_order": r.story_sort_order,
            }
            for r in results
        ]

    def _serialize_story_forces(self, session) -> list:
        from database.models import StoryForce, Story, LoadCase, ResultCategory, ResultSet

        results = (
            session.query(
                Story.name.label("story_name"),
                LoadCase.name.label("load_case_name"),
                ResultSet.name.label("result_set_name"),
                ResultCategory.category_name.label("result_category_name"),
                StoryForce.direction,
                StoryForce.location,
                StoryForce.force,
                StoryForce.max_force,
                StoryForce.min_force,
                StoryForce.story_sort_order,
            )
            .join(Story, StoryForce.story_id == Story.id)
            .join(LoadCase, StoryForce.load_case_id == LoadCase.id)
            .join(ResultCategory, StoryForce.result_category_id == ResultCategory.id)
            .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
            .all()
        )

        return [
            {
                "story_name": r.story_name,
                "load_case_name": r.load_case_name,
                "result_set_name": r.result_set_name,
                "result_category_name": r.result_category_name,
                "direction": r.direction,
                "location": r.location,
                "force": r.force,
                "max_force": r.max_force,
                "min_force": r.min_force,
                "story_sort_order": r.story_sort_order,
            }
            for r in results
        ]

    def _serialize_story_displacements(self, session) -> list:
        from database.models import StoryDisplacement, Story, LoadCase, ResultCategory, ResultSet

        results = (
            session.query(
                Story.name.label("story_name"),
                LoadCase.name.label("load_case_name"),
                ResultSet.name.label("result_set_name"),
                ResultCategory.category_name.label("result_category_name"),
                StoryDisplacement.direction,
                StoryDisplacement.displacement,
                StoryDisplacement.max_displacement,
                StoryDisplacement.min_displacement,
                StoryDisplacement.story_sort_order,
            )
            .join(Story, StoryDisplacement.story_id == Story.id)
            .join(LoadCase, StoryDisplacement.load_case_id == LoadCase.id)
            .join(ResultCategory, StoryDisplacement.result_category_id == ResultCategory.id)
            .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
            .all()
        )

        return [
            {
                "story_name": r.story_name,
                "load_case_name": r.load_case_name,
                "result_set_name": r.result_set_name,
                "result_category_name": r.result_category_name,
                "direction": r.direction,
                "displacement": r.displacement,
                "max_displacement": r.max_displacement,
                "min_displacement": r.min_displacement,
                "story_sort_order": r.story_sort_order,
            }
            for r in results
        ]

    def _serialize_absolute_maxmin_drifts(self, session) -> list:
        from database.models import AbsoluteMaxMinDrift, Story, LoadCase, ResultSet

        results = (
            session.query(
                Story.name.label("story_name"),
                LoadCase.name.label("load_case_name"),
                ResultSet.name.label("result_set_name"),
                AbsoluteMaxMinDrift.direction,
                AbsoluteMaxMinDrift.absolute_max_drift,
                AbsoluteMaxMinDrift.sign,
                AbsoluteMaxMinDrift.original_max,
                AbsoluteMaxMinDrift.original_min,
            )
            .join(Story, AbsoluteMaxMinDrift.story_id == Story.id)
            .join(LoadCase, AbsoluteMaxMinDrift.load_case_id == LoadCase.id)
            .join(ResultSet, AbsoluteMaxMinDrift.result_set_id == ResultSet.id)
            .all()
        )

        return [
            {
                "story_name": r.story_name,
                "load_case_name": r.load_case_name,
                "result_set_name": r.result_set_name,
                "direction": r.direction,
                "absolute_max_drift": r.absolute_max_drift,
                "sign": r.sign,
                "original_max": r.original_max,
                "original_min": r.original_min,
            }
            for r in results
        ]

    def _serialize_quad_rotations(self, session) -> list:
        from database.models import QuadRotation, Story, LoadCase, ResultCategory, ResultSet, Element

        results = (
            session.query(
                Story.name.label("story_name"),
                LoadCase.name.label("load_case_name"),
                ResultSet.name.label("result_set_name"),
                ResultCategory.category_name.label("result_category_name"),
                Element.name.label("element_name"),
                QuadRotation.direction,
                QuadRotation.rotation,
                QuadRotation.max_rotation,
                QuadRotation.min_rotation,
                QuadRotation.story_sort_order,
            )
            .join(Element, QuadRotation.element_id == Element.id)
            .join(Story, QuadRotation.story_id == Story.id)
            .join(LoadCase, QuadRotation.load_case_id == LoadCase.id)
            .join(ResultCategory, QuadRotation.result_category_id == ResultCategory.id)
            .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
            .all()
        )

        return [
            {
                "story_name": r.story_name,
                "load_case_name": r.load_case_name,
                "result_set_name": r.result_set_name,
                "result_category_name": r.result_category_name,
                "element_name": r.element_name,
                "direction": r.direction,
                "rotation": r.rotation,
                "max_rotation": r.max_rotation,
                "min_rotation": r.min_rotation,
                "story_sort_order": r.story_sort_order,
            }
            for r in results
        ]

    def _serialize_wall_shears(self, session) -> list:
        from database.models import WallShear, Story, LoadCase, ResultCategory, ResultSet, Element

        results = (
            session.query(
                Story.name.label("story_name"),
                LoadCase.name.label("load_case_name"),
                ResultSet.name.label("result_set_name"),
                ResultCategory.category_name.label("result_category_name"),
                Element.name.label("element_name"),
                WallShear.direction,
                WallShear.location,
                WallShear.force,
                WallShear.max_force,
                WallShear.min_force,
                WallShear.story_sort_order,
            )
            .join(Element, WallShear.element_id == Element.id)
            .join(Story, WallShear.story_id == Story.id)
            .join(LoadCase, WallShear.load_case_id == LoadCase.id)
            .join(ResultCategory, WallShear.result_category_id == ResultCategory.id)
            .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
            .all()
        )

        return [
            {
                "story_name": r.story_name,
                "load_case_name": r.load_case_name,
                "result_set_name": r.result_set_name,
                "result_category_name": r.result_category_name,
                "element_name": r.element_name,
                "direction": r.direction,
                "location": r.location,
                "force": r.force,
                "max_force": r.max_force,
                "min_force": r.min_force,
                "story_sort_order": r.story_sort_order,
            }
            for r in results
        ]

    def _serialize_global_cache(self, session) -> list:
        from database.models import GlobalResultsCache

        entries = session.query(GlobalResultsCache).all()
        return [
            {
                "project_id": entry.project_id,
                "result_set_id": entry.result_set_id,
                "result_type": entry.result_type,
                "story_id": entry.story_id,
                "story_sort_order": entry.story_sort_order,
                "results_matrix": entry.results_matrix,
            }
            for entry in entries
        ]

    def _serialize_element_cache(self, session) -> list:
        from database.models import ElementResultsCache

        entries = session.query(ElementResultsCache).all()
        return [
            {
                "project_id": entry.project_id,
                "result_set_id": entry.result_set_id,
                "result_type": entry.result_type,
                "element_id": entry.element_id,
                "story_id": entry.story_id,
                "story_sort_order": entry.story_sort_order,
                "results_matrix": entry.results_matrix,
            }
            for entry in entries
        ]
