"""Data transformation helpers for Max/Min result views."""

from __future__ import annotations

import math
from typing import Optional

import pandas as pd

from config.result_config import RESULT_CONFIGS


class MaxMinDataProcessor:
    """Pure data helpers for max/min datasets."""

    @staticmethod
    def infer_base_result_type(result_type: Optional[str]) -> str:
        """Infer the base result type name from a Max/Min identifier."""
        if not result_type:
            return "Drifts"
        if result_type.startswith("MaxMin"):
            base = result_type.replace("MaxMin", "", 1)
            return base or "Drifts"
        return result_type

    @staticmethod
    def create_direction_map(available_directions: tuple) -> dict:
        """Create a mapping from display directions (X/Y) to data directions (X/Y/V2/V3/R2/R3/empty)."""
        if "V2" in available_directions and "V3" in available_directions:
            return {"X": "V2", "Y": "V3"}
        if "R2" in available_directions and "R3" in available_directions:
            return {"X": "R2", "Y": "R3"}
        if "" in available_directions or (len(available_directions) == 1 and not available_directions[0]):
            return {"X": "", "Y": ""}
        return {"X": "X", "Y": "Y"}

    @staticmethod
    def get_config_key(base_result_type: str, direction: str) -> str:
        """Return the configuration key for a result type/direction."""
        if not direction or direction == "":
            return base_result_type

        key = f"{base_result_type}_{direction}"
        if key in RESULT_CONFIGS:
            return key
        return base_result_type

    @staticmethod
    def split_direction_columns(df: pd.DataFrame, direction: str) -> tuple[list[str], list[str]]:
        """Return max/min column lists for a direction."""
        if direction == "":
            all_cols = [col for col in df.columns if col != "Story"]
            direction_cols = [
                col
                for col in all_cols
                if not any(col.endswith(f"_{d}") for d in ["X", "Y", "V2", "V3"])
            ]
        else:
            suffix = f"_{direction}"
            direction_cols = [col for col in df.columns if col.endswith(suffix)]

        max_cols = sorted([col for col in direction_cols if "Max" in col])
        min_cols = sorted([col for col in direction_cols if "Min" in col])
        return max_cols, min_cols

    @staticmethod
    def has_signed_min_values(df: pd.DataFrame, min_cols: list[str]) -> bool:
        """Return True when Min columns already include negative values."""
        return any(
            col in df.columns and (pd.to_numeric(df[col], errors="coerce") < 0).any()
            for col in min_cols
        )

    @staticmethod
    def extract_load_case_name(col: str, direction: str) -> str:
        """Extract a load case name from a Max/Min column."""
        if direction:
            col_clean = col.replace(f"_{direction}", "").replace("Max_", "").replace("Min_", "")
        else:
            col_clean = col.replace("Max_", "").replace("Min_", "")
        parts = col_clean.split("_")
        return parts[-1] if len(parts) > 1 else col_clean

    @staticmethod
    def calculate_row_average(values: list[float]) -> Optional[float]:
        """Return the mean of valid numeric values, ignoring None/NaN."""
        valid = [
            val for val in values if val is not None and not (isinstance(val, float) and math.isnan(val))
        ]
        if not valid:
            return None
        return sum(valid) / len(valid)

    @staticmethod
    def compute_average_series(
        df: pd.DataFrame, columns: list[str], absolute: bool = False
    ) -> Optional[pd.Series]:
        """Return a per-story average series for the provided columns."""
        if not columns:
            return None

        valid_cols = [col for col in columns if col in df.columns]
        if not valid_cols:
            return None

        numeric_df = df[valid_cols].apply(pd.to_numeric, errors="coerce")
        if numeric_df.empty:
            return None

        if absolute:
            numeric_df = numeric_df.abs()

        avg_series = numeric_df.mean(axis=1, skipna=True)
        if avg_series.isna().all():
            return None

        return avg_series.fillna(0.0)
