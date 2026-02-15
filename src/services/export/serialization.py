"""Serialization helpers for export/import metadata payloads."""

from __future__ import annotations

from typing import Any, List


def serialize_story_drifts(session) -> list[dict[str, Any]]:
    from database.models import StoryDrift, Story, LoadCase

    results = (
        session.query(
            Story.name.label("story_name"),
            LoadCase.name.label("load_case_name"),
            StoryDrift.direction,
            StoryDrift.drift,
            StoryDrift.max_drift,
            StoryDrift.min_drift,
            StoryDrift.story_sort_order,
        )
        .join(Story, StoryDrift.story_id == Story.id)
        .join(LoadCase, StoryDrift.load_case_id == LoadCase.id)
        .all()
    )

    return [
        {
            "story_name": r.story_name,
            "load_case_name": r.load_case_name,
            "direction": r.direction,
            "drift": r.drift,
            "max_drift": r.max_drift,
            "min_drift": r.min_drift,
            "story_sort_order": r.story_sort_order,
        }
        for r in results
    ]


def serialize_story_accelerations(session) -> list[dict[str, Any]]:
    from database.models import StoryAcceleration, Story, LoadCase, ResultCategory, ResultSet

    results = (
        session.query(
            Story.name.label("story_name"),
            LoadCase.name.label("load_case_name"),
            ResultSet.name.label("result_set_name"),
            ResultCategory.category_name.label("result_category_name"),
            StoryAcceleration.direction,
            StoryAcceleration.acceleration,
            StoryAcceleration.max_acceleration,
            StoryAcceleration.min_acceleration,
            StoryAcceleration.story_sort_order,
        )
        .join(Story, StoryAcceleration.story_id == Story.id)
        .join(LoadCase, StoryAcceleration.load_case_id == LoadCase.id)
        .join(ResultCategory, StoryAcceleration.result_category_id == ResultCategory.id)
        .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
        .all()
    )

    return [
        {
            "story_name": r.story_name,
            "load_case_name": r.load_case_name,
            "result_set_name": r.result_set_name,
            "result_category_name": r.result_category_name,
            "direction": r.direction,
            "acceleration": r.acceleration,
            "max_acceleration": r.max_acceleration,
            "min_acceleration": r.min_acceleration,
            "story_sort_order": r.story_sort_order,
        }
        for r in results
    ]


def serialize_story_forces(session) -> list[dict[str, Any]]:
    from database.models import StoryForce, Story, LoadCase, ResultCategory, ResultSet

    results = (
        session.query(
            Story.name.label("story_name"),
            LoadCase.name.label("load_case_name"),
            ResultSet.name.label("result_set_name"),
            ResultCategory.category_name.label("result_category_name"),
            StoryForce.direction,
            StoryForce.location,
            StoryForce.force,
            StoryForce.max_force,
            StoryForce.min_force,
            StoryForce.story_sort_order,
        )
        .join(Story, StoryForce.story_id == Story.id)
        .join(LoadCase, StoryForce.load_case_id == LoadCase.id)
        .join(ResultCategory, StoryForce.result_category_id == ResultCategory.id)
        .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
        .all()
    )

    return [
        {
            "story_name": r.story_name,
            "load_case_name": r.load_case_name,
            "result_set_name": r.result_set_name,
            "result_category_name": r.result_category_name,
            "direction": r.direction,
            "location": r.location,
            "force": r.force,
            "max_force": r.max_force,
            "min_force": r.min_force,
            "story_sort_order": r.story_sort_order,
        }
        for r in results
    ]


def serialize_story_displacements(session) -> list[dict[str, Any]]:
    from database.models import StoryDisplacement, Story, LoadCase, ResultCategory, ResultSet

    results = (
        session.query(
            Story.name.label("story_name"),
            LoadCase.name.label("load_case_name"),
            ResultSet.name.label("result_set_name"),
            ResultCategory.category_name.label("result_category_name"),
            StoryDisplacement.direction,
            StoryDisplacement.displacement,
            StoryDisplacement.max_displacement,
            StoryDisplacement.min_displacement,
            StoryDisplacement.story_sort_order,
        )
        .join(Story, StoryDisplacement.story_id == Story.id)
        .join(LoadCase, StoryDisplacement.load_case_id == LoadCase.id)
        .join(ResultCategory, StoryDisplacement.result_category_id == ResultCategory.id)
        .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
        .all()
    )

    return [
        {
            "story_name": r.story_name,
            "load_case_name": r.load_case_name,
            "result_set_name": r.result_set_name,
            "result_category_name": r.result_category_name,
            "direction": r.direction,
            "displacement": r.displacement,
            "max_displacement": r.max_displacement,
            "min_displacement": r.min_displacement,
            "story_sort_order": r.story_sort_order,
        }
        for r in results
    ]


