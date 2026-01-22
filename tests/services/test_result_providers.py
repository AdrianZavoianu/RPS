"""Tests for dataset provider utilities (standard, element, joint)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import pytest

from services.result_service import providers


@dataclass
class DummyCacheEntry:
    shell_object: str
    unique_name: str
    results_matrix: Dict[str, float]


class DummyCacheRepo:
    def __init__(self, entries: Optional[List[Dict]] = None) -> None:
        self.entries = entries or []
        self.calls: List[Dict] = []

    # Methods used by StandardDatasetProvider / ElementDatasetProvider.
    def get_cache_for_display(self, **kwargs):
        self.calls.append(kwargs)
        return self.entries


class DummyElementCacheRepo(DummyCacheRepo):
    def get_cache_for_display(self, **kwargs):
        self.calls.append(kwargs)
        return self.entries


class DummyJointCacheRepo:
    def __init__(self, entries: List[DummyCacheEntry]) -> None:
        self.entries = entries
        self.calls: List[Dict] = []

    def get_all_for_type(self, **kwargs):
        self.calls.append(kwargs)
        return self.entries


def test_standard_dataset_provider_caches(monkeypatch):
    """Standard provider should cache results and honor invalidation."""
    repo = DummyCacheRepo(entries=[{"story_id": 1}])
    story_provider = object()
    sentinel = object()

    def fake_builder(**kwargs):
        return sentinel

    monkeypatch.setattr(providers, "build_standard_dataset", fake_builder)

    provider = providers.StandardDatasetProvider(
        project_id=1,
        cache_repo=repo,
        story_provider=story_provider,
    )

    assert provider.get("Drifts", "X", 1) is sentinel
    # Second call should hit cache.
    assert provider.get("Drifts", "X", 1) is sentinel
    assert len(repo.calls) == 1

    provider.invalidate("Drifts", "X", 1)
    assert provider.get("Drifts", "X", 1) is sentinel
    assert len(repo.calls) == 2


def test_element_dataset_provider_handles_missing_repo(monkeypatch):
    """Element provider returns None when repository is absent."""
    story_provider = object()
    provider = providers.ElementDatasetProvider(
        project_id=1,
        element_cache_repo=None,
        story_provider=story_provider,
    )
    assert provider.get(element_id=10, result_type="WallShears", direction="V2", result_set_id=5) is None


def test_element_dataset_provider_uses_full_result_type(monkeypatch):
    """Element provider should assemble the full result type before querying."""
    repo = DummyElementCacheRepo(entries=[{"element_id": 10}])
    story_provider = object()
    sentinel = object()

    def fake_builder(**kwargs):
        assert kwargs["result_type"] == "WallShears"
        assert kwargs["direction"] == "V2"
        return sentinel

    monkeypatch.setattr(providers, "build_element_dataset", fake_builder)

    provider = providers.ElementDatasetProvider(
        project_id=99,
        element_cache_repo=repo,
        story_provider=story_provider,
    )

    result = provider.get(element_id=10, result_type="WallShears", direction="V2", result_set_id=7)
    assert result is sentinel
    assert repo.calls[0]["result_type"] == "WallShears_V2"


def test_joint_dataset_provider_builds_summary_columns():
    """Joint provider should compute load case columns and summaries."""
    entries = [
        DummyCacheEntry(
            shell_object="F1",
            unique_name="Joint1",
            results_matrix={"DES": 10.0, "MCE": 20.0},
        ),
        DummyCacheEntry(
            shell_object="F2",
            unique_name="Joint2",
            results_matrix={"DES": 15.0, "MCE": 25.0},
        ),
    ]
    repo = DummyJointCacheRepo(entries=entries)
    provider = providers.JointDatasetProvider(project_id=1, joint_cache_repo=repo)

    dataset = provider.get("SoilPressures_Min", result_set_id=5)
    assert dataset is not None
    assert dataset.load_case_columns == ["DES", "MCE"]
    assert dataset.summary_columns == ["Average", "Maximum", "Minimum"]
    assert isinstance(dataset.data, pd.DataFrame)
    assert list(dataset.data.columns) == [
        "Shell Object",
        "Unique Name",
        "DES",
        "MCE",
        "Average",
        "Maximum",
        "Minimum",
    ]
    # Ensure caching works.
    assert provider.get("SoilPressures_Min", result_set_id=5) is dataset
    assert len(repo.calls) == 1

    provider.invalidate("SoilPressures_Min", 5)
    assert provider.get("SoilPressures_Min", 5) is not None
    assert len(repo.calls) == 2
