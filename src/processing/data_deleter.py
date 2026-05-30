"""Data deletion helpers for removing specific load cases from the database."""

import logging
from typing import Dict, Iterable, List, Optional, Set
from sqlalchemy import delete
from sqlalchemy.orm import Session

from database.models import (
    StoryDrift,
    StoryAcceleration,
    StoryForce,
    StoryDisplacement,
    WallShear,
    ColumnShear,
    ColumnAxial,
    BraceAxial,
    ColumnRotation,
    BeamRotation,
    QuadRotation,
    SoilPressure,
    VerticalDisplacement,
)

logger = logging.getLogger(__name__)

TASK_CACHE_RESULT_TYPES: Dict[str, List[str]] = {
    "Story Drifts": ["Drifts"],
    "Story Accelerations": ["Accelerations"],
    "Story Forces": ["Forces"],
    "Floors Displacements": ["Displacements"],
    "Pier Forces": ["WallShears_V2", "WallShears_V3"],
    "Column Forces": ["ColumnShears_V2", "ColumnShears_V3"],
    "Column Axials": ["ColumnAxials_Min", "ColumnAxials_Max"],
    "Brace Axials": ["BraceAxials_Min", "BraceAxials_Max"],
    "Column Rotations": ["ColumnRotations_R2", "ColumnRotations_R3"],
    "Beam Rotations": ["BeamRotations_R3Plastic"],
    "Quad Rotations": ["QuadRotations", "QuadRotations_Pier"],
    "Soil Pressures": ["SoilPressures_Min"],
    "Vertical Displacements": ["VerticalDisplacements_Min"],
}


class LoadCaseDataDeleter:
    """Deletes result data rows for specific load cases from all result tables."""

    @staticmethod
    def delete_load_case_data(
        session: Session,
        project_id: int,
        result_set_id: int,
        result_category_id: int,
        load_case_ids: List[int],
        task_labels: Optional[Iterable[str]] = None,
    ) -> Dict[str, int]:
        """Delete all result rows for the given load case IDs.

        If task_labels is provided, deletion is scoped to those import result
        types only (for example, Story Drifts without Story Forces).

        Returns: dict mapping table_name to rows_deleted
        """
        if not load_case_ids:
            return {}

        stats = {}
        requested_tasks: Optional[Set[str]] = set(task_labels) if task_labels else None

        def task_requested(task_label: str) -> bool:
            return requested_tasks is None or task_label in requested_tasks

        # Models that use result_category_id
        category_models = [
            ("Story Drifts", StoryDrift, "StoryDrift"),
            ("Story Accelerations", StoryAcceleration, "StoryAcceleration"),
            ("Story Forces", StoryForce, "StoryForce"),
            ("Floors Displacements", StoryDisplacement, "StoryDisplacement"),
            ("Pier Forces", WallShear, "WallShear"),
            ("Column Forces", ColumnShear, "ColumnShear"),
            ("Column Axials", ColumnAxial, "ColumnAxial"),
            ("Brace Axials", BraceAxial, "BraceAxial"),
            ("Column Rotations", ColumnRotation, "ColumnRotation"),
            ("Beam Rotations", BeamRotation, "BeamRotation"),
            ("Quad Rotations", QuadRotation, "QuadRotation"),
        ]

        # Models that use result_set_id
        set_models = [
            ("Soil Pressures", SoilPressure, "SoilPressure"),
            ("Vertical Displacements", VerticalDisplacement, "VerticalDisplacement"),
        ]

        try:
            for task_label, model_class, name in category_models:
                if not task_requested(task_label):
                    continue
                stmt = delete(model_class).where(
                    model_class.result_category_id == result_category_id,
                    model_class.load_case_id.in_(load_case_ids),
                )
                result = session.execute(stmt)
                stats[name] = result.rowcount

            for task_label, model_class, name in set_models:
                if not task_requested(task_label):
                    continue
                # Need to use project_id and result_set_id along with load_case_id
                stmt = delete(model_class).where(
                    model_class.project_id == project_id,
                    model_class.result_set_id == result_set_id,
                    model_class.load_case_id.in_(load_case_ids),
                )
                result = session.execute(stmt)
                stats[name] = result.rowcount

            session.commit()

            logger.info(
                f"Deleted existing data for {len(load_case_ids)} load cases "
                f"({', '.join(sorted(requested_tasks)) if requested_tasks else 'all result types'}): "
                f"{', '.join(f'{k}={v}' for k, v in stats.items() if v > 0)}"
            )

            return stats

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete load case data: {e}")
            raise
