"""Shared fixtures for GUI tests."""

from __future__ import annotations

import os

import pandas as pd
import pytest
from PyQt6.QtWidgets import QApplication

from config.result_config import get_config
from services.result_service.models import MaxMinDataset, ResultDataset, ResultDatasetMeta


@pytest.fixture(scope="session")
def qt_app():
    """Provide a QApplication instance for GUI tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    app.processEvents()
    yield app
    app.processEvents()


@pytest.fixture
def sample_result_dataset():
    """Small ResultDataset for table/plot widgets."""
    df = pd.DataFrame(
        {
            "Story": ["Level 1", "Level 2"],
            "LC1": [0.01, 0.02],
            "LC2": [0.015, 0.025],
            "Avg": [0.0125, 0.0225],
            "Max": [0.015, 0.025],
            "Min": [0.01, 0.02],
        }
    )

    meta = ResultDatasetMeta(
        result_type="Drifts",
        direction="X",
        result_set_id=1,
        display_name="Drifts X",
    )

    return ResultDataset(
        meta=meta,
        data=df,
        config=get_config("Drifts"),
        load_case_columns=["LC1", "LC2"],
        summary_columns=["Avg", "Max", "Min"],
    )


@pytest.fixture
def sample_maxmin_dataset():
    """Small MaxMinDataset for MaxMinDriftsWidget."""
    df = pd.DataFrame(
        {
            "Story": ["Roof", "Level 1", "Base"],
            "Max_DES_X": [0.03, 0.02, 0.01],
            "Min_DES_X": [0.015, 0.01, 0.005],
            "Max_DES_Y": [0.025, 0.017, 0.009],
            "Min_DES_Y": [0.012, 0.008, 0.004],
        }
    )

    meta = ResultDatasetMeta(
        result_type="MaxMinDrifts",
        direction=None,
        result_set_id=1,
        display_name="Max/Min Drifts",
    )

    return MaxMinDataset(
        meta=meta,
        data=df,
        directions=("X", "Y"),
        source_type="Drifts",
    )


@pytest.fixture
def rotations_df_max():
    """Sample rotations dataset (Max)."""
    return pd.DataFrame(
        {
            "Element": ["E1", "E2", "E3"],
            "Story": ["Level 1", "Level 1", "Level 2"],
            "LoadCase": ["LC1", "LC1", "LC2"],
            "Rotation": [0.5, 1.0, 0.8],
            "StoryOrder": [1, 1, 2],
            "StoryIndex": [0, 0, 1],
        }
    )


@pytest.fixture
def rotations_df_min():
    """Sample rotations dataset (Min)."""
    return pd.DataFrame(
        {
            "Element": ["E1", "E2", "E3"],
            "Story": ["Level 1", "Level 1", "Level 2"],
            "LoadCase": ["LC1", "LC1", "LC2"],
            "Rotation": [-0.4, -0.9, -0.6],
            "StoryOrder": [1, 1, 2],
            "StoryIndex": [0, 0, 1],
        }
    )


@pytest.fixture
def beam_rotations_df_max():
    """Sample beam rotations dataset (Max)."""
    return pd.DataFrame(
        {
            "Story": ["Level 1", "Level 2"],
            "LoadCase": ["LC1", "LC2"],
            "Rotation": [0.6, 0.8],
            "StoryOrder": [1, 2],
        }
    )


@pytest.fixture
def beam_rotations_df_min():
    """Sample beam rotations dataset (Min)."""
    return pd.DataFrame(
        {
            "Story": ["Level 1", "Level 2"],
            "LoadCase": ["LC1", "LC2"],
            "Rotation": [-0.55, -0.75],
            "StoryOrder": [1, 2],
        }
    )
