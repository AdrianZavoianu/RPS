"""Report section data loader with caching."""

from __future__ import annotations

from typing import Iterable, Optional

import pandas as pd

from .report_models import ReportSection


class ReportSectionLoader:
    """Fetch and cache datasets for report sections."""

    def __init__(self, result_service, reporting_service, project_id: int, analysis_context: str) -> None:
        self.result_service = result_service
        self.reporting_service = reporting_service
        self.project_id = project_id
        self.analysis_context = analysis_context
        self._cache: dict[tuple, object] = {}

    def clear_cache(self) -> None:
        """Clear cached datasets."""
        self._cache.clear()

    def needs_fetch(self, sections: Iterable[ReportSection]) -> bool:
        """Return True if any section is missing in the cache."""
        for section in sections:
            cache_key = self._cache_key(section)
            if cache_key and cache_key not in self._cache:
                return True
        return False

    def load_sections(self, sections: Iterable[ReportSection]) -> list[ReportSection]:
        """Load datasets for sections, using cache where possible."""
        loaded_sections = list(sections)
        for section in loaded_sections:
            cache_key = self._cache_key(section)
            if cache_key in self._cache:
                self._apply_cached(section, self._cache[cache_key])
                continue

            data = self._fetch_section_data(section)
            if cache_key:
                self._cache[cache_key] = data
            self._apply_cached(section, data)
        return loaded_sections

    def get_sections_with_data(self, sections: Iterable[ReportSection]) -> list[ReportSection]:
        """Return sections that have data available after loading."""
        loaded_sections = self.load_sections(sections)
        return [section for section in loaded_sections if self._has_data(section)]

    def _cache_key(self, section: ReportSection) -> Optional[tuple]:
        if section.category == "Global":
            return ("Global", section.result_type, section.direction, section.result_set_id)
        if section.category == "Element":
            return ("Element", section.result_type, section.result_set_id)
        if section.category == "Joint":
            return ("Joint", section.result_type, section.result_set_id)
        return None

    @staticmethod
    def _apply_cached(section: ReportSection, data: object) -> None:
        if section.category == "Global":
            section.dataset = data
        elif section.category == "Element":
            section.element_data = data
        elif section.category == "Joint":
            section.joint_data = data

    @staticmethod
    def _has_data(section: ReportSection) -> bool:
        if section.category == "Global":
            return section.dataset is not None
        if section.category == "Element":
            return section.element_data is not None
        if section.category == "Joint":
            return section.joint_data is not None
        return False

    def _fetch_section_data(self, section: ReportSection) -> object:
        if section.category == "Global":
            return self.result_service.get_standard_dataset(
                section.result_type,
                section.direction,
                section.result_set_id,
            )

        if section.category == "Element":
            if section.result_type == "BeamRotations":
                return self.reporting_service.get_beam_rotation_data(
                    self.project_id,
                    section.result_set_id,
                    self.analysis_context,
                )
            if section.result_type == "ColumnRotations":
                return self.reporting_service.get_column_rotation_data(
                    self.project_id,
                    section.result_set_id,
                    self.analysis_context,
                )
            return None

        if section.category == "Joint":
            if section.result_type == "SoilPressures_Min":
                return self._fetch_soil_pressure_data(section.result_set_id)
            return None

        return None

    def _fetch_soil_pressure_data(self, result_set_id: int) -> Optional[dict]:
        """Fetch soil pressure data for reporting."""
        is_pushover = self.analysis_context == "Pushover"
        dataset = self.result_service.get_joint_dataset(
            "SoilPressures_Min",
            result_set_id,
            is_pushover=is_pushover,
        )

        if dataset is None or dataset.data is None or dataset.data.empty:
            return None

        df = dataset.data.copy()
        load_case_cols = list(dataset.load_case_columns)

        if not load_case_cols:
            return None

        # Calculate absolute average for sorting (soil pressures are negative, so we use abs)
        numeric_df = df[load_case_cols].apply(pd.to_numeric, errors="coerce")

        # Add Avg, Max, Min if not already present (skip Avg for Pushover)
        if "Avg" not in df.columns and self.analysis_context != "Pushover":
            df["Avg"] = numeric_df.abs().mean(axis=1)
        if "Max" not in df.columns:
            df["Max"] = numeric_df.abs().max(axis=1)
        if "Min" not in df.columns:
            df["Min"] = numeric_df.abs().min(axis=1)

        df["_abs_avg"] = numeric_df.abs().mean(axis=1)

        top_10_df = df.nlargest(10, "_abs_avg").copy()

        df = df.drop(columns=["_abs_avg"])
        top_10_df = top_10_df.drop(columns=["_abs_avg"])

        # Prepare scatter plot data: (load_case_index, pressure_value)
        plot_data = []
        for lc_idx, lc in enumerate(load_case_cols):
            if lc in numeric_df.columns:
                values = numeric_df[lc].dropna().abs().values
                for value in values:
                    plot_data.append((lc_idx, value))

        return {
            "all_data": df,
            "top_10": top_10_df,
            "load_cases": load_case_cols,
            "plot_data": plot_data,
        }
