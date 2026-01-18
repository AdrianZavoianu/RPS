from __future__ import annotations

from typing import Dict, Iterable, List, Optional

import pandas as pd

from config.result_config import get_config
from processing.result_transformers import get_transformer

from .metadata import build_display_label
from .models import ResultDataset, ResultDatasetMeta
from .story_loader import StoryProvider

SUMMARY_COLUMNS = ("Avg", "Max", "Min")


def build_standard_dataset(
    project_id: int,
    result_type: str,
    direction: str,
    result_set_id: int,
    cache_entries: Iterable[object],
    story_provider: StoryProvider,
    is_pushover: bool = False,
) -> Optional[ResultDataset]:
    cache_entries = list(cache_entries)
    if not cache_entries:
        return None

    story_provider.ensure_loaded()
    story_lookup = {story.id: story for story in story_provider.stories}
    story_index = story_provider.story_index

    def entry_sort_key(entry):
        sort_order = getattr(entry, "story_sort_order", None)
        if sort_order is None:
            index_tuple = story_index.get(entry.story_id)
            if index_tuple is not None:
                sort_order = index_tuple[0]
            else:
                sort_order = 0
        return sort_order

    ordered_entries = sorted(cache_entries, key=entry_sort_key, reverse=True)

    story_labels: List[str] = []
    result_dicts: List[dict] = []

    for cache_entry in ordered_entries:
        story = story_lookup.get(cache_entry.story_id)
        story_labels.append(story.name if story else f"Story {cache_entry.story_id}")
        result_dicts.append(cache_entry.results_matrix or {})

    raw_df = pd.DataFrame(result_dicts)

    transformer_key = f"{result_type}_{direction}" if direction else result_type
    transformer = get_transformer(transformer_key)
    # Skip summary columns for Pushover analysis
    transformed_df = transformer.transform(raw_df, skip_summary=is_pushover)

    numeric_df = transformed_df.apply(pd.to_numeric, errors="coerce")

    config = get_config(transformer_key)
    value_columns = [
        col for col in numeric_df.columns if col not in SUMMARY_COLUMNS
    ]
    summary_columns = [col for col in SUMMARY_COLUMNS if col in numeric_df.columns]

    if config.multiplier != 1.0:
        numeric_df[value_columns] = numeric_df[value_columns] * config.multiplier
        if summary_columns:
            numeric_df[summary_columns] = numeric_df[summary_columns] * config.multiplier

    numeric_df.insert(0, "Story", story_labels)

    # Sort load case columns lexicographically for consistent display
    load_case_cols = [
        col for col in numeric_df.columns if col not in summary_columns and col != "Story"
    ]
    sorted_load_case_cols = sorted(load_case_cols)

    # Reorder DataFrame columns: Story, sorted load cases, then summary columns
    column_order = ["Story"] + sorted_load_case_cols + summary_columns
    numeric_df = numeric_df[column_order]

    meta = ResultDatasetMeta(
        result_type=result_type,
        direction=direction,
        result_set_id=result_set_id,
        display_name=build_display_label(result_type, direction),
    )

    return ResultDataset(
        meta=meta,
        data=numeric_df,
        config=config,
        load_case_columns=sorted_load_case_cols,
        summary_columns=summary_columns,
    )


def build_element_dataset(
    project_id: int,
    element_id: int,
    result_type: str,
    direction: str,
    result_set_id: int,
    cache_entries: Iterable[object],
    story_provider: StoryProvider,
    is_pushover: bool = False,
) -> Optional[ResultDataset]:
    cache_entries = list(cache_entries)
    if not cache_entries:
        return None

    story_provider.ensure_loaded()
    story_lookup = {story.id: story for story in story_provider.stories}
    story_index = story_provider.story_index

    def entry_sort_key(entry):
        sort_order = getattr(entry, "story_sort_order", None)
        if sort_order is None:
            index_tuple = story_index.get(entry.story_id)
            if index_tuple is not None:
                sort_order = index_tuple[0]
            else:
                sort_order = 0
        return sort_order

    ordered_entries = sorted(cache_entries, key=entry_sort_key, reverse=True)

    story_labels: List[str] = []
    result_dicts: List[dict] = []

    for cache_entry in ordered_entries:
        story = story_lookup.get(cache_entry.story_id)
        story_labels.append(story.name if story else f"Story {cache_entry.story_id}")
        result_dicts.append(cache_entry.results_matrix or {})

    raw_df = pd.DataFrame(result_dicts)
    numeric_df = raw_df.apply(pd.to_numeric, errors="coerce")

    # Add summary columns only for NLTHA, not Pushover
    summary_columns: List[str] = []
    if not is_pushover:
        numeric_df["Avg"] = numeric_df.mean(axis=1)
        numeric_df["Max"] = numeric_df.max(axis=1)
        numeric_df["Min"] = numeric_df.min(axis=1)
        summary_columns = [col for col in SUMMARY_COLUMNS if col in numeric_df.columns]

    transformer_key = f"{result_type}_{direction}" if direction else result_type
    config = get_config(transformer_key)

    value_columns = [col for col in numeric_df.columns if col not in summary_columns]

    if config.multiplier != 1.0:
        numeric_df[value_columns] = numeric_df[value_columns] * config.multiplier
        if summary_columns:
            numeric_df[summary_columns] = numeric_df[summary_columns] * config.multiplier

    numeric_df.insert(0, "Story", story_labels)

    # Sort load case columns lexicographically for consistent display
    load_case_cols = [
        col for col in numeric_df.columns if col not in summary_columns and col != "Story"
    ]
    sorted_load_case_cols = sorted(load_case_cols)

    # Reorder DataFrame columns: Story, sorted load cases, then summary columns
    column_order = ["Story"] + sorted_load_case_cols + summary_columns
    numeric_df = numeric_df[column_order]

    meta = ResultDatasetMeta(
        result_type=result_type,
        direction=direction,
        result_set_id=result_set_id,
        display_name=build_display_label(result_type, direction),
    )

    return ResultDataset(
        meta=meta,
        data=numeric_df,
        config=config,
        load_case_columns=sorted_load_case_cols,
        summary_columns=summary_columns,
    )
