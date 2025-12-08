"""Tests for project detail controllers and mapping behavior."""

from config.analysis_types import AnalysisType
from gui.controllers.project_detail_controller import ProjectDetailController, SelectionState
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


# ---- SelectionState Tests ----


def test_selection_state_defaults():
    """Test that SelectionState has correct default values."""
    state = SelectionState()

    assert state.result_type is None
    assert state.result_set_id is None
    assert state.direction == "X"
    assert state.element_id == 0
    assert state.active_context == AnalysisType.NLTHA


def test_selection_state_initialization():
    """Test that SelectionState can be initialized with values."""
    state = SelectionState(
        result_type="Drifts",
        result_set_id=5,
        direction="Y",
        element_id=10,
        active_context=AnalysisType.PUSHOVER,
    )

    assert state.result_type == "Drifts"
    assert state.result_set_id == 5
    assert state.direction == "Y"
    assert state.element_id == 10
    assert state.active_context == AnalysisType.PUSHOVER


def test_controller_update_selection_partial():
    """Test that update_selection updates only specified fields."""
    fake_repo = _FakeCacheRepo([])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Initial state
    assert controller.selection.direction == "X"
    assert controller.selection.element_id == 0

    # Update only direction
    controller.update_selection(direction="Y")
    assert controller.selection.direction == "Y"
    assert controller.selection.element_id == 0  # Unchanged

    # Update only element_id
    controller.update_selection(element_id=42)
    assert controller.selection.direction == "Y"  # Unchanged
    assert controller.selection.element_id == 42


def test_controller_context_switching():
    """Test context switching between NLTHA and Pushover."""
    fake_repo = _FakeCacheRepo([])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Default is NLTHA
    assert controller.get_active_context() == AnalysisType.NLTHA

    # Switch to Pushover
    controller.set_active_context("Pushover")
    assert controller.get_active_context() == AnalysisType.PUSHOVER

    # Switch back to NLTHA
    controller.set_active_context(AnalysisType.NLTHA)
    assert controller.get_active_context() == AnalysisType.NLTHA


def test_controller_reset_pushover_mapping_specific():
    """Test resetting pushover mapping for specific result set."""
    fake_repo = _FakeCacheRepo(["Push-Mod-X+Ecc+_UX"])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Build mappings for two result sets
    controller.get_pushover_mapping(result_set_id=10)
    controller._pushover_mappings[20] = {"TestCase": "Tx1"}

    # Reset only result_set_id=10
    controller.reset_pushover_mapping(result_set_id=10)

    assert 10 not in controller._pushover_mappings
    assert 20 in controller._pushover_mappings


def test_controller_reset_pushover_mapping_all():
    """Test resetting all pushover mappings."""
    fake_repo = _FakeCacheRepo(["Push-Mod-X+Ecc+_UX"])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Build mappings for two result sets
    controller.get_pushover_mapping(result_set_id=10)
    controller._pushover_mappings[20] = {"TestCase": "Tx1"}

    # Reset all
    controller.reset_pushover_mapping()

    assert len(controller._pushover_mappings) == 0


# ---- SelectionState Transition Tests ----


def test_selection_state_transitions_preserve_unset_fields():
    """Test that updating selection preserves fields not explicitly set."""
    fake_repo = _FakeCacheRepo([])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Set initial state
    controller.update_selection(
        result_type="Drifts",
        result_set_id=1,
        direction="X",
        element_id=0,
    )

    # Update only result_type
    controller.update_selection(result_type="Forces")

    # Other fields should be preserved
    assert controller.selection.result_type == "Forces"
    assert controller.selection.result_set_id == 1  # Preserved
    assert controller.selection.direction == "X"    # Preserved
    assert controller.selection.element_id == 0     # Preserved


