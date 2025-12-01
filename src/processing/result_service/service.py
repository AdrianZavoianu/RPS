from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

from config.result_config import get_config
from database.element_result_repository import ElementResultQueryRepository

from .comparison_builder import build_element_comparison, build_global_comparison, build_joint_comparison
from .maxmin_builder import build_drift_maxmin_dataset, build_generic_maxmin_dataset
from .metadata import build_display_label
from .models import ComparisonDataset, MaxMinDataset, ResultDataset, ResultDatasetMeta
from .providers import (
    ElementDatasetProvider,
    JointDatasetProvider,
    ResultCategory,
    StandardDatasetProvider,
)
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
        joint_cache_repo=None,
        session=None,
    ) -> None:
        self.project_id = project_id
        self.cache_repo = cache_repo
        self.story_repo = story_repo
        self.load_case_repo = load_case_repo
        self.abs_maxmin_repo = abs_maxmin_repo
        self.element_cache_repo = element_cache_repo
        self.element_repo = element_repo
        self.joint_cache_repo = joint_cache_repo
        self.session = session

        self._maxmin_cache: Dict[Tuple[str, int], Optional[MaxMinDataset]] = {}
        self._category_cache: Dict[int, Optional[int]] = {}
        self._comparison_cache: Dict[Tuple, Optional[ComparisonDataset]] = {}

        self._stories = StoryProvider(self.story_repo, self.project_id)
        self._dataset_providers = {
            ResultCategory.GLOBAL: StandardDatasetProvider(
                project_id=self.project_id,
                cache_repo=self.cache_repo,
                story_provider=self._stories,
            ),
            ResultCategory.ELEMENT: ElementDatasetProvider(
                project_id=self.project_id,
                element_cache_repo=self.element_cache_repo,
                story_provider=self._stories,
            ),
            ResultCategory.JOINT: JointDatasetProvider(
                project_id=self.project_id,
                joint_cache_repo=self.joint_cache_repo,
            ),
        }
        self._element_result_query_repo = (
            ElementResultQueryRepository(self.session) if self.session else None
        )

    # ------------------------------------------------------------------
    # Standard datasets
    # ------------------------------------------------------------------

    def get_standard_dataset(
        self, result_type: str, direction: str, result_set_id: int
    ) -> Optional[ResultDataset]:
        provider = self._dataset_providers[ResultCategory.GLOBAL]
        return provider.get(result_type, direction, result_set_id)

    def invalidate_standard_dataset(
        self, result_type: str, direction: str, result_set_id: int
    ) -> None:
        provider = self._dataset_providers[ResultCategory.GLOBAL]
        provider.invalidate(result_type, direction, result_set_id)

    # ------------------------------------------------------------------
    # Element datasets
    # ------------------------------------------------------------------

    def get_element_dataset(
        self, element_id: int, result_type: str, direction: str, result_set_id: int
    ) -> Optional[ResultDataset]:
        provider = self._dataset_providers[ResultCategory.ELEMENT]
        return provider.get(element_id, result_type, direction, result_set_id)

    def invalidate_element_dataset(
        self, element_id: int, result_type: str, direction: str, result_set_id: int
    ) -> None:
        provider = self._dataset_providers[ResultCategory.ELEMENT]
        provider.invalidate(element_id, result_type, direction, result_set_id)

    # ------------------------------------------------------------------
    # Joint datasets (for soil pressures and other joint-based results)
    # ------------------------------------------------------------------

    def get_joint_dataset(
        self, result_type: str, result_set_id: int
    ) -> Optional[ResultDataset]:
        provider = self._dataset_providers[ResultCategory.JOINT]
        return provider.get(result_type, result_set_id)

    def invalidate_joint_dataset(self, result_type: str, result_set_id: int) -> None:
        provider = self._dataset_providers[ResultCategory.JOINT]
        provider.invalidate(result_type, result_set_id)

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
        if not self.session or not self.element_repo or not self._element_result_query_repo:
            return None

        element = self.element_repo.get_by_id(element_id)
        if not element:
            return None

        query_result = self._element_result_query_repo.fetch_records(
            base_result_type=base_result_type,
            project_id=self.project_id,
            element_id=element_id,
        )

        if not query_result:
            return None

        records, model_info = query_result
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

            if model_info.direction_attr:
                direction = getattr(record, model_info.direction_attr, "") or ""
                directions_seen.add(direction)
            else:
                direction = ""
                directions_seen.add(direction)

            max_val = getattr(record, model_info.max_attr, None)
            min_val = getattr(record, model_info.min_attr, None)
            if max_val is None and min_val is None:
                continue

            row = data_by_story.setdefault(story.id, {"Story": story_obj.name})
            load_case_name = load_case.name

            if max_val is not None:
                key = f"Max_{load_case_name}_{direction}" if direction else f"Max_{load_case_name}"
                row[key] = abs(max_val) * model_info.multiplier
            if min_val is not None:
                key = f"Min_{load_case_name}_{direction}" if direction else f"Min_{load_case_name}"
                row[key] = abs(min_val) * model_info.multiplier

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
            # For pushover data, max_rotation and min_rotation are None, use rotation field
            # For NLTHA envelope data, use max_rotation or min_rotation
            if rotation.max_rotation is not None or rotation.min_rotation is not None:
                # NLTHA envelope data
                value = rotation.max_rotation if max_min == "Max" else rotation.min_rotation
            else:
                # Pushover data (or NLTHA single case) - use rotation field
                # Only include in "Max" call to avoid duplicates
                if max_min != "Max":
                    continue
                value = rotation.rotation

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
            # For pushover data, max_r3_plastic and min_r3_plastic are None, use r3_plastic field
            # For NLTHA envelope data, use max_r3_plastic or min_r3_plastic
            if rotation.max_r3_plastic is not None or rotation.min_r3_plastic is not None:
                # NLTHA envelope data
                value = rotation.max_r3_plastic if max_min == "Max" else rotation.min_r3_plastic
            else:
                # Pushover data (or NLTHA single case) - use r3_plastic field
                # Only include in "Max" call to avoid duplicates
                if max_min != "Max":
                    continue
                value = rotation.r3_plastic

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
    # Comparison datasets
    # ------------------------------------------------------------------

    def get_comparison_dataset(
        self,
        result_type: str,
        direction: Optional[str],
        result_set_ids: List[int],
        metric: str = 'Avg',
        element_id: Optional[int] = None,
        unique_name: Optional[str] = None
    ) -> Optional[ComparisonDataset]:
        """
        Get comparison dataset for multiple result sets.

        Args:
            result_type: Result type (e.g., 'Drifts', 'WallShears', 'SoilPressures_Min')
            direction: Direction (e.g., 'X', 'V2')
            result_set_ids: List of result set IDs to compare
            metric: Metric to extract ('Avg', 'Max', 'Min')
            element_id: Element ID for element comparisons (None for global)
            unique_name: Unique name for joint comparisons (e.g., foundation element name)

        Returns:
            ComparisonDataset with merged data and warnings
        """
        if not result_set_ids:
            return None

        # Determine scope type
        if unique_name is not None:
            scope = 'joint'
        elif element_id is not None:
            scope = 'element'
        else:
            scope = 'global'

        # Create cache key with frozenset for unordered result set IDs
        cache_key = (
            scope,
            result_type,
            direction,
            element_id,
            unique_name,
            frozenset(result_set_ids),
            metric
        )

        if cache_key in self._comparison_cache:
            return self._comparison_cache[cache_key]

        # Get result type config
        transformer_key = f"{result_type}_{direction}" if direction else result_type
        config = get_config(transformer_key)

        # Get result set repository
        if not self.session:
            return None

        from database.repository import ResultSetRepository
        result_set_repo = ResultSetRepository(self.session)

        # Build comparison dataset based on scope
        if unique_name is not None:
            # Joint comparison (soil pressures, vertical displacements)
            dataset = build_joint_comparison(
                result_type=result_type,
                unique_name=unique_name,
                result_set_ids=result_set_ids,
                config=config,
                get_dataset_func=self.get_joint_dataset,
                result_set_repo=result_set_repo
            )
        elif element_id is not None:
            # Element comparison
            dataset = build_element_comparison(
                result_type=result_type,
                direction=direction,
                element_id=element_id,
                result_set_ids=result_set_ids,
                metric=metric,
                config=config,
                get_dataset_func=self.get_element_dataset,
                result_set_repo=result_set_repo
            )
        else:
            # Global comparison
            dataset = build_global_comparison(
                result_type=result_type,
                direction=direction,
                result_set_ids=result_set_ids,
                metric=metric,
                config=config,
                get_dataset_func=self.get_standard_dataset,
                result_set_repo=result_set_repo
            )

        self._comparison_cache[cache_key] = dataset
        return dataset

    def invalidate_comparison_cache(self) -> None:
        """Clear all comparison cache entries."""
        self._comparison_cache.clear()

    # ------------------------------------------------------------------
    # Cache controls
    # ------------------------------------------------------------------

    def invalidate_all(self) -> None:
        for provider in self._dataset_providers.values():
            provider.clear()
        self._maxmin_cache.clear()
        self._comparison_cache.clear()

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
