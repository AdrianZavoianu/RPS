from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from .cache_builder import build_element_dataset, build_standard_dataset
from .maxmin_builder import build_drift_maxmin_dataset, build_generic_maxmin_dataset
from .metadata import build_display_label
from .models import MaxMinDataset, ResultDataset, ResultDatasetMeta
from .story_loader import StoryProvider


class ResultDataService:
    """Fetches and caches result datasets for UI presentation."""

    def __init__(
        self,
        project_id: int,
        cache_repo,
        story_repo,
        load_case_repo,
        abs_maxmin_repo=None,
        element_cache_repo=None,
        element_repo=None,
        session=None,
    ) -> None:
        self.project_id = project_id
        self.cache_repo = cache_repo
        self.story_repo = story_repo
        self.load_case_repo = load_case_repo
        self.abs_maxmin_repo = abs_maxmin_repo
        self.element_cache_repo = element_cache_repo
        self.element_repo = element_repo
        self.session = session

        self._standard_cache: Dict[Tuple[str, str, int], Optional[ResultDataset]] = {}
        self._maxmin_cache: Dict[Tuple[str, int], Optional[MaxMinDataset]] = {}
        self._element_cache: Dict[Tuple[int, str, str, int], Optional[ResultDataset]] = {}
        self._category_cache: Dict[int, Optional[int]] = {}

        self._stories = StoryProvider(self.story_repo, self.project_id)

    # ------------------------------------------------------------------
    # Standard datasets
    # ------------------------------------------------------------------

    def get_standard_dataset(
        self, result_type: str, direction: str, result_set_id: int
    ) -> Optional[ResultDataset]:
        cache_key = (result_type, direction, result_set_id)
        if cache_key in self._standard_cache:
            return self._standard_cache[cache_key]

        cache_entries = self.cache_repo.get_cache_for_display(
            project_id=self.project_id,
            result_type=result_type,
            result_set_id=result_set_id,
        )

        if not cache_entries:
            self._standard_cache[cache_key] = None
            return None

        dataset = build_standard_dataset(
            project_id=self.project_id,
            result_type=result_type,
            direction=direction,
            result_set_id=result_set_id,
            cache_entries=cache_entries,
            story_provider=self._stories,
        )

        self._standard_cache[cache_key] = dataset
        return dataset

    def invalidate_standard_dataset(
        self, result_type: str, direction: str, result_set_id: int
    ) -> None:
        cache_key = (result_type, direction, result_set_id)
        self._standard_cache.pop(cache_key, None)

    # ------------------------------------------------------------------
    # Element datasets
    # ------------------------------------------------------------------

    def get_element_dataset(
        self, element_id: int, result_type: str, direction: str, result_set_id: int
    ) -> Optional[ResultDataset]:
        if not self.element_cache_repo:
            return None

        cache_key = (element_id, result_type, direction, result_set_id)
        if cache_key in self._element_cache:
            return self._element_cache[cache_key]

        # Build full result type key (e.g., 'WallShears_V2', or 'QuadRotations' if no direction)
        if direction:
            full_result_type = f"{result_type}_{direction}"
        else:
            full_result_type = result_type

        cache_entries = self.element_cache_repo.get_cache_for_display(
            project_id=self.project_id,
            element_id=element_id,
            result_type=full_result_type,
            result_set_id=result_set_id,
        )

        if not cache_entries:
            self._element_cache[cache_key] = None
            return None

        dataset = build_element_dataset(
            project_id=self.project_id,
            element_id=element_id,
            result_type=result_type,
            direction=direction,
            result_set_id=result_set_id,
            cache_entries=cache_entries,
            story_provider=self._stories,
        )

        self._element_cache[cache_key] = dataset
        return dataset

    def invalidate_element_dataset(
        self, element_id: int, result_type: str, direction: str, result_set_id: int
    ) -> None:
        cache_key = (element_id, result_type, direction, result_set_id)
        self._element_cache.pop(cache_key, None)

    # ------------------------------------------------------------------
    # Max/min datasets
    # ------------------------------------------------------------------

    def get_maxmin_dataset(
        self,
        result_set_id: int,
        base_result_type: str = "Drifts",
    ) -> Optional[MaxMinDataset]:
        cache_key = (base_result_type, result_set_id)
        if cache_key in self._maxmin_cache:
            return self._maxmin_cache[cache_key]

        if base_result_type == "Drifts":
            if not self.abs_maxmin_repo:
                return None
            dataset = build_drift_maxmin_dataset(
                project_id=self.project_id,
                result_set_id=result_set_id,
                abs_maxmin_repo=self.abs_maxmin_repo,
                story_provider=self._stories,
                load_case_repo=self.load_case_repo,
            )
        else:
            if not self.session:
                return None
            dataset = build_generic_maxmin_dataset(
                project_id=self.project_id,
                result_set_id=result_set_id,
                base_result_type=base_result_type,
                session=self.session,
                category_id_provider=self._get_global_category_id,
                story_provider=self._stories,
            )

        self._maxmin_cache[cache_key] = dataset
        return dataset

    def invalidate_maxmin_dataset(
        self, result_set_id: int, base_result_type: str = "Drifts"
    ) -> None:
        cache_key = (base_result_type, result_set_id)
        self._maxmin_cache.pop(cache_key, None)

    # ------------------------------------------------------------------
    # Element max/min + rotation helpers
    # ------------------------------------------------------------------

    def get_element_maxmin_dataset(
        self,
        element_id: int,
        result_set_id: int,
        base_result_type: str = "WallShears",
    ) -> Optional[MaxMinDataset]:
        """Return absolute max/min dataset for element-specific results."""
        if not self.session or not self.element_repo:
            return None

        element = self.element_repo.get_by_id(element_id)
        if not element:
            return None

        from database.models import (
            QuadRotation,
            WallShear,
            ColumnShear,
            ColumnRotation,
            BeamRotation,
            LoadCase,
            Story,
        )

        if base_result_type == "WallShears":
            model = WallShear
            max_attr = "max_force"
            min_attr = "min_force"
            direction_attr = "direction"
            multiplier = 1.0
        elif base_result_type == "ColumnShears":
            model = ColumnShear
            max_attr = "max_force"
            min_attr = "min_force"
            direction_attr = "direction"
            multiplier = 1.0
        elif base_result_type == "ColumnRotations":
            model = ColumnRotation
            max_attr = "max_rotation"
            min_attr = "min_rotation"
            direction_attr = "direction"  # R2, R3
            multiplier = 100.0  # radians to %
        elif base_result_type == "BeamRotations":
            model = BeamRotation
            max_attr = "max_r3_plastic"
            min_attr = "min_r3_plastic"
            direction_attr = None
            multiplier = 100.0  # radians to %
        elif base_result_type == "QuadRotations":
            model = QuadRotation
            max_attr = "max_rotation"
            min_attr = "min_rotation"
            direction_attr = None
            multiplier = 100.0  # radians to %
        else:
            return None

        records = (
            self.session.query(model, LoadCase, Story)
            .join(LoadCase, model.load_case_id == LoadCase.id)
            .join(Story, model.story_id == Story.id)
            .filter(
                Story.project_id == self.project_id,
                model.element_id == element_id,
            )
            .all()
        )

        if not records:
            return None

        self._stories.ensure_loaded()
        story_lookup = {story.id: story for story in self._stories.stories}

        data_by_story: Dict[int, Dict[str, object]] = {}
        story_sort_orders: Dict[int, int] = {}
        directions_seen: Set[str] = set()

        for record, load_case, story in records:
            story_obj = story_lookup.get(story.id)
            if not story_obj:
                continue

            if story.id not in story_sort_orders:
                story_sort_orders[story.id] = getattr(record, "story_sort_order", None) or 0

            if direction_attr:
                direction = getattr(record, direction_attr, "") or ""
                directions_seen.add(direction)
            else:
                direction = ""
                if not directions_seen:
                    directions_seen.add(direction)

            max_val = getattr(record, max_attr, None)
            min_val = getattr(record, min_attr, None)
            if max_val is None and min_val is None:
                continue

            row = data_by_story.setdefault(story.id, {"Story": story_obj.name})
            load_case_name = load_case.name

            if max_val is not None:
                key = f"Max_{load_case_name}_{direction}" if direction else f"Max_{load_case_name}"
                row[key] = abs(max_val) * multiplier
            if min_val is not None:
                key = f"Min_{load_case_name}_{direction}" if direction else f"Min_{load_case_name}"
                row[key] = abs(min_val) * multiplier

        if not data_by_story:
            return None

        ordered_rows: List[Dict[str, object]] = [
            data_by_story[story_id]
            for story_id in sorted(
                data_by_story.keys(),
                key=lambda sid: (story_sort_orders.get(sid, 0), story_lookup[sid].name or ""),
            )
        ]

        df = pd.DataFrame(ordered_rows)
        result_type_key = f"MaxMin{base_result_type}"

        return MaxMinDataset(
            meta=ResultDatasetMeta(
                result_type=result_type_key,
                direction=None,
                result_set_id=result_set_id,
                display_name=build_display_label(result_type_key, None),
            ),
            data=df,
            directions=tuple(sorted(directions_seen)) or ("",),
            source_type=base_result_type,
        )

    def get_all_quad_rotations_dataset(
        self, result_set_id: int, max_min: str = "Max"
    ) -> Optional[pd.DataFrame]:
        """Return quad rotation points (all elements) for scatter visuals."""
        if not self.session or not self.element_repo:
            return None

        from database.models import QuadRotation, LoadCase, Story, Element

        records = (
            self.session.query(QuadRotation, LoadCase, Story, Element)
            .join(LoadCase, QuadRotation.load_case_id == LoadCase.id)
            .join(Story, QuadRotation.story_id == Story.id)
            .join(Element, QuadRotation.element_id == Element.id)
            .filter(Story.project_id == self.project_id)
            .all()
        )

        if not records:
            return None

        data_rows: List[Dict[str, object]] = []
        for rotation, load_case, story, element in records:
            value = rotation.max_rotation if max_min == "Max" else rotation.min_rotation
            if value is None:
                continue

            data_rows.append(
                {
                    "Element": element.name,
                    "Story": story.name,
                    "LoadCase": load_case.name,
                    "Rotation": value * 100.0,
                    "StoryOrder": story.sort_order or 0,
                    "StoryIndex": story.sort_order or 0,
                }
            )

        if not data_rows:
            return None

        df = pd.DataFrame(data_rows)
        return df.sort_values(by="StoryOrder", ascending=True).reset_index(drop=True)

    def get_all_column_rotations_dataset(
        self, result_set_id: int, max_min: str = "Max"
    ) -> Optional[pd.DataFrame]:
        """Return column rotation points (all elements) for scatter visuals."""
        if not self.session or not self.element_repo:
            return None

        from database.models import ColumnRotation, LoadCase, Story, Element

        records = (
            self.session.query(ColumnRotation, LoadCase, Story, Element)
            .join(LoadCase, ColumnRotation.load_case_id == LoadCase.id)
            .join(Story, ColumnRotation.story_id == Story.id)
            .join(Element, ColumnRotation.element_id == Element.id)
            .filter(Story.project_id == self.project_id)
            .all()
        )

        if not records:
            return None

        data_rows: List[Dict[str, object]] = []
        for rotation, load_case, story, element in records:
            value = rotation.max_rotation if max_min == "Max" else rotation.min_rotation
            if value is None:
                continue

            data_rows.append(
                {
                    "Element": element.name,
                    "Story": story.name,
                    "LoadCase": load_case.name,
                    "Direction": rotation.direction,  # R2 or R3
                    "Rotation": value * 100.0,
                    "StoryOrder": story.sort_order or 0,
                    "StoryIndex": story.sort_order or 0,
                }
            )

        if not data_rows:
            return None

        df = pd.DataFrame(data_rows)
        return df.sort_values(by="StoryOrder", ascending=True).reset_index(drop=True)

    def get_all_beam_rotations_dataset(
        self, result_set_id: int, max_min: str = "Max"
    ) -> Optional[pd.DataFrame]:
        """Return beam rotation points (all elements) for scatter visuals."""
        if not self.session or not self.element_repo:
            return None

        from database.models import BeamRotation, LoadCase, Story, Element

        records = (
            self.session.query(BeamRotation, LoadCase, Story, Element)
            .join(LoadCase, BeamRotation.load_case_id == LoadCase.id)
            .join(Story, BeamRotation.story_id == Story.id)
            .join(Element, BeamRotation.element_id == Element.id)
            .filter(Story.project_id == self.project_id)
            .all()
        )

        if not records:
            return None

        data_rows: List[Dict[str, object]] = []
        for rotation, load_case, story, element in records:
            value = rotation.max_r3_plastic if max_min == "Max" else rotation.min_r3_plastic
            if value is None:
                continue

            data_rows.append(
                {
                    "Element": element.name,
                    "Story": story.name,
                    "LoadCase": load_case.name,
                    "Rotation": value * 100.0,
                    "StoryOrder": story.sort_order or 0,
                    "StoryIndex": story.sort_order or 0,
                }
            )

        if not data_rows:
            return None

        df = pd.DataFrame(data_rows)
        return df.sort_values(by="StoryOrder", ascending=True).reset_index(drop=True)

    def get_beam_rotations_table_dataset(self, result_set_id: int) -> Optional[pd.DataFrame]:
        """Return beam rotation data in wide format for table display."""
        if not self.session or not self.element_repo:
            return None

        from database.models import BeamRotation, LoadCase, Story, Element

        records = (
            self.session.query(BeamRotation, LoadCase, Story, Element)
            .join(LoadCase, BeamRotation.load_case_id == LoadCase.id)
            .join(Story, BeamRotation.story_id == Story.id)
            .join(Element, BeamRotation.element_id == Element.id)
            .filter(Story.project_id == self.project_id)
            .order_by(Story.sort_order, Element.name, LoadCase.name)
            .all()
        )

        if not records:
            return None

        load_cases = sorted({lc.name for _, lc, _, _ in records})
        data_dict: Dict[Tuple[str, str, str, float], Dict[str, object]] = {}

        for rotation, load_case, story, element in records:
            key = (story.name, element.name, rotation.generated_hinge or "", rotation.rel_dist or 0.0)
            entry = data_dict.setdefault(
                key,
                {
                    "Story": story.name,
                    "Frame/Wall": element.name,
                    "Unique Name": element.name,
                    "Hinge": rotation.hinge or "",
                    "Generated Hinge": rotation.generated_hinge or "",
                    "Rel Dist": rotation.rel_dist or 0.0,
                },
            )
            entry[load_case.name] = rotation.r3_plastic * 100.0

        df = pd.DataFrame(list(data_dict.values()))
        if df.empty:
            return None

        load_case_cols = [col for col in df.columns if col in load_cases]
        if load_case_cols:
            df["Avg"] = df[load_case_cols].mean(axis=1)
            df["Max"] = df[load_case_cols].max(axis=1)
            df["Min"] = df[load_case_cols].min(axis=1)

        return df

    # ------------------------------------------------------------------
    # Cache controls
    # ------------------------------------------------------------------

    def invalidate_all(self) -> None:
        self._standard_cache.clear()
        self._maxmin_cache.clear()
        self._element_cache.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _get_global_category_id(self, result_set_id: int) -> Optional[int]:
        if result_set_id in self._category_cache:
            return self._category_cache[result_set_id]

        if not self.session:
            self._category_cache[result_set_id] = None
            return None

        from database.models import ResultCategory

        category = (
            self.session.query(ResultCategory)
            .filter(
                ResultCategory.result_set_id == result_set_id,
                ResultCategory.category_name == "Envelopes",
                ResultCategory.category_type == "Global",
            )
            .first()
        )

        category_id = category.id if category else None
        self._category_cache[result_set_id] = category_id
        return category_id
