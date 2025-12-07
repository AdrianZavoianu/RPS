"""Shared enums and helpers for analysis types and directions."""

from __future__ import annotations

from enum import Enum
from typing import Optional


class AnalysisType(str, Enum):
    NLTHA = "NLTHA"
    PUSHOVER = "Pushover"
    MIXED = "Mixed"


def normalize_analysis_type(value: Optional[str]) -> AnalysisType:
    """Normalize a string/enum to a canonical AnalysisType."""
    if not value:
        return AnalysisType.NLTHA
    if isinstance(value, AnalysisType):
        return value
    lower = value.strip().lower()
    if lower == "pushover":
        return AnalysisType.PUSHOVER
    if lower == "mixed":
        return AnalysisType.MIXED
    return AnalysisType.NLTHA


def is_pushover(value: Optional[str]) -> bool:
    return normalize_analysis_type(value) == AnalysisType.PUSHOVER


def is_nltha(value: Optional[str]) -> bool:
    return normalize_analysis_type(value) == AnalysisType.NLTHA
