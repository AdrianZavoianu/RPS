from __future__ import annotations

from collections import OrderedDict
from enum import Enum
from typing import Dict, List, Optional, Tuple, TypeVar
import os
import logging

import pandas as pd

from config.result_config import get_config
from .cache_builder import build_element_dataset, build_standard_dataset
from .metadata import build_display_label
from .models import ResultDataset, ResultDatasetMeta
from .story_loader import StoryProvider

CACHE_DEBUG = os.getenv("RPS_CACHE_DEBUG", "").lower() in {"1", "true", "yes"}
logger = logging.getLogger(__name__)

# Default max cache size per provider (configurable via environment)
DEFAULT_MAX_CACHE_SIZE = int(os.getenv("RPS_MAX_CACHE_SIZE", "100"))

K = TypeVar("K")
V = TypeVar("V")


class LRUCache(OrderedDict[K, V]):
    """Simple LRU cache with configurable max size."""

    def __init__(self, max_size: int = DEFAULT_MAX_CACHE_SIZE) -> None:
        super().__init__()
        self.max_size = max_size

    def get_item(self, key: K) -> Optional[V]:
        """Get item and move to end (most recently used)."""
        if key not in self:
            return None
        self.move_to_end(key)
        return self[key]

    def set_item(self, key: K, value: V) -> None:
        """Set item and evict oldest if over capacity."""
        if key in self:
            self.move_to_end(key)
        self[key] = value
        while len(self) > self.max_size:
            oldest_key = next(iter(self))
            if CACHE_DEBUG:
                logger.debug("cache_evict", extra={"key": str(oldest_key)})
            del self[oldest_key]


class ResultCategory(str, Enum):
    """Logical grouping for result datasets."""

    GLOBAL = "global"
    ELEMENT = "element"
    JOINT = "joint"


class StandardDatasetProvider:
    """Builds cached datasets for story-based (global) results."""

    def __init__(self, project_id: int, cache_repo, story_provider: StoryProvider, max_cache_size: int = DEFAULT_MAX_CACHE_SIZE) -> None:
        self.project_id = project_id
        self.cache_repo = cache_repo
        self.story_provider = story_provider
        self._cache: LRUCache[Tuple[str, str, int, bool], Optional[ResultDataset]] = LRUCache(max_cache_size)

    def get(self, result_type: str, direction: str, result_set_id: int, is_pushover: bool = False) -> Optional[ResultDataset]:
        cache_key = (result_type, direction, result_set_id, is_pushover)
        if cache_key in self._cache:
            if CACHE_DEBUG:
                logger.debug("cache_hit.standard", extra={"result_type": result_type, "direction": direction, "result_set_id": result_set_id})
            return self._cache.get_item(cache_key)

        cache_entries = self.cache_repo.get_cache_for_display(
            project_id=self.project_id,
            result_type=result_type,
            result_set_id=result_set_id,
        )

        if not cache_entries:
            if CACHE_DEBUG:
                logger.debug("cache_miss.standard", extra={"result_type": result_type, "direction": direction, "result_set_id": result_set_id})
            self._cache[cache_key] = None
            return None

        dataset = build_standard_dataset(
            project_id=self.project_id,
            result_type=result_type,
            direction=direction,
            result_set_id=result_set_id,
            cache_entries=cache_entries,
            story_provider=self.story_provider,
            is_pushover=is_pushover,
        )

        if CACHE_DEBUG:
            logger.debug("cache_store.standard", extra={"result_type": result_type, "direction": direction, "result_set_id": result_set_id})
        self._cache.set_item(cache_key, dataset)
        return dataset

    def invalidate(self, result_type: str, direction: str, result_set_id: int) -> None:
        # Remove both pushover and non-pushover versions from cache
        for is_pushover in [True, False]:
            cache_key = (result_type, direction, result_set_id, is_pushover)
            self._cache.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()

    def clear_for_result_set(self, result_set_id: int) -> None:
        """Remove cached datasets belonging to a specific result set."""
        # Cache key is (result_type, direction, result_set_id, is_pushover), so result_set_id is at index 2
        keys_to_delete = [k for k in list(self._cache.keys()) if k[2] == result_set_id]
        for key in keys_to_delete:
            self._cache.pop(key, None)


