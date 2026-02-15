"""Global (story-level) import helpers for drifts, accelerations, forces, and displacements."""

from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

from database.models import StoryDrift, StoryAcceleration, StoryForce, StoryDisplacement
from database.repositories import (
    StoryDriftDataRepository,
    StoryAccelerationDataRepository,
    StoryForceDataRepository,
    StoryDisplacementDataRepository,
)
from .import_filtering import filter_cases_and_dataframe
from .import_context import ResultImportHelper
from .result_processor import ResultProcessor


class GlobalImporter:
    """Handles global story-level imports (drifts, accelerations, forces, displacements)."""

    def __init__(
        self,
        *,
        session: Session,
        parser,
        project_id: int,
        result_category_id: int,
        allowed_load_cases: set[str] | None = None,
    ) -> None:
        self.session = session
        self.parser = parser
        self.project_id = project_id
        self.result_category_id = result_category_id
        self.allowed_load_cases = allowed_load_cases

    def import_story_drifts(self) -> Dict[str, int]:
        stats = {"load_cases": 0, "stories": 0, "drifts": 0}
        try:
            df, load_cases, stories = self.parser.get_story_drifts()
            load_cases, df = filter_cases_and_dataframe(
                df,
                load_cases,
                self.allowed_load_cases,
                column="Output Case",
            )
            if not load_cases:
                return stats
            helper = ResultImportHelper(self.session, self.project_id, stories)
            drift_repo = StoryDriftDataRepository(self.session)

            for direction in ["X", "Y"]:
                processed = ResultProcessor.process_story_drifts(
                    df, load_cases, stories, direction
                )

                drift_objects = []
                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"], case_type="Time History")
                    drift_objects.append(
                        StoryDrift(
                            story_id=story.id,
                            load_case_id=load_case.id,
                            result_category_id=self.result_category_id,
                            direction=direction,
                            drift=row["Drift"],
                            max_drift=row.get("MaxDrift"),
                            min_drift=row.get("MinDrift"),
                            story_sort_order=helper._story_order.get(row["Story"]),
                        )
                    )

                drift_repo.bulk_create(drift_objects)
                stats["drifts"] += len(drift_objects)

            stats["load_cases"] = len(load_cases)
            stats["stories"] = len(stories)
            return stats
        except Exception as e:
            raise ValueError(f"Error importing story drifts: {e}")

    def import_story_accelerations(self) -> Dict[str, int]:
        stats = {"accelerations": 0}
        try:
            df, load_cases, stories = self.parser.get_story_accelerations()
            load_cases, df = filter_cases_and_dataframe(
                df,
                load_cases,
                self.allowed_load_cases,
                column="Output Case",
            )
            if not load_cases:
                return stats
            helper = ResultImportHelper(self.session, self.project_id, stories)
            accel_repo = StoryAccelerationDataRepository(self.session)

            for direction in ["UX", "UY"]:
                processed = ResultProcessor.process_story_accelerations(
                    df, load_cases, stories, direction
                )

                accel_objects: List[StoryAcceleration] = []
                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    accel_objects.append(
                        StoryAcceleration(
                            story_id=story.id,
                            load_case_id=load_case.id,
                            result_category_id=self.result_category_id,
                            direction=direction,
                            acceleration=row["Acceleration"],
                            max_acceleration=row.get("MaxAcceleration"),
                            min_acceleration=row.get("MinAcceleration"),
                            story_sort_order=helper._story_order.get(row["Story"]),
                        )
                    )

                accel_repo.bulk_create(accel_objects)
                stats["accelerations"] += len(accel_objects)

            return stats
        except Exception as e:
            raise ValueError(f"Error importing story accelerations: {e}")

    def import_story_forces(self) -> Dict[str, int]:
        stats = {"forces": 0}
        try:
            df, load_cases, stories = self.parser.get_story_forces()
            load_cases, df = filter_cases_and_dataframe(
                df,
                load_cases,
                self.allowed_load_cases,
                column="Output Case",
            )
            if not load_cases:
                return stats
            helper = ResultImportHelper(self.session, self.project_id, stories)
            force_repo = StoryForceDataRepository(self.session)

            for direction in ["VX", "VY"]:
                processed = ResultProcessor.process_story_forces(
                    df, load_cases, stories, direction
                )

                force_objects = []
                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    force_objects.append(
                        StoryForce(
                            story_id=story.id,
                            load_case_id=load_case.id,
                            result_category_id=self.result_category_id,
                            direction=direction,
                            location=row.get("Location", "Bottom"),
                            force=row["Force"],
                            max_force=row.get("MaxForce"),
                            min_force=row.get("MinForce"),
                            story_sort_order=helper._story_order.get(row["Story"]),
                        )
                    )

                force_repo.bulk_create(force_objects)
                stats["forces"] += len(force_objects)

            return stats
        except Exception as e:
            raise ValueError(f"Error importing story forces: {e}")

    def import_joint_displacements(self) -> Dict[str, int]:
        stats = {"displacements": 0}
        try:
            df, load_cases, stories = self.parser.get_joint_displacements()
            load_cases, df = filter_cases_and_dataframe(
                df,
                load_cases,
                self.allowed_load_cases,
                column="Output Case",
            )
            if not load_cases:
                return stats
            helper = ResultImportHelper(self.session, self.project_id, stories)

            if df.empty:
                return stats

            disp_repo = StoryDisplacementDataRepository(self.session)

            for direction in ["Ux", "Uy"]:
                processed = ResultProcessor.process_joint_displacements(
                    df, load_cases, stories, direction
                )

                displacement_objects = []
                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"], case_type="Time History")
                    displacement_objects.append(
                        StoryDisplacement(
                            story_id=story.id,
                            load_case_id=load_case.id,
                            result_category_id=self.result_category_id,
                            direction=row["Direction"],
                            displacement=row["Displacement"],
                            max_displacement=row.get("MaxDisplacement"),
                            min_displacement=row.get("MinDisplacement"),
                            story_sort_order=helper._story_order.get(row["Story"]),
                        )
                    )

                disp_repo.bulk_create(displacement_objects)
                stats["displacements"] += len(displacement_objects)

            return stats
        except Exception as e:
            raise ValueError(f"Error importing joint displacements: {e}")
