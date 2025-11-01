from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import pandas as pd

from config.result_config import ResultTypeConfig


@dataclass(frozen=True)
class ResultDatasetMeta:
    """Identifying metadata for a dataset."""

    result_type: str
    direction: Optional[str]
    result_set_id: int
    display_name: str


@dataclass
class ResultDataset:
    """Container for a transformed result dataset."""

    meta: ResultDatasetMeta
    data: pd.DataFrame
    config: ResultTypeConfig
    load_case_columns: List[str]
    summary_columns: List[str] = field(default_factory=list)


@dataclass
class MaxMinDataset:
    """Container for absolute max/min drift data across both directions."""

    meta: ResultDatasetMeta
    data: pd.DataFrame
    directions: Tuple[str, ...] = ("X", "Y")
    source_type: str = "Drifts"
