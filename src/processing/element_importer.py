"""Element-level import helpers for walls, quads, columns, and beams."""

from __future__ import annotations

from typing import Dict

from sqlalchemy.orm import Session

from database.models import WallShear, QuadRotation, ColumnShear, ColumnAxial, ColumnRotation, BeamRotation
from database.repository import ElementRepository
from .import_context import ResultImportHelper
from .result_processor import ResultProcessor


class ElementImporter:
    """Handles element-level imports for walls, quads, columns, and beams."""

    def __init__(
        self,
        *,
        session: Session,
        parser,
        project_id: int,
        result_category_id: int,
    ) -> None:
        self.session = session
        self.parser = parser
        self.project_id = project_id
        self.result_category_id = result_category_id
        self._element_repo = ElementRepository(session)

    def import_pier_forces(self) -> Dict[str, int]:
        stats = {"pier_forces": 0, "piers": 0}
        try:
            df, load_cases, stories, piers = self.parser.get_pier_forces()
            helper = ResultImportHelper(self.session, self.project_id, stories)

            pier_elements = {
                pier_name: self._element_repo.get_or_create(
                    project_id=self.project_id,
                    element_type="Wall",
                    unique_name=pier_name,
                    name=pier_name,
                )
                for pier_name in piers
            }

            stats["piers"] = len(pier_elements)

            for direction in ["V2", "V3"]:
                processed = ResultProcessor.process_pier_forces(
                    df, load_cases, stories, piers, direction
                )

                wall_shear_objects = []
                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = pier_elements[row["Pier"]]

                    wall_shear_objects.append(
                        WallShear(
                            element_id=element.id,
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

                self.session.bulk_save_objects(wall_shear_objects)
                self.session.commit()
                stats["pier_forces"] += len(wall_shear_objects)

            return stats
        except Exception as e:
            raise ValueError(f"Error importing pier forces: {e}")

    def import_quad_rotations(self) -> Dict[str, int]:
        stats = {"quad_rotations": 0, "piers": 0}
        try:
            df, load_cases, stories, piers = self.parser.get_quad_rotations()
            helper = ResultImportHelper(self.session, self.project_id, stories)

            pier_elements = {
                pier_name: self._element_repo.get_or_create(
                    project_id=self.project_id,
                    element_type="Quad",
                    unique_name=pier_name,
                    name=pier_name,
                )
                for pier_name in piers
            }
            stats["piers"] = len(pier_elements)

            processed = ResultProcessor.process_quad_rotations(
                df, load_cases, stories, piers
            )

            quad_rotation_objects = []
            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = pier_elements[row["Pier"]]
                story_order = getattr(story, "sort_order", None) or helper._story_order.get(row["Story"])

                quad_rotation_objects.append(
                    QuadRotation(
                        element_id=element.id,
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        quad_name=row.get("QuadName"),
                        direction="Pier",
                        rotation=row["Rotation"],
                        max_rotation=row.get("MaxRotation"),
                        min_rotation=row.get("MinRotation"),
                        story_sort_order=story_order,
                    )
                )

            self.session.bulk_save_objects(quad_rotation_objects)
            self.session.commit()
            stats["quad_rotations"] = len(quad_rotation_objects)
            return stats
        except Exception as e:
            raise ValueError(f"Error importing quad rotations: {e}")

    def import_column_forces(self) -> Dict[str, int]:
        stats = {"column_forces": 0, "columns": 0}
        try:
            df, load_cases, stories, columns = self.parser.get_column_forces()
            helper = ResultImportHelper(self.session, self.project_id, stories)

            column_elements = {
                column_name: self._element_repo.get_or_create(
                    project_id=self.project_id,
                    element_type="Column",
                    unique_name=column_name,
                    name=column_name,
                )
                for column_name in columns
            }
            stats["columns"] = len(column_elements)

            for direction in ["V2", "V3"]:
                processed = ResultProcessor.process_column_forces(
                    df, load_cases, stories, columns, direction
                )

                column_shear_objects = []
                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = column_elements[row["Column"]]

                    column_shear_objects.append(
                        ColumnShear(
                            element_id=element.id,
                            story_id=story.id,
                            load_case_id=load_case.id,
                            result_category_id=self.result_category_id,
                            direction=direction,
                            location=row.get("Location"),
                            force=row["Force"],
                            max_force=row.get("MaxForce"),
                            min_force=row.get("MinForce"),
                            story_sort_order=helper._story_order.get(row["Story"]),
                        )
                    )

                self.session.bulk_save_objects(column_shear_objects)
                self.session.commit()
                stats["column_forces"] += len(column_shear_objects)

            return stats
        except Exception as e:
            raise ValueError(f"Error importing column forces: {e}")

    def import_column_axials(self) -> Dict[str, int]:
        stats = {"column_axials": 0}
        try:
            df, load_cases, stories, columns = self.parser.get_column_forces()
            helper = ResultImportHelper(self.session, self.project_id, stories)

            column_elements = {
                column_name: self._element_repo.get_or_create(
                    project_id=self.project_id,
                    element_type="Column",
                    unique_name=column_name,
                    name=column_name,
                )
                for column_name in columns
            }

            processed = ResultProcessor.process_column_axials(
                df, load_cases, stories, columns
            )

            column_axial_objects = []
            for _, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = column_elements[row["Column"]]

                column_axial_objects.append(
                    ColumnAxial(
                        element_id=element.id,
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        location=row.get("Location"),
                        min_axial=row["MinAxial"],
                        max_axial=row.get("MaxAxial"),
                        story_sort_order=helper._story_order.get(row["Story"]),
                    )
                )

            self.session.bulk_save_objects(column_axial_objects)
            self.session.commit()
            stats["column_axials"] += len(column_axial_objects)
            return stats
        except Exception as e:
            raise ValueError(f"Error importing column axials: {e}")

    def import_column_rotations(self) -> Dict[str, int]:
        stats = {"column_rotations": 0, "columns": 0}
        try:
            df, load_cases, stories, columns = self.parser.get_fiber_hinge_states()
            helper = ResultImportHelper(self.session, self.project_id, stories)

            column_elements = {
                column_name: self._element_repo.get_or_create(
                    project_id=self.project_id,
                    element_type="Column",
                    unique_name=column_name,
                    name=column_name,
                )
                for column_name in columns
            }
            stats["columns"] = len(column_elements)

            for direction in ["R2", "R3"]:
                processed = ResultProcessor.process_column_rotations(
                    df, load_cases, stories, columns, direction
                )

                column_rotation_objects = []
                for _, row in processed.iterrows():
                    story = helper.get_story(row["Story"])
                    load_case = helper.get_load_case(row["LoadCase"])
                    element = column_elements[row["Column"]]

                    column_rotation_objects.append(
                        ColumnRotation(
                            element_id=element.id,
                            story_id=story.id,
                            load_case_id=load_case.id,
                            result_category_id=self.result_category_id,
                            direction=direction,
                            rotation=row["Rotation"],
                            max_rotation=row.get("MaxRotation"),
                            min_rotation=row.get("MinRotation"),
                            story_sort_order=helper._story_order.get(row["Story"]),
                        )
                    )

                self.session.bulk_save_objects(column_rotation_objects)
                self.session.commit()
                stats["column_rotations"] += len(column_rotation_objects)

            return stats
        except Exception as e:
            raise ValueError(f"Error importing column rotations: {e}")

    def import_beam_rotations(self) -> Dict[str, int]:
        stats = {"beam_rotations": 0, "beams": 0}
        try:
            df, load_cases, stories, beams = self.parser.get_hinge_states()
            helper = ResultImportHelper(self.session, self.project_id, stories)

            beam_elements = {
                beam_name: self._element_repo.get_or_create(
                    project_id=self.project_id,
                    element_type="Beam",
                    unique_name=beam_name,
                    name=beam_name,
                )
                for beam_name in beams
            }
            stats["beams"] = len(beam_elements)

            processed = ResultProcessor.process_beam_rotations(
                df, load_cases, stories, beams
            )

            beam_rotation_objects = []
            for idx, row in processed.iterrows():
                story = helper.get_story(row["Story"])
                load_case = helper.get_load_case(row["LoadCase"])
                element = beam_elements[row["Beam"]]

                beam_rotation_objects.append(
                    BeamRotation(
                        element_id=element.id,
                        story_id=story.id,
                        load_case_id=load_case.id,
                        result_category_id=self.result_category_id,
                        step_type=row.get("StepType"),
                        hinge=row.get("Hinge"),
                        generated_hinge=row.get("GeneratedHinge"),
                        rel_dist=row.get("RelDist"),
                        r3_plastic=row["R3Plastic"],
                        max_r3_plastic=None,  # Will compute in export if needed
                        min_r3_plastic=None,
                        story_sort_order=idx,  # Use DataFrame index to preserve source order
                    )
                )

            self.session.bulk_save_objects(beam_rotation_objects)
            self.session.commit()
            stats["beam_rotations"] += len(beam_rotation_objects)
            return stats
        except Exception as e:
            raise ValueError(f"Error importing beam rotations: {e}")