def test_selection_state_transitions_from_global_to_element():
    """Test transition from global result to element result."""
    fake_repo = _FakeCacheRepo([])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Start with global result (element_id=0)
    controller.update_selection(
        result_type="Drifts",
        result_set_id=1,
        direction="X",
        element_id=0,
    )
    assert controller.selection.element_id == 0

    # Transition to element result
    controller.update_selection(
        result_type="WallShears",
        element_id=42,
        direction="V2",
    )

    assert controller.selection.result_type == "WallShears"
    assert controller.selection.element_id == 42
    assert controller.selection.direction == "V2"
    assert controller.selection.result_set_id == 1  # Preserved


def test_selection_state_transitions_between_result_sets():
    """Test transition between different result sets."""
    fake_repo = _FakeCacheRepo([])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Start with DES result set
    controller.update_selection(
        result_type="Drifts",
        result_set_id=1,
        direction="X",
    )

    # Switch to MCE result set
    controller.update_selection(result_set_id=2)

    assert controller.selection.result_set_id == 2
    assert controller.selection.result_type == "Drifts"  # Preserved
    assert controller.selection.direction == "X"         # Preserved


def test_context_switch_preserves_selection():
    """Test that context switch doesn't clear selection state."""
    fake_repo = _FakeCacheRepo([])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Set selection in NLTHA context
    controller.update_selection(
        result_type="Drifts",
        result_set_id=1,
        direction="X",
    )

    # Switch to Pushover context
    controller.set_active_context("Pushover")

    # Selection should be preserved
    assert controller.selection.result_type == "Drifts"
    assert controller.selection.result_set_id == 1
    assert controller.selection.direction == "X"
    assert controller.get_active_context() == AnalysisType.PUSHOVER


def test_pushover_mapping_lazy_initialization():
    """Test that pushover mapping is only built when requested."""
    fake_repo = _FakeCacheRepo(["Push-Mod-X+Ecc+_UX"])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)

    # Initially no mappings
    assert len(controller._pushover_mappings) == 0
    assert fake_repo.calls == 0

    # Request mapping for result set 1
    mapping = controller.get_pushover_mapping(result_set_id=1)
    assert len(mapping) > 0
    assert fake_repo.calls == 1

    # Request mapping for same result set - should use cache
    mapping2 = controller.get_pushover_mapping(result_set_id=1)
    assert mapping2 == mapping
    assert fake_repo.calls == 1  # No additional call

    # Request mapping for different result set - should call repo
    controller.get_pushover_mapping(result_set_id=2)
    assert fake_repo.calls == 2


def test_view_controller_mapping_returns_original_when_not_pushover():
    """Test that ResultViewController returns original headers in NLTHA context."""
    fake_repo = _FakeCacheRepo(["Push-Mod-X+Ecc+_UX"])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)
    view_controller = ResultViewController(project_id=1, cache_repo=fake_repo, controller=controller)

    # Set up mapping
    controller._pushover_mappings[1] = {"Push-Mod-X+Ecc+": "Px1"}

    # In NLTHA context, headers should not be mapped
    controller.set_active_context("NLTHA")
    headers = ["Story", "Push-Mod-X+Ecc+", "SomeOther"]
    result = view_controller.apply_mapping_to_headers(headers, result_set_id=1)

    assert result == headers  # Unchanged


def test_view_controller_mapping_handles_missing_keys():
    """Test that ResultViewController handles headers not in mapping."""
    fake_repo = _FakeCacheRepo(["Push-Mod-X+Ecc+_UX"])
    controller = ProjectDetailController(project_id=1, cache_repo=fake_repo)
    view_controller = ResultViewController(project_id=1, cache_repo=fake_repo, controller=controller)

    # Set up partial mapping
    controller._pushover_mappings[1] = {"Push-Mod-X+Ecc+": "Px1"}
    controller.set_active_context("Pushover")

    # Headers include both mapped and unmapped values
    headers = ["Story", "Push-Mod-X+Ecc+", "UnknownCase"]
    result = view_controller.apply_mapping_to_headers(headers, result_set_id=1)

    # Mapped header should be replaced, others preserved
    assert result[0] == "Story"
    assert result[1] == "Px1"
    assert result[2] == "UnknownCase"
