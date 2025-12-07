"""Tests for result cache invalidation helpers."""

from processing.result_service.providers import ResultCategory
from processing.result_service.service import ResultDataService


class _FakeProvider:
    def __init__(self):
        self._cache = {}

    def clear(self):
        self._cache.clear()

    def clear_for_result_set(self, result_set_id: int):
        to_delete = [k for k in self._cache if k[-1] == result_set_id]
        for key in to_delete:
            self._cache.pop(key, None)


def test_invalidate_result_set_clears_targeted_caches():
    # Build service with fake providers to isolate invalidation behavior
    service = ResultDataService(
        project_id=1,
        cache_repo=None,
        story_repo=None,
        load_case_repo=None,
    )

    fake_global = _FakeProvider()
    fake_element = _FakeProvider()
    fake_joint = _FakeProvider()

    fake_global._cache = {("Drifts", "X", 10): "keep", ("Drifts", "X", 1): "drop"}
    fake_element._cache = {(5, "WallShears", "V2", 1): "drop", (6, "WallShears", "V2", 99): "keep"}
    fake_joint._cache = {("SoilPressures_Min", 1): "drop", ("SoilPressures_Min", 99): "keep"}

    service._dataset_providers = {
        ResultCategory.GLOBAL: fake_global,
        ResultCategory.ELEMENT: fake_element,
        ResultCategory.JOINT: fake_joint,
    }

    service._maxmin_cache = {("Drifts", 1): "drop", ("Drifts", 3): "keep"}
    service._comparison_cache = {("Drifts", (1, 2)): "drop", ("Drifts", (3, 4)): "keep"}
    service._category_cache = {1: "drop", 5: "keep"}

    service.invalidate_result_set(1)

    assert ("Drifts", "X", 1) not in fake_global._cache
    assert ("Drifts", "X", 10) in fake_global._cache

    assert (5, "WallShears", "V2", 1) not in fake_element._cache
    assert (6, "WallShears", "V2", 99) in fake_element._cache

    assert ("SoilPressures_Min", 1) not in fake_joint._cache
    assert ("SoilPressures_Min", 99) in fake_joint._cache

    assert ("Drifts", 1) not in service._maxmin_cache
    assert ("Drifts", 3) in service._maxmin_cache

    assert ("Drifts", (1, 2)) not in service._comparison_cache
    assert ("Drifts", (3, 4)) in service._comparison_cache

    assert 1 not in service._category_cache
    assert 5 in service._category_cache
