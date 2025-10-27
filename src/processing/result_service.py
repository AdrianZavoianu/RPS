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
    "WallShears": "Wall Shears",
    "QuadRotations": "Quad Rotations",
    "MaxMinDrifts": "Max/Min Drifts",
    "MaxMinAccelerations": "Max/Min Accelerations",
    "MaxMinForces": "Max/Min Story Shears",
    "MaxMinDisplacements": "Max/Min Floors Displacements",
    "MaxMinQuadRotations": "Max/Min Quad Rotations",
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
        element_cache_repo: Optional["ElementCacheRepository"] = None,
        element_repo: Optional["ElementRepository"] = None,
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

        self._story_index: Dict[int, Tuple[int, str]] = {}
        self._stories: List["Story"] = []

        self._standard_cache: Dict[Tuple[str, str, int], Optional[ResultDataset]] = {}
        self._maxmin_cache: Dict[Tuple[str, int], Optional[MaxMinDataset]] = {}
        self._element_cache: Dict[Tuple[int, str, str, int], Optional[ResultDataset]] = {}
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
        self._element_cache.clear()

    def get_element_dataset(
        self, element_id: int, result_type: str, direction: str, result_set_id: int
    ) -> Optional[ResultDataset]:
        """Return a transformed dataset for element-specific results (pier shears, etc.).

        Args:
            element_id: ID of the specific element (pier/wall)
            result_type: Base result type (e.g., 'WallShears')
            direction: Direction (e.g., 'V2', 'V3')
            result_set_id: Result set ID

        Returns:
            ResultDataset with stories × load cases for this specific element
        """
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

        # Order by story sort_order (same as global results)
        ordered_entries = self._order_element_cache_entries(cache_entries)
        dataframe = self._build_element_dataframe(ordered_entries, result_type, direction)

        if dataframe.empty:
            self._element_cache[cache_key] = None
            return None

        # Get element name for display
        element_name = "Element"
        if self.element_repo:
            element = self.element_repo.get_by_id(element_id)
            if element:
                element_name = element.name

        meta = ResultDatasetMeta(
            result_type=result_type,
            direction=direction,
            result_set_id=result_set_id,
            display_name=f"{element_name} - {self._build_display_label(result_type, direction)}",
        )

        config = get_config(full_result_type)

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

        self._element_cache[cache_key] = dataset
        return dataset

    def invalidate_element_dataset(
        self, element_id: int, result_type: str, direction: str, result_set_id: int
    ) -> None:
        """Remove a cached element dataset so it will be re-fetched next time."""
        cache_key = (element_id, result_type, direction, result_set_id)
        self._element_cache.pop(cache_key, None)
        self._category_cache.clear()

    def get_element_maxmin_dataset(
        self, element_id: int, result_set_id: int, base_result_type: str = "WallShears"
    ) -> Optional[MaxMinDataset]:
        """Return absolute max/min dataset for element-specific results (pier shears, quad rotations)."""
        if not self.session or not self.element_repo:
            return None

        # Get element details
        element = self.element_repo.get_by_id(element_id)
        if not element:
            return None

        from database.models import WallShear, QuadRotation, LoadCase, Story

        # Determine which model and attributes to use
        if base_result_type == "WallShears":
            model = WallShear
            max_attr = "max_force"
            min_attr = "min_force"
            direction_attr = "direction"  # V2, V3
        elif base_result_type == "QuadRotations":
            model = QuadRotation
            max_attr = "max_rotation"
            min_attr = "min_rotation"
            direction_attr = None  # No direction for rotations
        else:
            return None

        # Query all wall shear records for this element
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

        self._ensure_stories_loaded()
        story_lookup = {story.id: story for story in self._stories}
        data_by_story: Dict[int, Dict[str, object]] = {}
        story_sort_orders: Dict[int, int] = {}  # Track story_sort_order from result records
        directions_seen: Set[str] = set()

        for record, load_case, story in records:
            story_obj = story_lookup.get(story.id)
            if not story_obj:
                continue

            # Capture story_sort_order from first record for this story
            if story.id not in story_sort_orders:
                story_sort_orders[story.id] = getattr(record, 'story_sort_order', None) or 0

            # Get direction if applicable (WallShears has V2/V3, QuadRotations doesn't)
            if direction_attr:
                direction = getattr(record, direction_attr, "")
                if not direction:
                    continue
                directions_seen.add(direction)
            else:
                # No direction for QuadRotations - use empty string
                direction = ""
                if not directions_seen:
                    directions_seen.add("")

            max_val = getattr(record, max_attr, None)
            min_val = getattr(record, min_attr, None)

            if max_val is None and min_val is None:
                continue

            row = data_by_story.setdefault(story.id, {"Story": story_obj.name})
            load_case_name = load_case.name

            # For QuadRotations, convert radians to percentage (* 100)
            multiplier = 100.0 if base_result_type == "QuadRotations" else 1.0

            if max_val is not None:
                val = abs(max_val) * multiplier
                if direction:
                    row[f"Max_{load_case_name}_{direction}"] = val
                else:
                    row[f"Max_{load_case_name}"] = val
            if min_val is not None:
                val = abs(min_val) * multiplier
                if direction:
                    row[f"Min_{load_case_name}_{direction}"] = val
                else:
                    row[f"Min_{load_case_name}"] = val

        if not data_by_story:
            return None

        # Order rows by story_sort_order from result records to preserve sheet order
        ordered_rows = [
            data_by_story[story_id]
            for story_id in sorted(data_by_story.keys(), key=lambda sid: (story_sort_orders.get(sid, 0), story_lookup.get(sid).name or ""))
        ]

        df = pd.DataFrame(ordered_rows)
        # Don't reverse - preserve sheet order as-is

        result_type_key = f"MaxMin{base_result_type}"

        # Set display name based on result type
        if base_result_type == "WallShears":
            display_name = f"{element.name} - Max/Min Wall Shears"
            default_directions = ("V2", "V3")
        elif base_result_type == "QuadRotations":
            display_name = f"{element.name} - Max/Min Quad Rotations"
            default_directions = ("",)  # No direction for rotations
        else:
            display_name = f"{element.name} - Max/Min {base_result_type}"
            default_directions = ("X", "Y")

        dataset = MaxMinDataset(
            meta=ResultDatasetMeta(
                result_type=result_type_key,
                direction=None,
                result_set_id=result_set_id,
                display_name=display_name,
            ),
            data=df,
            directions=tuple(sorted(directions_seen)) if directions_seen else default_directions,
            source_type=base_result_type,
        )
        return dataset

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
        """Return cache entries preserving sheet-specific ordering.

        The repository already orders by GlobalResultsCache.story_sort_order ascending.
        Since story_sort_order preserves the Excel sheet order exactly (0=first row, N=last row),
        we return entries as-is to maintain the sheet's original order.
        """
        # Repository already ordered by story_sort_order - return as-is to preserve sheet order
        return cache_entries

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

    def _order_element_cache_entries(self, cache_entries):
        """Return element cache entries preserving sheet-specific ordering.

        The repository already orders by ElementResultsCache.story_sort_order ascending.
        Since story_sort_order preserves the Excel sheet order exactly (0=first row, N=last row),
        we return entries as-is to maintain the sheet's original order.
        """
        # Repository already ordered by story_sort_order - return as-is to preserve sheet order
        return cache_entries

    def _build_element_dataframe(self, ordered_entries, result_type: str, direction: str) -> pd.DataFrame:
        """Construct a numeric DataFrame for element-specific results (piers, walls, etc.)."""

        if not ordered_entries:
            return pd.DataFrame()

        story_labels: List[str] = []
        result_dicts: List[dict] = []

        for cache_entry, story in ordered_entries:
            story_labels.append(story.name)
            result_dicts.append(cache_entry.results_matrix or {})

        raw_df = pd.DataFrame(result_dicts)

        # Element results don't use transformer (data is already clean)
        # Just convert to numeric and apply multiplier
        numeric_df = raw_df.apply(pd.to_numeric, errors="coerce")

        # Add summary columns
        numeric_df['Avg'] = numeric_df.mean(axis=1)
        numeric_df['Max'] = numeric_df.max(axis=1)
        numeric_df['Min'] = numeric_df.min(axis=1)

        # Apply multiplier if needed
        if direction:
            transformer_key = f"{result_type}_{direction}"
        else:
            transformer_key = result_type
        config = get_config(transformer_key)

        summary_columns = [col for col in self.SUMMARY_COLUMNS if col in numeric_df.columns]
        value_columns = [
            col for col in numeric_df.columns if col not in summary_columns
        ]

        if config.multiplier != 1.0:
            numeric_df[value_columns] = numeric_df[value_columns] * config.multiplier
            if summary_columns:
                numeric_df[summary_columns] = numeric_df[summary_columns] * config.multiplier

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
        story_sort_orders: Dict[int, int] = {}  # Track from drift records (via StoryDrift)

        for drift in drifts:
            story = story_lookup.get(drift.story_id)
            if not story:
                continue

            row = data_by_story.setdefault(drift.story_id, {"Story": story.name})

            # Note: AbsoluteMaxMinDrift doesn't have story_sort_order, need to query StoryDrift
            # For now, fallback to Story.sort_order (will be fixed when AbsoluteMaxMinDrift is recalculated)
            if drift.story_id not in story_sort_orders:
                story_sort_orders[drift.story_id] = story.sort_order or 0

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

        # Order by story_sort_order from tracked values to preserve sheet order
        ordered_rows = [
            data_by_story[story_id]
            for story_id in sorted(data_by_story.keys(), key=lambda sid: (story_sort_orders.get(sid, 0), story_lookup.get(sid).name or ""))
        ]

        df = pd.DataFrame(ordered_rows)
        # Don't reverse - preserve sheet order as-is

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
        story_sort_orders: Dict[int, int] = {}  # Track story_sort_order from result records
        directions_seen: Set[str] = set()

        for record, load_case, story in records:
            story_obj = story_lookup.get(story.id)
            if not story_obj:
                continue

            # Capture story_sort_order from first record for this story
            if story.id not in story_sort_orders:
                story_sort_orders[story.id] = getattr(record, 'story_sort_order', None) or 0

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

        # Order rows by story_sort_order from result records to preserve sheet order
        ordered_rows = [
            data_by_story[story_id]
            for story_id in sorted(data_by_story.keys(), key=lambda sid: (story_sort_orders.get(sid, 0), story_lookup.get(sid).name or ""))
        ]

        df = pd.DataFrame(ordered_rows)
        # Don't reverse - preserve sheet order as-is

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
