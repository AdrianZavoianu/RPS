from __future__ import annotations

from typing import Dict, Optional, Set

import pandas as pd

from .metadata import build_display_label
from .models import MaxMinDataset, ResultDatasetMeta
from .story_loader import StoryProvider


def build_drift_maxmin_dataset(
    project_id: int,
    result_set_id: int,
    abs_maxmin_repo,
    story_provider: StoryProvider,
    load_case_repo=None,
) -> Optional[MaxMinDataset]:
    drifts = abs_maxmin_repo.get_by_result_set(
        project_id=project_id,
        result_set_id=result_set_id,
    )

    if not drifts:
        return None

    story_provider.ensure_loaded()
    story_lookup = {story.id: story for story in story_provider.stories}
    load_case_cache: Dict[int, object] = {}

    data_by_story: Dict[int, Dict[str, object]] = {}
    story_sort_orders: Dict[int, int] = {}
    directions_seen: Set[str] = set()

    for drift in drifts:
        story = story_lookup.get(drift.story_id)
        if not story:
            continue

        row = data_by_story.setdefault(drift.story_id, {"Story": story.name})

        if drift.story_id not in story_sort_orders:
            story_sort_orders[drift.story_id] = story.sort_order or 0

        if load_case_repo and drift.load_case_id not in load_case_cache:
            load_case_cache[drift.load_case_id] = load_case_repo.get_by_id(drift.load_case_id)

        load_case = load_case_cache.get(drift.load_case_id) if load_case_cache else None
        load_case_name = getattr(load_case, "name", f"LC{drift.load_case_id}")

        direction = _normalize_direction(drift.direction)
        if direction is None:
            continue
        directions_seen.add(direction)

        row[f"Max_{load_case_name}_{direction}"] = drift.original_max * 100.0
        row[f"Min_{load_case_name}_{direction}"] = drift.original_min * 100.0

    if not data_by_story:
        return None

    ordered_rows = [
        data_by_story[story_id]
        for story_id in sorted(
            data_by_story.keys(),
            key=lambda sid: (story_sort_orders.get(sid, 0), story_lookup.get(sid).name or ""),
        )
    ]

    df = pd.DataFrame(ordered_rows)

    meta = ResultDatasetMeta(
        result_type="MaxMinDrifts",
        direction=None,
        result_set_id=result_set_id,
        display_name=build_display_label("MaxMinDrifts", None),
    )

    return MaxMinDataset(
        meta=meta,
        data=df,
        directions=tuple(sorted(directions_seen)) or ("X", "Y"),
        source_type="Drifts",
    )


def build_generic_maxmin_dataset(
    project_id: int,
    result_set_id: int,
    base_result_type: str,
    session,
    category_id_provider,
    story_provider: StoryProvider,
) -> Optional[MaxMinDataset]:
    category_id = category_id_provider(result_set_id)
    if not category_id:
        return None

    from database.models import (
        StoryAcceleration,
        StoryForce,
        StoryDisplacement,
        LoadCase,
        Story,
    )

    model_map = {
        "Accelerations": (StoryAcceleration, "max_acceleration", "min_acceleration"),
        "Forces": (StoryForce, "max_force", "min_force"),
        "Displacements": (StoryDisplacement, "max_displacement", "min_displacement"),
    }

    model_tuple = model_map.get(base_result_type)
    if not model_tuple:
        return None

    model, max_attr, min_attr = model_tuple

    records = (
        session.query(model, LoadCase, Story)
        .join(LoadCase, model.load_case_id == LoadCase.id)
        .join(Story, model.story_id == Story.id)
        .filter(
            Story.project_id == project_id,
            model.result_category_id == category_id,
        )
        .all()
    )

    if not records:
        return None

    story_provider.ensure_loaded()
    story_lookup = {story.id: story for story in story_provider.stories}

    story_data: Dict[int, Dict[str, object]] = {}
    story_order: Dict[int, int] = {}
    directions_seen: Set[str] = set()

    for record, load_case, story in records:
        lookup_story = story_lookup.get(story.id)
        if not lookup_story:
            continue

        story_order[story.id] = getattr(record, "story_sort_order", lookup_story.sort_order or 0)
        direction = _normalize_direction(getattr(record, "direction", ""))
        if direction is None:
            continue

        directions_seen.add(direction)

        max_value = getattr(record, max_attr)
        min_value = getattr(record, min_attr)
        if max_value is None and min_value is None:
            continue

        story_entry = story_data.setdefault(story.id, {"Story": lookup_story.name})
        load_case_name = load_case.name

        if max_value is not None:
            story_entry[f"Max_{load_case_name}_{direction}"] = abs(max_value)
        if min_value is not None:
            story_entry[f"Min_{load_case_name}_{direction}"] = abs(min_value)

    if not story_data:
        return None

    ordered_rows = [
        story_data[story_id]
        for story_id in sorted(
            story_data.keys(),
            key=lambda sid: (story_order.get(sid, 0), story_lookup.get(sid).name or ""),
        )
    ]

    df = pd.DataFrame(ordered_rows)

    meta = ResultDatasetMeta(
        result_type=f"MaxMin{base_result_type}",
        direction=None,
        result_set_id=result_set_id,
        display_name=build_display_label(f"MaxMin{base_result_type}", None),
    )

    return MaxMinDataset(
        meta=meta,
        data=df,
        directions=tuple(sorted(directions_seen)) or ("X", "Y"),
        source_type=base_result_type,
    )


def _normalize_direction(direction: Optional[str]) -> Optional[str]:
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
