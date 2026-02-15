"""Helpers for filtering import data by load case selection."""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Set, Tuple

import pandas as pd


def filter_load_cases(
    load_cases: Sequence[str],
    allowed_load_cases: Optional[Set[str]],
) -> list[str]:
    """Return load cases limited to the allowed set (if provided)."""
    if not allowed_load_cases:
        return list(load_cases)
    return [lc for lc in load_cases if lc in allowed_load_cases]


def filter_dataframe_by_load_cases(
    df: pd.DataFrame,
    allowed_load_cases: Optional[Set[str]],
    column: str = "Output Case",
) -> pd.DataFrame:
    """Filter a DataFrame to allowed load cases using the provided column."""
    if not allowed_load_cases:
        return df
    if column not in df.columns:
        return df
    return df[df[column].isin(allowed_load_cases)].copy()


def filter_cases_and_dataframe(
    df: pd.DataFrame,
    load_cases: Sequence[str],
    allowed_load_cases: Optional[Set[str]],
    column: str = "Output Case",
) -> Tuple[list[str], pd.DataFrame]:
    """Filter load_cases and df in tandem, returning filtered copies."""
    filtered_cases = filter_load_cases(load_cases, allowed_load_cases)
    if not allowed_load_cases:
        return filtered_cases, df
    if not filtered_cases:
        # Return empty DataFrame with same columns to avoid downstream surprises.
        return filtered_cases, df.head(0).copy()
    return filtered_cases, filter_dataframe_by_load_cases(df, allowed_load_cases, column=column)
