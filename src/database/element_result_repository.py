from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Optional, Tuple, Type

from sqlalchemy.orm import Session

from database.models import (
    BeamRotation,
    ColumnRotation,
    ColumnShear,
    LoadCase,
    QuadRotation,
    Story,
    WallShear,
)


@dataclass(frozen=True)
class ElementResultModelInfo:
    """Metadata for querying element-level result models."""

    model: Type[Any]
    max_attr: str
    min_attr: str
    direction_attr: Optional[str]
    multiplier: float


class ElementResultQueryRepository:
    """Encapsulates ORM queries for element max/min datasets."""

    _MODEL_REGISTRY: Dict[str, ElementResultModelInfo] = {
        "WallShears": ElementResultModelInfo(
            model=WallShear,
            max_attr="max_force",
            min_attr="min_force",
            direction_attr="direction",
            multiplier=1.0,
        ),
        "ColumnShears": ElementResultModelInfo(
            model=ColumnShear,
            max_attr="max_force",
            min_attr="min_force",
            direction_attr="direction",
            multiplier=1.0,
        ),
        "ColumnRotations": ElementResultModelInfo(
            model=ColumnRotation,
            max_attr="max_rotation",
            min_attr="min_rotation",
            direction_attr="direction",
            multiplier=100.0,
        ),
        "BeamRotations": ElementResultModelInfo(
            model=BeamRotation,
            max_attr="max_r3_plastic",
            min_attr="min_r3_plastic",
            direction_attr=None,
            multiplier=100.0,
        ),
        "QuadRotations": ElementResultModelInfo(
            model=QuadRotation,
            max_attr="max_rotation",
            min_attr="min_rotation",
            direction_attr=None,
            multiplier=100.0,
        ),
    }

    def __init__(self, session: Session) -> None:
        self.session = session

    @classmethod
    def supported_types(cls) -> Iterable[str]:
        return cls._MODEL_REGISTRY.keys()

    def fetch_records(
        self, base_result_type: str, project_id: int, element_id: int
    ) -> Optional[Tuple[Iterable[Tuple[Any, LoadCase, Story]], ElementResultModelInfo]]:
        model_info = self._MODEL_REGISTRY.get(base_result_type)
        if not model_info:
            return None

        query = (
            self.session.query(model_info.model, LoadCase, Story)
            .join(LoadCase, model_info.model.load_case_id == LoadCase.id)
            .join(Story, model_info.model.story_id == Story.id)
            .filter(
                Story.project_id == project_id,
                model_info.model.element_id == element_id,
            )
        )
        records = query.all()
        return records, model_info

