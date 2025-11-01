import pytest

from processing.result_service import ResultDataService
from processing.result_service.maxmin_builder import (
    build_drift_maxmin_dataset,
    build_generic_maxmin_dataset,
)
from processing.result_service.story_loader import StoryProvider


class CacheEntryStub:
    def __init__(self, story_id, result_type, results_matrix, story_sort_order=0):
        self.story_id = story_id
        self.result_type = result_type
        self.results_matrix = results_matrix
        self.story_sort_order = story_sort_order


class StoryStub:
    def __init__(self, story_id, name, sort_order):
        self.id = story_id
        self.name = name
        self.sort_order = sort_order


class CacheRepoStub:
    def __init__(self, entries):
        self._entries = entries
        self.calls = 0

    def get_cache_for_display(self, project_id, result_type, result_set_id):
        self.calls += 1
        return list(self._entries)


class StoryRepoStub:
    def __init__(self, stories):
        self._stories = stories

    def get_by_project(self, project_id):
        return list(self._stories)


class LoadCaseRepoStub:
    def __init__(self, cases=None):
        self._cases = cases or {}

    def get_by_project(self, project_id):
        return []

    def get_by_id(self, case_id):
        return self._cases.get(case_id)


@pytest.fixture()
def drifts_cache_entries():
    story_one = StoryStub(1, "Roof", 0)
    story_two = StoryStub(2, "GFL", 1)

    entry_one = CacheEntryStub(
        story_id=1,
        result_type="Drifts",
        results_matrix={
            "DES_TH01_X": 0.001,
            "DES_TH02_X": 0.002,
            "DES_TH01_Y": 0.010,
        },
        story_sort_order=0,
    )
    entry_two = CacheEntryStub(
        story_id=2,
        result_type="Drifts",
        results_matrix={
            "DES_TH01_X": 0.003,
            "DES_TH02_X": 0.004,
        },
        story_sort_order=1,
    )

    entries = [entry_one, entry_two]
    return entries, [story_one, story_two]


def test_get_standard_dataset_builds_dataframe_and_caches(drifts_cache_entries):
    entries, stories = drifts_cache_entries
    cache_repo = CacheRepoStub(entries)
    story_repo = StoryRepoStub(stories)
    load_case_repo = LoadCaseRepoStub()

    service = ResultDataService(
        project_id=1,
        cache_repo=cache_repo,
        story_repo=story_repo,
        load_case_repo=load_case_repo,
    )

    dataset = service.get_standard_dataset("Drifts", "X", result_set_id=42)

    assert dataset is not None
    assert dataset.meta.display_name == "Story Drifts - X Direction"
    assert list(dataset.data["Story"]) == ["GFL", "Roof"]
    assert dataset.load_case_columns == ["TH01", "TH02"]
    assert dataset.summary_columns == ["Avg", "Max", "Min"]
    assert pytest.approx(dataset.data.loc[0, "TH01"]) == 0.3
    assert pytest.approx(dataset.data.loc[1, "TH02"]) == 0.2
    assert cache_repo.calls == 1

    cached = service.get_standard_dataset("Drifts", "X", result_set_id=42)
    assert cached is dataset
    assert cache_repo.calls == 1

    service.invalidate_standard_dataset("Drifts", "X", 42)
    assert service.get_standard_dataset("Drifts", "X", 42) is not None


class LoadCaseStub:
    def __init__(self, case_id, name):
        self.id = case_id
        self.name = name


class DriftRecordStub:
    def __init__(self, story_id, load_case_id, direction, original_max, original_min):
        self.story_id = story_id
        self.load_case_id = load_case_id
        self.direction = direction
        self.original_max = original_max
        self.original_min = original_min


class AbsoluteMaxMinRepoStub:
    def __init__(self, records):
        self._records = records

    def get_by_result_set(self, project_id, result_set_id):
        return list(self._records)


class FakeQuery:
    def __init__(self, records):
        self._records = records

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return list(self._records)


class FakeSession:
    def __init__(self, records):
        self._records = records

    def query(self, *args, **kwargs):
        return FakeQuery(self._records)


class GenericRecordStub:
    def __init__(self, story_id, direction, max_value, min_value, story_sort_order=0):
        self.story_id = story_id
        self.direction = direction
        self.story_sort_order = story_sort_order
        self.max_acceleration = getattr(self, "max_acceleration", None)
        self.min_acceleration = getattr(self, "min_acceleration", None)
        self.max_force = getattr(self, "max_force", None)
        self.min_force = getattr(self, "min_force", None)
        self.max_displacement = getattr(self, "max_displacement", None)
        self.min_displacement = getattr(self, "min_displacement", None)
        # Store values based on attribute names expected by builder
        self.max_acceleration = max_value
        self.min_acceleration = min_value
        self.max_force = max_value
        self.min_force = min_value
        self.max_displacement = max_value
        self.min_displacement = min_value


def test_build_drift_maxmin_dataset_produces_expected_columns():
    stories = [StoryStub(1, "Roof", 0), StoryStub(2, "GFL", 1)]
    story_repo = StoryRepoStub(stories)
    story_provider = StoryProvider(story_repo, project_id=1)
    load_cases = {
        101: LoadCaseStub(101, "TH01"),
        102: LoadCaseStub(102, "TH02"),
    }
    load_case_repo = LoadCaseRepoStub(load_cases)
    abs_repo = AbsoluteMaxMinRepoStub(
        [
            DriftRecordStub(1, 101, "X", 0.002, -0.0015),
            DriftRecordStub(2, 101, "X", 0.0035, -0.0025),
            DriftRecordStub(1, 102, "Y", 0.004, -0.003),
        ]
    )

    dataset = build_drift_maxmin_dataset(
        project_id=1,
        result_set_id=7,
        abs_maxmin_repo=abs_repo,
        story_provider=story_provider,
        load_case_repo=load_case_repo,
    )

    assert dataset is not None
    assert "Max_TH01_X" in dataset.data.columns
    assert "Min_TH01_X" in dataset.data.columns
    assert "Max_TH02_Y" in dataset.data.columns
    assert list(dataset.data["Story"]) == ["Roof", "GFL"]
    assert pytest.approx(dataset.data.loc[0, "Max_TH01_X"]) == 0.2


def test_build_generic_maxmin_dataset_shapes_data():
    stories = [StoryStub(1, "Roof", 0), StoryStub(2, "GFL", 1)]
    story_repo = StoryRepoStub(stories)
    story_provider = StoryProvider(story_repo, project_id=1)

    load_case_one = LoadCaseStub(201, "TH01")
    load_case_two = LoadCaseStub(202, "TH02")

    records = [
        (
            GenericRecordStub(1, "UX", 0.5, -0.3, story_sort_order=0),
            load_case_one,
            stories[0],
        ),
        (
            GenericRecordStub(2, "UY", 0.4, -0.2, story_sort_order=1),
            load_case_two,
            stories[1],
        ),
    ]

    dataset = build_generic_maxmin_dataset(
        project_id=1,
        result_set_id=10,
        base_result_type="Accelerations",
        session=FakeSession(records),
        category_id_provider=lambda _: 1,
        story_provider=story_provider,
    )

    assert dataset is not None
    assert "Max_TH01_X" in dataset.data.columns
    assert "Min_TH01_X" in dataset.data.columns
    assert list(dataset.data["Story"]) == ["Roof", "GFL"]
