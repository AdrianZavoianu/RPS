"""Cache generation helpers for wide-format result views."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import and_

from database.repository import (
    StoryRepository,
    CacheRepository,
    ResultRepository,
    AbsoluteMaxMinDriftRepository,
    ElementRepository,
    ElementCacheRepository,
    JointCacheRepository,
)
from database.models import (
    StoryDrift,
    StoryAcceleration,
    StoryForce,
    StoryDisplacement,
    WallShear,
    ColumnShear,
    ColumnAxial,
    ColumnRotation,
    QuadRotation,
    BeamRotation,
    SoilPressure,
    VerticalDisplacement,
    LoadCase,
    Story,
    Element,
)


class CacheBuilder:
    """Generates wide-format cache tables for a project/result set."""

    def __init__(
        self,
        *,
        session: Session,
        project_id: int,
        result_set_id: int,
        result_category_id: int,
    ) -> None:
        self.session = session
        self.project_id = project_id
        self.result_set_id = result_set_id
        self.result_category_id = result_category_id

        self._story_repo = StoryRepository(session)
        self._cache_repo = CacheRepository(session)
        self._result_repo = ResultRepository(session)
        self._abs_repo = AbsoluteMaxMinDriftRepository(session)
        self._element_repo = ElementRepository(session)
        self._element_cache_repo = ElementCacheRepository(session)
        self._joint_cache_repo = JointCacheRepository(session)

    def generate_all(self) -> None:
        """Generate cache rows for all supported result types."""
        stories = self._story_repo.get_by_project(self.project_id)

        self._cache_drifts(stories)
        self._cache_accelerations(stories)
        self._cache_forces(stories)
        self._cache_displacements(stories)
        self._cache_pier_forces(stories)
        self._cache_column_shears(stories)
        self._cache_column_axials(stories)
        self._cache_column_rotations(stories)
        self._cache_beam_rotations(stories)
        self._cache_quad_rotations(stories)
        self._cache_soil_pressures()
        self._cache_vertical_displacements()
        self._calculate_absolute_maxmin(stories)

    # ------------------------------------------------------------------
    # Global result caches
    # ------------------------------------------------------------------
    def _cache_drifts(self, stories):
        drifts = (
            self.session.query(StoryDrift, LoadCase.name)
            .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
            .join(Story, StoryDrift.story_id == Story.id)
            .filter(Story.project_id == self.project_id)
            .filter(StoryDrift.result_category_id == self.result_category_id)
            .all()
        )

        story_matrices = {}
        story_sort_orders = {}
        for drift, load_case_name in drifts:
            story_id = drift.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                story_sort_orders[story_id] = drift.story_sort_order

            key = f"{load_case_name}_{drift.direction}"
            story_matrices[story_id][key] = drift.drift

        for story_id, results_matrix in story_matrices.items():
            self._cache_repo.upsert_cache_entry(
                project_id=self.project_id,
                story_id=story_id,
                result_type="Drifts",
                results_matrix=results_matrix,
                result_set_id=self.result_set_id,
                story_sort_order=story_sort_orders.get(story_id),
            )

    def _cache_accelerations(self, stories):
        accels = (
            self.session.query(StoryAcceleration, LoadCase.name)
            .join(LoadCase, StoryAcceleration.load_case_id == LoadCase.id)
            .join(Story, StoryAcceleration.story_id == Story.id)
            .filter(Story.project_id == self.project_id)
            .filter(StoryAcceleration.result_category_id == self.result_category_id)
            .all()
        )

        story_matrices = {}
        story_sort_orders = {}
        for accel, load_case_name in accels:
            story_id = accel.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                story_sort_orders[story_id] = accel.story_sort_order

            key = f"{load_case_name}_{accel.direction}"
            story_matrices[story_id][key] = accel.acceleration

        for story_id, results_matrix in story_matrices.items():
            self._cache_repo.upsert_cache_entry(
                project_id=self.project_id,
                story_id=story_id,
                result_type="Accelerations",
                results_matrix=results_matrix,
                result_set_id=self.result_set_id,
                story_sort_order=story_sort_orders.get(story_id),
            )

    def _cache_forces(self, stories):
        forces = (
            self.session.query(StoryForce, LoadCase.name)
            .join(LoadCase, StoryForce.load_case_id == LoadCase.id)
            .join(Story, StoryForce.story_id == Story.id)
            .filter(Story.project_id == self.project_id)
            .filter(StoryForce.result_category_id == self.result_category_id)
            .all()
        )

        story_matrices = {}
        story_sort_orders = {}
        for force, load_case_name in forces:
            story_id = force.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                story_sort_orders[story_id] = force.story_sort_order

            key = f"{load_case_name}_{force.direction}"
            story_matrices[story_id][key] = force.force

        for story_id, results_matrix in story_matrices.items():
            self._cache_repo.upsert_cache_entry(
                project_id=self.project_id,
                story_id=story_id,
                result_type="Forces",
                results_matrix=results_matrix,
                result_set_id=self.result_set_id,
                story_sort_order=story_sort_orders.get(story_id),
            )

    def _cache_displacements(self, stories):
        displacements = (
            self.session.query(StoryDisplacement, LoadCase.name)
            .join(LoadCase, StoryDisplacement.load_case_id == LoadCase.id)
            .join(Story, StoryDisplacement.story_id == Story.id)
            .filter(Story.project_id == self.project_id)
            .filter(StoryDisplacement.result_category_id == self.result_category_id)
            .all()
        )

        story_matrices = {}
        story_sort_orders = {}
        for displacement, load_case_name in displacements:
            story_id = displacement.story_id
            if story_id not in story_matrices:
                story_matrices[story_id] = {}
                story_sort_orders[story_id] = displacement.story_sort_order

            key = f"{load_case_name}_{displacement.direction}"
            story_matrices[story_id][key] = displacement.displacement

        for story_id, results_matrix in story_matrices.items():
            self._cache_repo.upsert_cache_entry(
                project_id=self.project_id,
                story_id=story_id,
                result_type="Displacements",
                results_matrix=results_matrix,
                result_set_id=self.result_set_id,
                story_sort_order=story_sort_orders.get(story_id),
            )

    # ------------------------------------------------------------------
    # Element caches
    # ------------------------------------------------------------------
    def _cache_pier_forces(self, stories):
        piers = self._element_repo.get_by_project(self.project_id, element_type="Wall")

        for pier in piers:
            for direction in ["V2", "V3"]:
                result_type = f"WallShears_{direction}"

                shears = (
                    self.session.query(WallShear, LoadCase.name, Story)
                    .join(LoadCase, WallShear.load_case_id == LoadCase.id)
                    .join(Story, WallShear.story_id == Story.id)
                    .filter(WallShear.element_id == pier.id)
                    .filter(WallShear.direction == direction)
                    .filter(WallShear.result_category_id == self.result_category_id)
                    .all()
                )

                story_data = {}
                story_sort_orders = {}
                for shear, case_name, story in shears:
                    if story.id not in story_data:
                        story_data[story.id] = {}
                        story_sort_orders[story.id] = shear.story_sort_order
                    story_data[story.id][case_name] = shear.force

                for story_id, results_matrix in story_data.items():
                    self._element_cache_repo.upsert_cache_entry(
                        project_id=self.project_id,
                        element_id=pier.id,
                        story_id=story_id,
                        result_type=result_type,
                        results_matrix=results_matrix,
                        result_set_id=self.result_set_id,
                        story_sort_order=story_sort_orders.get(story_id),
                    )

    def _cache_column_shears(self, stories):
        columns = self._element_repo.get_by_project(self.project_id, element_type="Column")

        for column in columns:
            for direction in ["V2", "V3"]:
                result_type = f"ColumnShears_{direction}"

                shears = (
                    self.session.query(ColumnShear, LoadCase.name, Story)
                    .join(LoadCase, ColumnShear.load_case_id == LoadCase.id)
                    .join(Story, ColumnShear.story_id == Story.id)
                    .filter(ColumnShear.element_id == column.id)
                    .filter(ColumnShear.direction == direction)
                    .filter(ColumnShear.result_category_id == self.result_category_id)
                    .all()
                )

                story_data = {}
                story_sort_orders = {}
                for shear, case_name, story in shears:
                    if story.id not in story_data:
                        story_data[story.id] = {}
                        story_sort_orders[story.id] = shear.story_sort_order
                    story_data[story.id][case_name] = shear.force

                for story_id, results_matrix in story_data.items():
                    self._element_cache_repo.upsert_cache_entry(
                        project_id=self.project_id,
                        element_id=column.id,
                        story_id=story_id,
                        result_type=result_type,
                        results_matrix=results_matrix,
                        result_set_id=self.result_set_id,
                        story_sort_order=story_sort_orders.get(story_id),
                    )

    def _cache_column_axials(self, stories):
        """Cache column axial forces (both min and max)."""
        columns = self._element_repo.get_by_project(self.project_id, element_type="Column")

        for column in columns:
            axials = (
                self.session.query(ColumnAxial, LoadCase.name, Story)
                .join(LoadCase, ColumnAxial.load_case_id == LoadCase.id)
                .join(Story, ColumnAxial.story_id == Story.id)
                .filter(ColumnAxial.element_id == column.id)
                .filter(ColumnAxial.result_category_id == self.result_category_id)
                .all()
            )

            # Cache min axials
            min_story_data = {}
            max_story_data = {}
            story_sort_orders = {}
            for axial, case_name, story in axials:
                if story.id not in min_story_data:
                    min_story_data[story.id] = {}
                    max_story_data[story.id] = {}
                    story_sort_orders[story.id] = axial.story_sort_order
                min_story_data[story.id][case_name] = axial.min_axial
                if axial.max_axial is not None:
                    max_story_data[story.id][case_name] = axial.max_axial

            # Store min axials cache
            for story_id, results_matrix in min_story_data.items():
                self._element_cache_repo.upsert_cache_entry(
                    project_id=self.project_id,
                    element_id=column.id,
                    story_id=story_id,
                    result_type="ColumnAxials_Min",
                    results_matrix=results_matrix,
                    result_set_id=self.result_set_id,
                    story_sort_order=story_sort_orders.get(story_id),
                )

            # Store max axials cache
            for story_id, results_matrix in max_story_data.items():
                if results_matrix:  # Only store if we have max data
                    self._element_cache_repo.upsert_cache_entry(
                        project_id=self.project_id,
                        element_id=column.id,
                        story_id=story_id,
                        result_type="ColumnAxials_Max",
                        results_matrix=results_matrix,
                        result_set_id=self.result_set_id,
                        story_sort_order=story_sort_orders.get(story_id),
                    )

    def _cache_quad_rotations(self, stories):
        quads = self._element_repo.get_by_project(self.project_id, element_type="Quad")

        for quad in quads:
            rotations = (
                self.session.query(QuadRotation, LoadCase.name, Story)
                .join(LoadCase, QuadRotation.load_case_id == LoadCase.id)
                .join(Story, QuadRotation.story_id == Story.id)
                .filter(QuadRotation.element_id == quad.id)
                .filter(QuadRotation.result_category_id == self.result_category_id)
                .all()
            )

            story_data = {}
            story_sort_orders = {}
            for rotation, case_name, story in rotations:
                if story.id not in story_data:
                    story_data[story.id] = {}
                    story_sort_orders[story.id] = rotation.story_sort_order
                # Use max_rotation for NLTHA envelope data (consistent with All Rotations view)
                # Fall back to rotation for pushover/single-case data
                value = rotation.max_rotation if rotation.max_rotation is not None else rotation.rotation
                story_data[story.id][case_name] = value

            for story_id, results_matrix in story_data.items():
                self._element_cache_repo.upsert_cache_entry(
                    project_id=self.project_id,
                    element_id=quad.id,
                    story_id=story_id,
                    result_type="QuadRotations_Pier",
                    results_matrix=results_matrix,
                    result_set_id=self.result_set_id,
                    story_sort_order=story_sort_orders.get(story_id),
                )

    def _cache_column_rotations(self, stories):
        columns = self._element_repo.get_by_project(self.project_id, element_type="Column")

        for column in columns:
            for direction in ["R2", "R3"]:
                result_type = f"ColumnRotations_{direction}"

                rotations = (
                    self.session.query(ColumnRotation, LoadCase.name, Story)
                    .join(LoadCase, ColumnRotation.load_case_id == LoadCase.id)
                    .join(Story, ColumnRotation.story_id == Story.id)
                    .filter(ColumnRotation.element_id == column.id)
                    .filter(ColumnRotation.direction == direction)
                    .filter(ColumnRotation.result_category_id == self.result_category_id)
                    .all()
                )

                story_data = {}
                story_sort_orders = {}
                for rotation, case_name, story in rotations:
                    if story.id not in story_data:
                        story_data[story.id] = {}
                        story_sort_orders[story.id] = rotation.story_sort_order
                    # Use max_rotation for NLTHA envelope data (consistent with All Rotations view)
                    # Fall back to rotation for pushover/single-case data
                    value = rotation.max_rotation if rotation.max_rotation is not None else rotation.rotation
                    story_data[story.id][case_name] = value

                for story_id, results_matrix in story_data.items():
                    self._element_cache_repo.upsert_cache_entry(
                        project_id=self.project_id,
                        element_id=column.id,
                        story_id=story_id,
                        result_type=result_type,
                        results_matrix=results_matrix,
                        result_set_id=self.result_set_id,
                        story_sort_order=story_sort_orders.get(story_id),
                    )

    def _cache_beam_rotations(self, stories):
        # Query all beam rotations at once, ordered by source appearance (BeamRotation.id)
        # This preserves the element and story order from the source Excel file
        rotations = (
            self.session.query(BeamRotation, LoadCase.name, Story, Element)
            .join(LoadCase, BeamRotation.load_case_id == LoadCase.id)
            .join(Story, BeamRotation.story_id == Story.id)
            .join(Element, BeamRotation.element_id == Element.id)
            .filter(Element.project_id == self.project_id)
            .filter(Element.element_type == "Beam")
            .filter(BeamRotation.result_category_id == self.result_category_id)
            .order_by(BeamRotation.id)  # Preserve source order
            .all()
        )

        # Group by element and story, preserving first-occurrence order
        # Structure: {element_id: {story_id: {load_case: value, ...}}}
        element_story_data = {}
        story_sort_orders = {}

        for rotation, case_name, story, element in rotations:
            elem_id = element.id
            if elem_id not in element_story_data:
                element_story_data[elem_id] = {}
            if story.id not in element_story_data[elem_id]:
                element_story_data[elem_id][story.id] = {}
                # Track story sort order per element-story pair
                key = (elem_id, story.id)
                if key not in story_sort_orders:
                    story_sort_orders[key] = rotation.story_sort_order

            # Use max_r3_plastic for NLTHA envelope data (consistent with All Rotations view)
            # Fall back to r3_plastic for pushover/single-case data
            value = rotation.max_r3_plastic if rotation.max_r3_plastic is not None else rotation.r3_plastic
            element_story_data[elem_id][story.id][case_name] = value

        # Create cache entries in the order elements/stories first appeared
        for elem_id, story_data in element_story_data.items():
            for story_id, results_matrix in story_data.items():
                self._element_cache_repo.upsert_cache_entry(
                    project_id=self.project_id,
                    element_id=elem_id,
                    story_id=story_id,
                    result_type="BeamRotations_R3Plastic",
                    results_matrix=results_matrix,
                    result_set_id=self.result_set_id,
                    story_sort_order=story_sort_orders.get((elem_id, story_id)),
                )

    # ------------------------------------------------------------------
    # Joint caches
    # ------------------------------------------------------------------
    def _cache_soil_pressures(self):
        pressures = (
            self.session.query(SoilPressure, LoadCase.name)
            .join(LoadCase, SoilPressure.load_case_id == LoadCase.id)
            .filter(SoilPressure.project_id == self.project_id)
            .filter(SoilPressure.result_set_id == self.result_set_id)
            .order_by(LoadCase.name)
            .all()
        )

        element_matrices = {}
        shell_objects = {}

        for pressure, load_case_name in pressures:
            unique_name = pressure.unique_name
            if unique_name not in element_matrices:
                element_matrices[unique_name] = {}
                shell_objects[unique_name] = pressure.shell_object

            element_matrices[unique_name][load_case_name] = pressure.min_pressure

        for unique_name, results_matrix in element_matrices.items():
            sorted_results_matrix = dict(sorted(results_matrix.items()))
            self._joint_cache_repo.upsert_cache_entry(
                project_id=self.project_id,
                result_set_id=self.result_set_id,
                result_type="SoilPressures_Min",
                shell_object=shell_objects[unique_name],
                unique_name=unique_name,
                results_matrix=sorted_results_matrix,
            )

    def _cache_vertical_displacements(self):
        displacements = (
            self.session.query(VerticalDisplacement, LoadCase.name)
            .join(LoadCase, VerticalDisplacement.load_case_id == LoadCase.id)
            .filter(VerticalDisplacement.project_id == self.project_id)
            .filter(VerticalDisplacement.result_set_id == self.result_set_id)
            .order_by(LoadCase.name)
            .all()
        )

        joint_matrices = {}
        joint_labels = {}

        for disp, load_case_name in displacements:
            unique_name = disp.unique_name
            if unique_name not in joint_matrices:
                joint_matrices[unique_name] = {}
                joint_labels[unique_name] = disp.label

            joint_matrices[unique_name][load_case_name] = disp.min_displacement

        for unique_name, results_matrix in joint_matrices.items():
            sorted_results_matrix = dict(sorted(results_matrix.items()))
            self._joint_cache_repo.upsert_cache_entry(
                project_id=self.project_id,
                result_set_id=self.result_set_id,
                result_type="VerticalDisplacements_Min",
                shell_object=joint_labels[unique_name],
                unique_name=unique_name,
                results_matrix=sorted_results_matrix,
            )

    # ------------------------------------------------------------------
    # Envelope helpers
    # ------------------------------------------------------------------
    def _calculate_absolute_maxmin(self, stories):
        drifts = (
            self.session.query(StoryDrift, LoadCase, Story)
            .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
            .join(Story, StoryDrift.story_id == Story.id)
            .filter(
                and_(
                    Story.project_id == self.project_id,
                    StoryDrift.result_category_id == self.result_category_id,
                )
            )
            .all()
        )

        self._abs_repo.delete_by_result_set(self.project_id, self.result_set_id)

        if not drifts:
            return

        aggregates: Dict[Tuple[int, int, str], Dict[str, Any]] = {}

        for drift, load_case, story in drifts:
            key = (story.id, load_case.id, drift.direction)
            max_val = drift.max_drift if drift.max_drift is not None else drift.drift
            min_val = drift.min_drift if drift.min_drift is not None else drift.drift

            if abs(max_val) >= abs(min_val):
                abs_val = abs(max_val)
                sign = "positive" if max_val >= 0 else "negative"
                source_max = max_val
                source_min = min_val
            else:
                abs_val = abs(min_val)
                sign = "positive" if min_val >= 0 else "negative"
                source_max = max_val
                source_min = min_val

            current = aggregates.get(key)
            if not current or abs_val > current["absolute_max_drift"]:
                aggregates[key] = {
                    "project_id": self.project_id,
                    "result_set_id": self.result_set_id,
                    "story_id": story.id,
                    "load_case_id": load_case.id,
                    "direction": drift.direction,
                    "absolute_max_drift": abs_val,
                    "sign": sign,
                    "original_max": source_max,
                    "original_min": source_min,
                }

        if aggregates:
            self._abs_repo.bulk_create(list(aggregates.values()))
