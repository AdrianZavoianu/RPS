from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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


@dataclass
class ComparisonSeries:
    """Single result set's data in a comparison."""

    result_set_id: int
    result_set_name: str
    values: Dict[str, float]  # story → value
    has_data: bool  # False if this result set lacks the requested metric
    warning: Optional[str] = None  # E.g., "No data for this result type"


@dataclass
class ComparisonDataset:
    """Multi-result-set comparison dataset."""

    result_type: str
    direction: Optional[str]
    metric: str  # 'Avg', 'Max', 'Min'
    config: ResultTypeConfig  # Include config for units, multipliers, colors
    series: List[ComparisonSeries]
    data: pd.DataFrame  # Columns: Story | DES_Avg | MCE_Avg | SLE_Avg | Delta
    meta: ResultDatasetMeta
    warnings: List[str] = field(default_factory=list)  # Aggregate warnings for missing data
