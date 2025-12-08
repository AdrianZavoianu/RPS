"""Pushover repositories for PushoverCase and PushoverCurvePoint operations."""

from typing import List, Optional

from ..models import PushoverCase, PushoverCurvePoint
from ..base_repository import BaseRepository


class PushoverCaseRepository(BaseRepository[PushoverCase]):
    """Repository for PushoverCase operations."""

    model = PushoverCase

    def get_by_result_set(self, result_set_id: int) -> List[PushoverCase]:
        """Get all pushover cases for a result set."""
        return self.session.query(PushoverCase).filter(
            PushoverCase.result_set_id == result_set_id
        ).all()

    def get_by_name(self, project_id: int, result_set_id: int, name: str) -> Optional[PushoverCase]:
        """Get a specific pushover case by name."""
        return self.session.query(PushoverCase).filter(
            PushoverCase.project_id == project_id,
            PushoverCase.result_set_id == result_set_id,
            PushoverCase.name == name
        ).first()

    def get_curve_data(self, pushover_case_id: int) -> List[PushoverCurvePoint]:
        """Get all curve points for a pushover case, ordered by step."""
        return self.session.query(PushoverCurvePoint).filter(
            PushoverCurvePoint.pushover_case_id == pushover_case_id
        ).order_by(PushoverCurvePoint.step_number).all()
