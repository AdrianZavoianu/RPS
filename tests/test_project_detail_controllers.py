"""Tests for project detail controllers and mapping behavior."""

from gui.controllers.project_detail_controller import ProjectDetailController
from gui.controllers.result_view_controller import ResultViewController


class _FakeCacheRepo:
    def __init__(self, load_cases):
        self._load_cases = load_cases
        self.calls = 0

    def get_distinct_load_cases(self, project_id, result_set_id):
        self.calls += 1
        return list(self._load_cases)


def test_project_detail_controller_caches_pushover_mapping():
    fake_repo = _FakeCacheRepo(
        [
            "Push-Mod-X+Ecc+_UX",
            "Push-Mod-X+Ecc+_UY",
            "Push_Mod_Y+Ecc-_UY",
        ]
    )
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    mapping_first = controller.get_pushover_mapping(result_set_id=10)

    # Mapping should include both hyphen and underscore variants
    assert mapping_first["Push-Mod-X+Ecc+"] == "Px1"
    assert mapping_first["Push_Mod_Y+Ecc-"] == "Py1"
    # Cache repo called once
    assert fake_repo.calls == 1

    # Second call should use cached mapping without hitting repo
    mapping_second = controller.get_pushover_mapping(result_set_id=10)
    assert mapping_second == mapping_first
    assert fake_repo.calls == 1


def test_result_view_controller_only_maps_headers_in_pushover_context():
    fake_repo = _FakeCacheRepo(["Push-Mod-X+Ecc+_UX"])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)
    controller._pushover_mappings[5] = {"Push-Mod-X+Ecc+": "Px1"}
    view_controller = ResultViewController(project_id=1, cache_repo=fake_repo, controller=controller)

    headers = ["Story", "Push-Mod-X+Ecc+"]

    controller.set_active_context("NLTHA")
    assert view_controller.apply_mapping_to_headers(headers, result_set_id=5) == headers

    controller.set_active_context("Pushover")
    mapped_headers = view_controller.apply_mapping_to_headers(headers, result_set_id=5)
    assert mapped_headers == ["Story", "Px1"]
