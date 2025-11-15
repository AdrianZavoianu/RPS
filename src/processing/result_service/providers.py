from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Tuple

import pandas as pd

from config.result_config import get_config
from .cache_builder import build_element_dataset, build_standard_dataset
from .metadata import build_display_label
from .models import ResultDataset, ResultDatasetMeta
from .story_loader import StoryProvider


class ResultCategory(str, Enum):
    """Logical grouping for result datasets."""

    GLOBAL = "global"
    ELEMENT = "element"
    JOINT = "joint"


class StandardDatasetProvider:
    """Builds cached datasets for story-based (global) results."""

    def __init__(self, project_id: int, cache_repo, story_provider: StoryProvider) -> None:
        self.project_id = project_id
        self.cache_repo = cache_repo
        self.story_provider = story_provider
        self._cache: Dict[Tuple[str, str, int], Optional[ResultDataset]] = {}

    def get(self, result_type: str, direction: str, result_set_id: int) -> Optional[ResultDataset]:
        cache_key = (result_type, direction, result_set_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        cache_entries = self.cache_repo.get_cache_for_display(
            project_id=self.project_id,
            result_type=result_type,
            result_set_id=result_set_id,
        )

        if not cache_entries:
            self._cache[cache_key] = None
            return None

        dataset = build_standard_dataset(
            project_id=self.project_id,
            result_type=result_type,
            direction=direction,
            result_set_id=result_set_id,
            cache_entries=cache_entries,
            story_provider=self.story_provider,
        )

        self._cache[cache_key] = dataset
        return dataset

    def invalidate(self, result_type: str, direction: str, result_set_id: int) -> None:
        cache_key = (result_type, direction, result_set_id)
        self._cache.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()


class ElementDatasetProvider:
    """Builds cached datasets for element-based results."""

    def __init__(self, project_id: int, element_cache_repo, story_provider: StoryProvider) -> None:
        self.project_id = project_id
        self.element_cache_repo = element_cache_repo
        self.story_provider = story_provider
        self._cache: Dict[Tuple[int, str, str, int], Optional[ResultDataset]] = {}

    def get(
        self,
        element_id: int,
        result_type: str,
        direction: str,
        result_set_id: int,
    ) -> Optional[ResultDataset]:
        if not self.element_cache_repo:
            return None

        cache_key = (element_id, result_type, direction, result_set_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        full_result_type = f"{result_type}_{direction}" if direction else result_type
        cache_entries = self.element_cache_repo.get_cache_for_display(
            project_id=self.project_id,
            element_id=element_id,
            result_type=full_result_type,
            result_set_id=result_set_id,
        )

        if not cache_entries:
            self._cache[cache_key] = None
            return None

        dataset = build_element_dataset(
            project_id=self.project_id,
            element_id=element_id,
            result_type=result_type,
            direction=direction,
            result_set_id=result_set_id,
            cache_entries=cache_entries,
            story_provider=self.story_provider,
        )

        self._cache[cache_key] = dataset
        return dataset

    def invalidate(self, element_id: int, result_type: str, direction: str, result_set_id: int) -> None:
        cache_key = (element_id, result_type, direction, result_set_id)
        self._cache.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()


class JointDatasetProvider:
    """Builds cached datasets for joint/foundation results."""

    def __init__(self, project_id: int, joint_cache_repo) -> None:
        self.project_id = project_id
        self.joint_cache_repo = joint_cache_repo
        self._cache: Dict[Tuple[str, int], Optional[ResultDataset]] = {}

    def get(self, result_type: str, result_set_id: int) -> Optional[ResultDataset]:
        if not self.joint_cache_repo:
            return None

        cache_key = (result_type, result_set_id)
        if cache_key in self._cache:
            return self._cache[cache_key]

        cache_entries = self.joint_cache_repo.get_all_for_type(
            project_id=self.project_id,
            result_set_id=result_set_id,
            result_type=result_type,
        )

        if not cache_entries:
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

        summary_columns: List[str] = []
        if load_case_columns and not df.empty:
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

        self._cache[cache_key] = dataset
        return dataset

    def invalidate(self, result_type: str, result_set_id: int) -> None:
        cache_key = (result_type, result_set_id)
        self._cache.pop(cache_key, None)

    def clear(self) -> None:
        self._cache.clear()