def serialize_absolute_maxmin_drifts(session) -> list[dict[str, Any]]:
    from database.models import AbsoluteMaxMinDrift, Story, LoadCase, ResultSet

    results = (
        session.query(
            Story.name.label("story_name"),
            LoadCase.name.label("load_case_name"),
            ResultSet.name.label("result_set_name"),
            AbsoluteMaxMinDrift.direction,
            AbsoluteMaxMinDrift.absolute_max_drift,
            AbsoluteMaxMinDrift.sign,
            AbsoluteMaxMinDrift.original_max,
            AbsoluteMaxMinDrift.original_min,
        )
        .join(Story, AbsoluteMaxMinDrift.story_id == Story.id)
        .join(LoadCase, AbsoluteMaxMinDrift.load_case_id == LoadCase.id)
        .join(ResultSet, AbsoluteMaxMinDrift.result_set_id == ResultSet.id)
        .all()
    )

    return [
        {
            "story_name": r.story_name,
            "load_case_name": r.load_case_name,
            "result_set_name": r.result_set_name,
            "direction": r.direction,
            "absolute_max_drift": r.absolute_max_drift,
            "sign": r.sign,
            "original_max": r.original_max,
            "original_min": r.original_min,
        }
        for r in results
    ]


def serialize_quad_rotations(session) -> list[dict[str, Any]]:
    from database.models import QuadRotation, Story, LoadCase, ResultCategory, ResultSet, Element

    results = (
        session.query(
            Story.name.label("story_name"),
            LoadCase.name.label("load_case_name"),
            ResultSet.name.label("result_set_name"),
            ResultCategory.category_name.label("result_category_name"),
            Element.name.label("element_name"),
            QuadRotation.direction,
            QuadRotation.rotation,
            QuadRotation.max_rotation,
            QuadRotation.min_rotation,
            QuadRotation.story_sort_order,
        )
        .join(Element, QuadRotation.element_id == Element.id)
        .join(Story, QuadRotation.story_id == Story.id)
        .join(LoadCase, QuadRotation.load_case_id == LoadCase.id)
        .join(ResultCategory, QuadRotation.result_category_id == ResultCategory.id)
        .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
        .all()
    )

    return [
        {
            "story_name": r.story_name,
            "load_case_name": r.load_case_name,
            "result_set_name": r.result_set_name,
            "result_category_name": r.result_category_name,
            "element_name": r.element_name,
            "direction": r.direction,
            "rotation": r.rotation,
            "max_rotation": r.max_rotation,
            "min_rotation": r.min_rotation,
            "story_sort_order": r.story_sort_order,
        }
        for r in results
    ]


def serialize_wall_shears(session) -> list[dict[str, Any]]:
    from database.models import WallShear, Story, LoadCase, ResultCategory, ResultSet, Element

    results = (
        session.query(
            Story.name.label("story_name"),
            LoadCase.name.label("load_case_name"),
            ResultSet.name.label("result_set_name"),
            ResultCategory.category_name.label("result_category_name"),
            Element.name.label("element_name"),
            WallShear.direction,
            WallShear.location,
            WallShear.force,
            WallShear.max_force,
            WallShear.min_force,
            WallShear.story_sort_order,
        )
        .join(Element, WallShear.element_id == Element.id)
        .join(Story, WallShear.story_id == Story.id)
        .join(LoadCase, WallShear.load_case_id == LoadCase.id)
        .join(ResultCategory, WallShear.result_category_id == ResultCategory.id)
        .join(ResultSet, ResultCategory.result_set_id == ResultSet.id)
        .all()
    )

    return [
        {
            "story_name": r.story_name,
            "load_case_name": r.load_case_name,
            "result_set_name": r.result_set_name,
            "result_category_name": r.result_category_name,
            "element_name": r.element_name,
            "direction": r.direction,
            "location": r.location,
            "force": r.force,
            "max_force": r.max_force,
            "min_force": r.min_force,
            "story_sort_order": r.story_sort_order,
        }
        for r in results
    ]


def serialize_global_cache(session) -> list[dict[str, Any]]:
    from database.models import GlobalResultsCache, ResultSet, Story

    entries = (
        session.query(
            GlobalResultsCache,
            ResultSet.name.label("result_set_name"),
            Story.name.label("story_name"),
        )
        .join(ResultSet, GlobalResultsCache.result_set_id == ResultSet.id)
        .join(Story, GlobalResultsCache.story_id == Story.id)
        .all()
    )

    return [
        {
            "result_set_name": result_set_name,
            "story_name": story_name,
            "result_type": cache_entry.result_type,
            "story_sort_order": cache_entry.story_sort_order,
            "results_matrix": cache_entry.results_matrix,
        }
        for cache_entry, result_set_name, story_name in entries
    ]


def serialize_element_cache(session) -> list[dict[str, Any]]:
    from database.models import ElementResultsCache, ResultSet, Story, Element

    entries = (
        session.query(
            ElementResultsCache,
            ResultSet.name.label("result_set_name"),
            Story.name.label("story_name"),
            Element.name.label("element_name"),
        )
        .join(ResultSet, ElementResultsCache.result_set_id == ResultSet.id)
        .join(Story, ElementResultsCache.story_id == Story.id)
        .join(Element, ElementResultsCache.element_id == Element.id)
        .all()
    )

    return [
        {
            "result_set_name": result_set_name,
            "story_name": story_name,
            "element_name": element_name,
            "result_type": cache_entry.result_type,
            "story_sort_order": cache_entry.story_sort_order,
            "results_matrix": cache_entry.results_matrix,
        }
        for cache_entry, result_set_name, story_name, element_name in entries
    ]

