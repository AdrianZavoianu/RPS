"""
Pushover Brace Forces Parser.

Parses pushover brace axial forces from "Element Forces - Braces" sheets.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class PushoverBraceResults:
    """Container for pushover brace axial force data."""

    axials: Optional[pd.DataFrame] = None
    direction: str = ""


class PushoverBraceParser:
    """Parser for pushover brace axial force Excel files."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.excel_data = pd.ExcelFile(file_path)
        self._sheet_cache = {}
        self._results_cache = {}

    def _read_sheet(
        self, sheet_name: str, header: int = 1, drop_units: bool = True
    ) -> pd.DataFrame:
        """Read and cache a sheet from the Excel file."""
        cache_key = (sheet_name, header, drop_units)
        if cache_key in self._sheet_cache:
            return self._sheet_cache[cache_key].copy()

        df = pd.read_excel(self.excel_data, sheet_name=sheet_name, header=header)
        if drop_units and len(df) > 0:
            df = df.drop(0)

        self._sheet_cache[cache_key] = df
        return df.copy()

    def parse(self, direction: str) -> PushoverBraceResults:
        """Parse brace axial forces for a pushover direction."""
        direction = direction.upper()
        if direction not in ["X", "Y", "XY"]:
            raise ValueError(f"Invalid direction '{direction}'. Must be 'X', 'Y', or 'XY'.")

        cached = self._results_cache.get(direction)
        if cached is not None:
            return cached

        results = PushoverBraceResults(direction=direction)
        try:
            results.axials = self._extract_brace_axials(direction)
        except Exception as exc:
            logger.warning("Failed to extract brace axials for %s: %s", direction, exc)
            results.axials = None

        self._results_cache[direction] = results
        return results

    def _extract_brace_axials(self, direction: str) -> pd.DataFrame:
        """Extract min/max brace axial forces per brace, story, and output case."""
        df = self._read_sheet("Element Forces - Braces")

        required_cols = ["Story", "Brace", "Output Case", "P"]
        df = df[required_cols].copy()

        df = self._filter_by_direction(df, direction)
        if df.empty:
            return pd.DataFrame(columns=["Brace", "Story", "Output Case", "MinAxial", "MaxAxial"])

        brace_order = df["Brace"].unique().tolist()
        story_order = df["Story"].unique().tolist()

        df["P"] = pd.to_numeric(df["P"], errors="coerce")
        df = df.dropna(subset=["P"])
        if df.empty:
            return pd.DataFrame(columns=["Brace", "Story", "Output Case", "MinAxial", "MaxAxial"])

        grouped = (
            df.groupby(["Brace", "Story", "Output Case"], sort=False)["P"]
            .agg(["min", "max"])
            .reset_index()
        )
        grouped = grouped.rename(columns={"min": "MinAxial", "max": "MaxAxial"})
        grouped["MinAxial"] = grouped["MinAxial"].round(1)
        grouped["MaxAxial"] = grouped["MaxAxial"].round(1)

        grouped["Brace"] = pd.Categorical(grouped["Brace"], categories=brace_order, ordered=True)
        grouped["Story"] = pd.Categorical(grouped["Story"], categories=story_order, ordered=True)
        grouped = grouped.sort_values(["Brace", "Story"]).reset_index(drop=True)

        return grouped[["Brace", "Story", "Output Case", "MinAxial", "MaxAxial"]]

    def get_available_directions(self) -> List[str]:
        """Detect available pushover directions from brace force output cases."""
        df = self._read_sheet("Element Forces - Braces")
        output_cases = df["Output Case"].unique()

        directions = []
        if any("X" in str(case).upper() and "Y" in str(case).upper() for case in output_cases):
            directions.append("XY")
        if any("X" in str(case).upper() for case in output_cases):
            directions.append("X")
        if any("Y" in str(case).upper() for case in output_cases):
            directions.append("Y")
        return directions

    def get_output_cases(self, direction: str) -> List[str]:
        """Get output case names for a pushover direction."""
        df = self._read_sheet("Element Forces - Braces")
        direction = direction.upper()
        filtered = self._filter_by_direction(df, direction)
        return sorted(filtered["Output Case"].unique().tolist())

    def get_braces(self) -> List[str]:
        """Get brace names from the file."""
        df = self._read_sheet("Element Forces - Braces")
        return sorted(df["Brace"].unique().tolist())

    @staticmethod
    def _filter_by_direction(df: pd.DataFrame, direction: str) -> pd.DataFrame:
        """Filter rows by pushover direction encoded in the output case name."""
        if direction == "XY":
            return df[
                df["Output Case"].apply(
                    lambda case: "X" in str(case).upper() and "Y" in str(case).upper()
                )
            ].copy()

        return df[df["Output Case"].apply(lambda case: direction in str(case).upper())].copy()
