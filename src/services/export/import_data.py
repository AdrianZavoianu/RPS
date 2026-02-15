"""IMPORT_DATA sheet serialization helpers for export."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Dict

import pandas as pd

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
        return serialize_story_drifts(session)

    def _serialize_story_accelerations(self, session) -> list:
        return serialize_story_accelerations(session)

    def _serialize_story_forces(self, session) -> list:
        return serialize_story_forces(session)

    def _serialize_story_displacements(self, session) -> list:
        return serialize_story_displacements(session)

    def _serialize_absolute_maxmin_drifts(self, session) -> list:
        return serialize_absolute_maxmin_drifts(session)

    def _serialize_quad_rotations(self, session) -> list:
        return serialize_quad_rotations(session)

    def _serialize_wall_shears(self, session) -> list:
        return serialize_wall_shears(session)

    def _serialize_global_cache(self, session) -> list:
        return serialize_global_cache(session)

    def _serialize_element_cache(self, session) -> list:
        return serialize_element_cache(session)