class ElementDatasetProvider:
    """Builds cached datasets for element-based results."""

    def __init__(self, project_id: int, element_cache_repo, story_provider: StoryProvider, max_cache_size: int = DEFAULT_MAX_CACHE_SIZE) -> None:
        self.project_id = project_id
        self.element_cache_repo = element_cache_repo
        self.story_provider = story_provider
        self._cache: LRUCache[Tuple[int, str, str, int, bool], Optional[ResultDataset]] = LRUCache(max_cache_size)

    def get(
        self,
        element_id: int,
        result_type: str,
        direction: str,
        result_set_id: int,
        is_pushover: bool = False,
    ) -> Optional[ResultDataset]:
        if not self.element_cache_repo:
            return None

        cache_key = (element_id, result_type, direction, result_set_id, is_pushover)
        if cache_key in self._cache:
            if CACHE_DEBUG:
                logger.debug("cache_hit.element", extra={"result_type": result_type, "direction": direction, "result_set_id": result_set_id, "element_id": element_id})
            return self._cache.get_item(cache_key)

        # Resolve cache key (element cache stores more specific result_type names)
        fallback_types = [f"{result_type}_{direction}" if direction else result_type]
        if not direction:
            if result_type == "BeamRotations":
                fallback_types.append("BeamRotations_R3Plastic")
            elif result_type == "ColumnRotations":
                # Prefer R3 if not explicitly requested
                fallback_types.extend(["ColumnRotations_R3", "ColumnRotations_R2"])
            elif result_type == "ColumnAxials":
                fallback_types.extend(["ColumnAxials_Min", "ColumnAxials_Max"])

        cache_entries = None
        chosen_direction = direction
        for rt in fallback_types:
            cache_entries = self.element_cache_repo.get_cache_for_display(
                project_id=self.project_id,
                element_id=element_id,
                result_type=rt,
                result_set_id=result_set_id,
            )
            if cache_entries:
                if not direction:
                    # Derive a direction label from the resolved cache type (after first underscore)
                    parts = rt.split("_", 1)
                    if len(parts) > 1:
                        chosen_direction = parts[1]
                full_result_type = rt
                break

        if not cache_entries:
            if CACHE_DEBUG:
                logger.debug("cache_miss.element", extra={"result_type": result_type, "direction": direction, "result_set_id": result_set_id, "element_id": element_id})
            self._cache[cache_key] = None
            return None

        dataset = build_element_dataset(
            project_id=self.project_id,
            element_id=element_id,
            result_type=result_type,
            direction=chosen_direction,
            result_set_id=result_set_id,
            cache_entries=cache_entries,
            story_provider=self.story_provider,
            is_pushover=is_pushover,
        )

        if CACHE_DEBUG:
            logger.debug("cache_store.element", extra={"result_type": result_type, "direction": direction, "result_set_id": result_set_id, "element_id": element_id})
        self._cache.set_item(cache_key, dataset)
        return dataset

    def invalidate(self, element_id: int, result_type: str, direction: str, result_set_id: int) -> None:
        # Remove both pushover and non-pushover versions from cache
        for is_pushover in [True, False]:
            cache_key = (element_id, result_type, direction, result_set_id, is_pushover)
            self._cache.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()

    def clear_for_result_set(self, result_set_id: int) -> None:
        """Remove cached datasets belonging to a specific result set."""
        # Cache key is (element_id, result_type, direction, result_set_id, is_pushover), so result_set_id is at index 3
        keys_to_delete = [k for k in list(self._cache.keys()) if k[3] == result_set_id]
        for key in keys_to_delete:
            self._cache.pop(key, None)


class JointDatasetProvider:
    """Builds cached datasets for joint/foundation results."""

    def __init__(self, project_id: int, joint_cache_repo, max_cache_size: int = DEFAULT_MAX_CACHE_SIZE) -> None:
        self.project_id = project_id
        self.joint_cache_repo = joint_cache_repo
        self._cache: LRUCache[Tuple[str, int, bool], Optional[ResultDataset]] = LRUCache(max_cache_size)

    def get(self, result_type: str, result_set_id: int, is_pushover: bool = False) -> Optional[ResultDataset]:
        if not self.joint_cache_repo:
            return None

        cache_key = (result_type, result_set_id, is_pushover)
        if cache_key in self._cache:
            if CACHE_DEBUG:
                logger.debug("cache_hit.joint", extra={"result_type": result_type, "result_set_id": result_set_id})
            return self._cache.get_item(cache_key)

        cache_entries = self.joint_cache_repo.get_all_for_type(
            project_id=self.project_id,
            result_set_id=result_set_id,
            result_type=result_type,
        )

        if not cache_entries:
            if CACHE_DEBUG:
                logger.debug("cache_miss.joint", extra={"result_type": result_type, "result_set_id": result_set_id})
            self._cache[cache_key] = None
            return None

        config = get_config(result_type)
        rows: List[Dict[str, object]] = []

        for entry in cache_entries:
            row_data = {
                "Shell Object": entry.shell_object,
                "Unique Name": entry.unique_name,
            }
            row_data.update(entry.results_matrix)
            rows.append(row_data)

        df = pd.DataFrame(rows)

        if not df.empty:
            df = df.sort_values(["Shell Object", "Unique Name"]).reset_index(drop=True)

        non_data_cols = ["Shell Object", "Unique Name"]
        load_case_columns = [col for col in df.columns if col not in non_data_cols]

        # Add summary columns only for NLTHA, not Pushover
        summary_columns: List[str] = []
        if load_case_columns and not df.empty and not is_pushover:
            df["Average"] = df[load_case_columns].mean(axis=1)
            df["Maximum"] = df[load_case_columns].max(axis=1)
            df["Minimum"] = df[load_case_columns].min(axis=1)
            summary_columns.extend(["Average", "Maximum", "Minimum"])

        meta = ResultDatasetMeta(
            result_type=result_type,
            direction="",
            result_set_id=result_set_id,
            display_name=build_display_label(result_type, ""),
        )

        dataset = ResultDataset(
            meta=meta,
            data=df,
            config=config,
            load_case_columns=load_case_columns,
            summary_columns=summary_columns,
        )

        if CACHE_DEBUG:
            logger.debug("cache_store.joint", extra={"result_type": result_type, "result_set_id": result_set_id})
        self._cache.set_item(cache_key, dataset)
        return dataset

    def invalidate(self, result_type: str, result_set_id: int) -> None:
        # Remove both pushover and non-pushover versions from cache
        for is_pushover in [True, False]:
            cache_key = (result_type, result_set_id, is_pushover)
            self._cache.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()

    def clear_for_result_set(self, result_set_id: int) -> None:
        """Remove cached datasets belonging to a specific result set."""
        # Cache key is (result_type, result_set_id, is_pushover), so result_set_id is at index 1
        keys_to_delete = [k for k in list(self._cache.keys()) if k[1] == result_set_id]
        for key in keys_to_delete:
            self._cache.pop(key, None)
