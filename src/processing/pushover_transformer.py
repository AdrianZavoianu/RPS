"""Pushover data transformer - converts parsed data to ORM models."""

from typing import Dict, List
from sqlalchemy.orm import Session

from database.models import PushoverCase, PushoverCurvePoint
from .pushover_curve_parser import PushoverCurveData


class PushoverTransformer:
    """Transforms pushover curve data into database models."""

    def __init__(self, session: Session):
        self.session = session

    def transform_curves(
        self,
        curves: Dict[str, PushoverCurveData],
        project_id: int,
        result_set_id: int,
        base_story: str
    ) -> List[PushoverCase]:
        """
        Transform pushover curve data into PushoverCase ORM models.

        Args:
            curves: Dict of PushoverCurveData from parser
            project_id: Project ID
            result_set_id: Result set ID
            base_story: Base story used for extraction

        Returns:
            List of PushoverCase ORM objects (not yet committed)
        """
        pushover_cases = []

        for case_name, curve_data in curves.items():
            # Create PushoverCase
            pushover_case = PushoverCase(
                project_id=project_id,
                result_set_id=result_set_id,
                name=case_name,
                direction=curve_data.direction,
                base_story=base_story
            )

            # Create curve points
            for i in range(len(curve_data.step_numbers)):
                point = PushoverCurvePoint(
                    step_number=curve_data.step_numbers[i],
                    displacement=curve_data.displacements[i],
                    base_shear=curve_data.base_shears[i]
                )
                pushover_case.curve_points.append(point)

            pushover_cases.append(pushover_case)

        return pushover_cases

    def save_pushover_cases(self, pushover_cases: List[PushoverCase]) -> None:
        """Save pushover cases to database."""
        self.session.add_all(pushover_cases)
        self.session.commit()

    def delete_existing_cases(self, project_id: int, result_set_id: int) -> None:
        """Delete existing pushover cases for a result set (for reimport)."""
        self.session.query(PushoverCase).filter(
            PushoverCase.project_id == project_id,
            PushoverCase.result_set_id == result_set_id
        ).delete()
        self.session.commit()
