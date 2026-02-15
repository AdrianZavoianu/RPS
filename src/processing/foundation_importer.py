"""Foundation and joint import helpers (soil pressures, vertical displacements)."""

from __future__ import annotations

from typing import Dict, Optional

from sqlalchemy.orm import Session

from database.models import SoilPressure, VerticalDisplacement
from database.repositories import ResultCategoryRepository
from .import_context import ResultImportHelper


class FoundationImporter:
    """Handles foundation/joint imports that share load-case handling."""

    def __init__(
        self,
        *,
        session: Session,
        parser,
        project_id: int,
        result_set_id: int,
    ) -> None:
        self.session = session
        self.parser = parser
        self.project_id = project_id
        self.result_set_id = result_set_id
        self._category_repo = ResultCategoryRepository(session)
        self._joint_category_id_value: Optional[int] = None

    def _joint_category_id(self) -> int:
        if self._joint_category_id_value is None:
            category = self._category_repo.get_or_create(
                result_set_id=self.result_set_id,
                category_name="Envelopes",
                category_type="Joints",
            )
            self._joint_category_id_value = category.id
        return self._joint_category_id_value

    def import_soil_pressures(self) -> Dict[str, int]:
        """Import minimum soil pressures from the Soil Pressures sheet."""
        stats: Dict[str, int] = {"soil_pressures": 0}
        try:
            df, load_cases, _unique_elements = self.parser.get_soil_pressures()
            if df is None or df.empty or not load_cases:
                return stats

            helper = ResultImportHelper(self.session, self.project_id, [])  # No stories needed

            load_case_map = {
                case_name: helper.get_load_case(case_name)
                for case_name in load_cases
            }

            # Remove only rows for load cases being re-imported so multiple files can merge
            load_case_ids = [lc.id for lc in load_case_map.values()]
            if load_case_ids:
                self.session.query(SoilPressure).filter(
                    SoilPressure.project_id == self.project_id,
                    SoilPressure.result_set_id == self.result_set_id,
                    SoilPressure.load_case_id.in_(load_case_ids),
                ).delete(synchronize_session=False)

            soil_pressure_objects = []
            category_id = self._joint_category_id()

            for _, row in df.iterrows():
                load_case = load_case_map[row["Output Case"]]
                soil_pressure = SoilPressure(
                    project_id=self.project_id,
                    result_set_id=self.result_set_id,
                    result_category_id=category_id,
                    load_case_id=load_case.id,
                    shell_object=row["Shell Object"],
                    unique_name=row["Unique Name"],
                    min_pressure=row["Soil Pressure"],
                )
                soil_pressure_objects.append(soil_pressure)

            self.session.bulk_save_objects(soil_pressure_objects)
            self.session.commit()
            stats["soil_pressures"] += len(soil_pressure_objects)
            return stats
        except Exception as e:
            raise ValueError(f"Error importing soil pressures: {e}")

    def import_vertical_displacements(self) -> Dict[str, int]:
        """Import minimum vertical displacements (Uz) for foundation joints."""
        stats: Dict[str, int] = {"vertical_displacements": 0}
        try:
            df, load_cases, _unique_joints = self.parser.get_vertical_displacements()

            if df.empty:
                return stats

            helper = ResultImportHelper(self.session, self.project_id, [])  # No stories needed

            load_case_map = {
                case_name: helper.get_load_case(case_name)
                for case_name in load_cases
            }

            load_case_ids = [lc.id for lc in load_case_map.values()]
            if load_case_ids:
                self.session.query(VerticalDisplacement).filter(
                    VerticalDisplacement.project_id == self.project_id,
                    VerticalDisplacement.result_set_id == self.result_set_id,
                    VerticalDisplacement.load_case_id.in_(load_case_ids),
                ).delete(synchronize_session=False)

            vert_disp_objects = []
            category_id = self._joint_category_id()

            for _, row in df.iterrows():
                load_case = load_case_map[row["Output Case"]]
                vert_disp = VerticalDisplacement(
                    project_id=self.project_id,
                    result_set_id=self.result_set_id,
                    result_category_id=category_id,
                    load_case_id=load_case.id,
                    story=row["Story"],
                    label=row["Label"],
                    unique_name=row["Unique Name"],
                    min_displacement=row["Min Uz"],
                )
                vert_disp_objects.append(vert_disp)

            self.session.bulk_save_objects(vert_disp_objects)
            self.session.commit()
            stats["vertical_displacements"] += len(vert_disp_objects)
            return stats
        except Exception as e:
            raise ValueError(f"Error importing vertical displacements: {e}")
