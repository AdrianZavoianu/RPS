"""Service for assembling result datasets used by the UI."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING, Set

import pandas as pd

from config.result_config import ResultTypeConfig, get_config
from processing.result_transformers import get_transformer

if TYPE_CHECKING:
    from database.repository import (
        AbsoluteMaxMinDriftRepository,
        CacheRepository,
        LoadCaseRepository,
        StoryRepository,
    )
    from database.models import LoadCase, Story


DISPLAY_NAME_OVERRIDES = {
    "Drifts": "Story Drifts",
    "Accelerations": "Story Accelerations",
    "Forces": "Story Shears",
    "Displacements": "Floors Displacements",
    "MaxMinDrifts": "Max/Min Drifts",
    "MaxMinAccelerations": "Max/Min Accelerations",
    "MaxMinForces": "Max/Min Story Shears",
    "MaxMinDisplacements": "Max/Min Floors Displacements",
}


@dataclass(frozen=True)
class ResultDatasetMeta:
    """Identifying metadata for a dataset."""

    result_type: str
    direction: Optional[str]
    result_set_id: int
    display_name: str


@dataclass
class ResultDataset:
    """Container for a transformed result dataset."""

    meta: ResultDatasetMeta
    data: pd.DataFrame
    config: ResultTypeConfig
    load_case_columns: List[str]
    summary_columns: List[str] = field(default_factory=list)


@dataclass
class MaxMinDataset:
    """Container for absolute max/min drift data across both directions."""

    meta: ResultDatasetMeta
    data: pd.DataFrame
    directions: Tuple[str, ...] = ("X", "Y")
    source_type: str = "Drifts"


class ResultDataService:
    """Fetches and caches result datasets for UI presentation."""

    SUMMARY_COLUMNS = ("Avg", "Max", "Min")

    def __init__(
        self,
        project_id: int,
        cache_repo: "CacheRepository",
        story_repo: "StoryRepository",
        load_case_repo: "LoadCaseRepository",
        abs_maxmin_repo: Optional["AbsoluteMaxMinDriftRepository"] = None,
        session=None,
    ) -> None:
        self.project_id = project_id
        self.cache_repo = cache_repo
        self.story_repo = story_repo
        self.load_case_repo = load_case_repo
        self.abs_maxmin_repo = abs_maxmin_repo
        self.session = session

        self._story_index: Dict[int, Tuple[int, str]] = {}
        self._stories: List["Story"] = []

        self._standard_cache: Dict[Tuple[str, str, int], Optional[ResultDataset]] = {}
        self._maxmin_cache: Dict[Tuple[str, int], Optional[MaxMinDataset]] = {}
        self._category_cache: Dict[int, Optional[int]] = {}

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def get_standard_dataset(
        self, result_type: str, direction: str, result_set_id: int
    ) -> Optional[ResultDataset]:
        """Return a transformed dataset for table/plot presentation."""

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

        ordered_entries = self._order_cache_entries(cache_entries)
        dataframe = self._build_dataframe(ordered_entries, result_type, direction)

        if dataframe.empty:
            self._standard_cache[cache_key] = None
            return None

        meta = ResultDatasetMeta(
            result_type=result_type,
            direction=direction,
            result_set_id=result_set_id,
            display_name=self._build_display_label(result_type, direction),
        )

        config_key = f"{result_type}_{direction}" if direction else result_type
        config = get_config(config_key)

        summary_columns = [col for col in self.SUMMARY_COLUMNS if col in dataframe.columns]
        load_case_columns = [
            col for col in dataframe.columns if col not in summary_columns and col != "Story"
        ]

        dataset = ResultDataset(
            meta=meta,
            data=dataframe,
            config=config,
            load_case_columns=load_case_columns,
            summary_columns=summary_columns,
        )

        self._standard_cache[cache_key] = dataset
        return dataset

    def invalidate_standard_dataset(
        self, result_type: str, direction: str, result_set_id: int
    ) -> None:
        """Remove a cached dataset so it will be re-fetched next time."""
        cache_key = (result_type, direction, result_set_id)
        self._standard_cache.pop(cache_key, None)

    def invalidate_maxmin_dataset(self, result_set_id: int, base_result_type: str = "Drifts") -> None:
        """Remove cached absolute max/min dataset for a result set."""
        cache_key = (base_result_type, result_set_id)
        self._maxmin_cache.pop(cache_key, None)

    def invalidate_all(self) -> None:
        """Clear all cached datasets."""
        self._standard_cache.clear()
        self._maxmin_cache.clear()
        self._category_cache.clear()

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    def _ensure_stories_loaded(self) -> None:
        if self._stories:
            return

        stories = self.story_repo.get_by_project(self.project_id)
        # Sort by sort_order ascending (bottom to top) then name
        stories.sort(key=lambda s: ((s.sort_order or 0), s.name or ""))
        self._stories = stories
        self._story_index = {
            story.id: (idx, story.name or "") for idx, story in enumerate(stories)
        }

    def _order_cache_entries(self, cache_entries):
        """Return cache entries ordered from top story to bottom story."""
        self._ensure_stories_loaded()

        def rank(story):
            index = self._story_index.get(story.id)
            if index is None:
                # Fallback: append to the end while preserving order
                return (len(self._stories), story.name or "")
            return index

        # Sort ascending using pre-computed rank, then reverse for top-to-bottom display
        sorted_entries = sorted(cache_entries, key=lambda item: rank(item[1]))
        return list(reversed(sorted_entries))

    def _build_dataframe(self, ordered_entries, result_type: str, direction: str) -> pd.DataFrame:
        """Construct a numeric DataFrame for presentation."""

        if not ordered_entries:
            return pd.DataFrame()

        story_labels: List[str] = []
        result_dicts: List[dict] = []

        for cache_entry, story in ordered_entries:
            story_labels.append(story.name)
            result_dicts.append(cache_entry.results_matrix or {})

        raw_df = pd.DataFrame(result_dicts)

        transformer_key = f"{result_type}_{direction}" if direction else result_type
        transformer = get_transformer(transformer_key)
        transformed_df = transformer.transform(raw_df)

        # Convert all values (except Story) to numeric and apply multiplier
        numeric_df = transformed_df.apply(pd.to_numeric, errors="coerce")

        config = get_config(transformer_key)
        value_columns = [
            col for col in numeric_df.columns if col not in self.SUMMARY_COLUMNS
        ]
        summary_columns = [
            col for col in self.SUMMARY_COLUMNS if col in numeric_df.columns
        ]

        if config.multiplier != 1.0:
            numeric_df[value_columns] = numeric_df[value_columns] * config.multiplier
            if summary_columns:
                numeric_df[summary_columns] = (
                    numeric_df[summary_columns] * config.multiplier
                )

        # Insert story labels as first column
        numeric_df.insert(0, "Story", story_labels)
        return numeric_df

    @staticmethod
    def _build_display_label(result_type: str, direction: Optional[str]) -> str:
        base_label = DISPLAY_NAME_OVERRIDES.get(result_type, result_type)
        if direction:
            return f"{base_label} - {direction} Direction"
        return base_label

    def get_maxmin_dataset(
        self,
        result_set_id: int,
        base_result_type: str = "Drifts",
    ) -> Optional[MaxMinDataset]:
        """Return absolute max/min dataset for a result set and result type."""

        cache_key = (base_result_type, result_set_id)
        if cache_key in self._maxmin_cache:
            return self._maxmin_cache[cache_key]

        if base_result_type == "Drifts":
            dataset = self._build_drift_maxmin_dataset(result_set_id)
        else:
            dataset = self._build_generic_maxmin_dataset(result_set_id, base_result_type)

        self._maxmin_cache[cache_key] = dataset
        return dataset

    def _build_drift_maxmin_dataset(self, result_set_id: int) -> Optional[MaxMinDataset]:
        """Existing absolute drift implementation (stored in dedicated table)."""
        if not self.abs_maxmin_repo:
            return None

        drifts = self.abs_maxmin_repo.get_by_result_set(
            project_id=self.project_id,
            result_set_id=result_set_id,
        )

        if not drifts:
            return None

        self._ensure_stories_loaded()

        story_lookup = {story.id: story for story in self._stories}
        load_case_cache: Dict[int, Optional["LoadCase"]] = {}
        data_by_story: Dict[int, Dict[str, object]] = {}

        for drift in drifts:
            story = story_lookup.get(drift.story_id)
            if not story:
                continue

            row = data_by_story.setdefault(drift.story_id, {"Story": story.name})

            if drift.load_case_id not in load_case_cache:
                load_case_cache[drift.load_case_id] = self.load_case_repo.get_by_id(
                    drift.load_case_id
                )

            load_case = load_case_cache.get(drift.load_case_id)
            load_case_name = getattr(load_case, "name", f"LC{drift.load_case_id}")
            direction = self._normalize_direction(drift.direction)
            if direction is None:
                continue

            row[f"Max_{load_case_name}_{direction}"] = drift.original_max * 100.0
            row[f"Min_{load_case_name}_{direction}"] = drift.original_min * 100.0

        if not data_by_story:
            return None

        ordered_rows = [
            data_by_story[story.id]
            for story in sorted(self._stories, key=lambda s: (s.sort_order or 0, s.name or ""))
            if story.id in data_by_story
        ]

        df = pd.DataFrame(ordered_rows)
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)

        dataset = MaxMinDataset(
            meta=ResultDatasetMeta(
                result_type="MaxMinDrifts",
                direction=None,
                result_set_id=result_set_id,
                display_name=DISPLAY_NAME_OVERRIDES["MaxMinDrifts"],
            ),
            data=df,
            directions=("X", "Y"),
            source_type="Drifts",
        )
        return dataset

    def _build_generic_maxmin_dataset(
        self,
        result_set_id: int,
        base_result_type: str,
    ) -> Optional[MaxMinDataset]:
        """Build max/min dataset for accelerations, forces, or displacements."""
        if not self.session:
            return None

        category_id = self._get_global_category_id(result_set_id)
        if not category_id:
            return None

        from database.models import (
            StoryAcceleration,
            StoryForce,
            StoryDisplacement,
            LoadCase,
            Story,
        )

        model = None
        max_attr = None
        min_attr = None

        if base_result_type == "Accelerations":
            model = StoryAcceleration
            max_attr = "max_acceleration"
            min_attr = "min_acceleration"
        elif base_result_type == "Forces":
            model = StoryForce
            max_attr = "max_force"
            min_attr = "min_force"
        elif base_result_type == "Displacements":
            model = StoryDisplacement
            max_attr = "max_displacement"
            min_attr = "min_displacement"
        else:
            return None

        records = (
            self.session.query(model, LoadCase, Story)
            .join(LoadCase, model.load_case_id == LoadCase.id)
            .join(Story, model.story_id == Story.id)
            .filter(
                Story.project_id == self.project_id,
                model.result_category_id == category_id,
            )
            .all()
        )

        if not records:
            return None

        self._ensure_stories_loaded()
        story_lookup = {story.id: story for story in self._stories}
        data_by_story: Dict[int, Dict[str, object]] = {}
        directions_seen: Set[str] = set()

        for record, load_case, story in records:
            story_obj = story_lookup.get(story.id)
            if not story_obj:
                continue

            direction = self._normalize_direction(getattr(record, "direction", ""))
            if direction is None:
                continue
            directions_seen.add(direction)

            max_val = getattr(record, max_attr, None)
            min_val = getattr(record, min_attr, None)

            if max_val is None and min_val is None:
                continue

            row = data_by_story.setdefault(story.id, {"Story": story_obj.name})
            load_case_name = load_case.name

            if max_val is not None:
                row[f"Max_{load_case_name}_{direction}"] = abs(max_val)
            if min_val is not None:
                row[f"Min_{load_case_name}_{direction}"] = abs(min_val)

        if not data_by_story:
            return None

        ordered_rows = [
            data_by_story[story.id]
            for story in sorted(self._stories, key=lambda s: (s.sort_order or 0, s.name or ""))
            if story.id in data_by_story
        ]

        df = pd.DataFrame(ordered_rows)
        if not df.empty:
            df = df.iloc[::-1].reset_index(drop=True)

        result_type_key = f"MaxMin{base_result_type}"
        dataset = MaxMinDataset(
            meta=ResultDatasetMeta(
                result_type=result_type_key,
                direction=None,
                result_set_id=result_set_id,
                display_name=DISPLAY_NAME_OVERRIDES.get(result_type_key, f"Max/Min {base_result_type}"),
            ),
            data=df,
            directions=tuple(sorted(directions_seen)) or ("X", "Y"),
            source_type=base_result_type,
        )
        return dataset

    def _get_global_category_id(self, result_set_id: int) -> Optional[int]:
        """Memoized lookup for the 'Envelopes/Global' category id."""
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

    @staticmethod
    def _normalize_direction(direction: Optional[str]) -> Optional[str]:
        """Normalize raw direction (UX, VX, X) into X/Y for plotting."""
        if not direction:
            return None
        raw = direction.strip().upper()
        if raw.endswith("X"):
            return "X"
        if raw.endswith("Y"):
            return "Y"
        if raw in {"X", "Y"}:
            return raw
        return None
