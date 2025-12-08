"""Foundation repositories for SoilPressure and VerticalDisplacement operations."""

from typing import List, Optional
from sqlalchemy import and_

from ..models import SoilPressure, VerticalDisplacement
from ..base_repository import BaseRepository


class SoilPressureRepository(BaseRepository[SoilPressure]):
    """Repository for SoilPressure operations."""

    model = SoilPressure

    def create(
        self,
        project_id: int,
        load_case_id: int,
        shell_object: str,
        unique_name: str,
        min_pressure: float,
        result_set_id: Optional[int] = None,
        result_category_id: Optional[int] = None,
    ) -> SoilPressure:
        """Create a new soil pressure record."""
        return super().create(
            project_id=project_id,
            load_case_id=load_case_id,
            shell_object=shell_object,
            unique_name=unique_name,
            min_pressure=min_pressure,
            result_set_id=result_set_id,
            result_category_id=result_category_id,
        )

    def get_by_result_set(self, project_id: int, result_set_id: int) -> List[SoilPressure]:
        """Get all soil pressures for a result set."""
        return (
            self.session.query(SoilPressure)
            .filter(
                and_(
                    SoilPressure.project_id == project_id,
                    SoilPressure.result_set_id == result_set_id,
                )
            )
            .all()
        )


class VerticalDisplacementRepository(BaseRepository[VerticalDisplacement]):
    """Repository for VerticalDisplacement operations."""

    model = VerticalDisplacement

    def create(
        self,
        project_id: int,
        load_case_id: int,
        story: str,
        label: str,
        unique_name: str,
        min_displacement: float,
        result_set_id: Optional[int] = None,
        result_category_id: Optional[int] = None,
    ) -> VerticalDisplacement:
        """Create a new vertical displacement record."""
        return super().create(
            project_id=project_id,
            load_case_id=load_case_id,
            story=story,
            label=label,
            unique_name=unique_name,
            min_displacement=min_displacement,
            result_set_id=result_set_id,
            result_category_id=result_category_id,
        )

    def get_by_result_set(self, project_id: int, result_set_id: int) -> List[VerticalDisplacement]:
        """Get all vertical displacements for a result set."""
        return (
            self.session.query(VerticalDisplacement)
            .filter(
                and_(
                    VerticalDisplacement.project_id == project_id,
                    VerticalDisplacement.result_set_id == result_set_id,
                )
            )
            .all()
        )
