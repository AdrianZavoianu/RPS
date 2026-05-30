"""
Pushover Brace Axial Importer.

Imports pushover brace axial forces into BraceAxial records and element caches.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Set

import pandas as pd

from database.models import (
    BraceAxial,
    Element,
    ElementResultsCache,
    LoadCase,
    ResultCategory,
    Story,
)
from processing.pushover.pushover_base_importer import BasePushoverImporter
from processing.pushover.pushover_brace_parser import PushoverBraceParser

logger = logging.getLogger(__name__)


class PushoverBraceImporter(BasePushoverImporter):
    """Importer for pushover brace axial forces."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parser = None
        self._result_category_id = None

    def _get_parser(self) -> PushoverBraceParser:
        """Get or create parser instance."""
        if self._parser is None:
            self._parser = PushoverBraceParser(self.file_path)
        return self._parser

    def _create_stats_dict(self) -> Dict[str, Any]:
        return {
            "x_axials": 0,
            "y_axials": 0,
            "errors": [],
            "result_set_id": self.result_set_id,
        }

    def _ensure_entities(self):
        """Ensure all brace elements and stories exist."""
        parser = self._get_parser()

        results = None
        if self.selected_load_cases_x:
            results = parser.parse("X")
        if (
            results is None or results.axials is None or results.axials.empty
        ) and self.selected_load_cases_y:
            results = parser.parse("Y")

        if results is None or results.axials is None or results.axials.empty:
            return

        df = results.axials

        for brace_name in df["Brace"].unique().tolist():
            self._get_or_create_element(str(brace_name), "Brace")

        for idx, story_name in enumerate(df["Story"].unique().tolist()):
            self._get_or_create_story(str(story_name), sort_order=idx)

        self._get_or_create_result_category_id()

    def _import_direction(self, direction: str, selected_load_cases: Set[str]) -> Dict:
        """Import brace axial forces for one pushover direction."""
        stats = {"axials": 0, "errors": []}
        results = self._get_parser().parse(direction)

        if results.axials is not None:
            stats["axials"] = self._import_axials(results.axials, selected_load_cases)

        return stats

    def _import_axials(self, df: pd.DataFrame, selected_load_cases: Set[str]) -> int:
        """Import parsed brace axial rows into BraceAxial records."""
        count = 0
        result_category_id = self._get_or_create_result_category_id()

        for _, row in df.iterrows():
            load_case_name = str(row["Output Case"])
            if load_case_name not in selected_load_cases:
                continue

            brace_name = str(row["Brace"])
            story_name = str(row["Story"])
            element = self.elements_cache.get(f"Brace:{brace_name}")
            story = self.stories_cache.get(story_name)
            if not element or not story:
                continue

            min_axial = row["MinAxial"]
            max_axial = row["MaxAxial"]
            if pd.isna(min_axial) and pd.isna(max_axial):
                continue

            load_case = self._get_or_create_load_case(load_case_name)
            record = BraceAxial(
                element_id=element.id,
                story_id=story.id,
                load_case_id=load_case.id,
                result_category_id=result_category_id,
                min_axial=float(min_axial) if not pd.isna(min_axial) else 0.0,
                max_axial=float(max_axial) if not pd.isna(max_axial) else None,
                story_sort_order=story.sort_order,
            )
            self.session.add(record)
            count += 1

        return count

    def _build_cache(self):
        """Build element result cache entries for brace min/max axial forces."""
        self.session.query(ElementResultsCache).filter(
            ElementResultsCache.result_set_id == self.result_set_id,
            ElementResultsCache.result_type.in_(["BraceAxials_Min", "BraceAxials_Max"]),
        ).delete(synchronize_session=False)

        self._cache_axials("Min")
        self._cache_axials("Max")
        logger.info("Built element cache for brace axials")

    def _cache_axials(self, max_min: str):
        """Build cache for either minimum or maximum brace axial values."""
        load_case_ids = self._get_load_case_ids()
        if not load_case_ids:
            logger.warning("No load cases in cache for brace axials %s", max_min)
            return

        result_category_id = self._get_or_create_result_category_id()
        records = (
            self.session.query(
                BraceAxial,
                LoadCase.name,
                BraceAxial.element_id,
                BraceAxial.story_id,
                BraceAxial.story_sort_order,
            )
            .join(LoadCase, BraceAxial.load_case_id == LoadCase.id)
            .join(Element, BraceAxial.element_id == Element.id)
            .filter(
                BraceAxial.load_case_id.in_(load_case_ids),
                BraceAxial.result_category_id == result_category_id,
                Element.element_type == "Brace",
            )
            .all()
        )

        element_story_data = {}
        value_attr = "min_axial" if max_min == "Min" else "max_axial"
        for axial, load_case_name, element_id, story_id, story_sort_order in records:
            value = getattr(axial, value_attr)
            if value is None:
                continue

            key = (element_id, story_id)
            if key not in element_story_data:
                element_story_data[key] = {
                    "results_matrix": {},
                    "story_sort_order": story_sort_order,
                }
            element_story_data[key]["results_matrix"][load_case_name] = value

        result_type = f"BraceAxials_{max_min}"
        for (element_id, story_id), data in element_story_data.items():
            cache_entry = ElementResultsCache(
                project_id=self.project_id,
                result_set_id=self.result_set_id,
                element_id=element_id,
                story_id=story_id,
                result_type=result_type,
                story_sort_order=data["story_sort_order"],
                results_matrix=data["results_matrix"],
            )
            self.session.add(cache_entry)

        logger.info("Created %s cache entries for %s", len(element_story_data), result_type)

    def _get_or_create_result_category_id(self) -> int:
        """Create a result category so brace rows stay scoped to this pushover result set."""
        if self._result_category_id is not None:
            return self._result_category_id

        category = (
            self.session.query(ResultCategory)
            .filter(
                ResultCategory.result_set_id == self.result_set_id,
                ResultCategory.category_name == "Pushover",
                ResultCategory.category_type == "Elements",
            )
            .first()
        )
        if not category:
            category = ResultCategory(
                result_set_id=self.result_set_id,
                category_name="Pushover",
                category_type="Elements",
            )
            self.session.add(category)
            self.session.flush()

        self._result_category_id = category.id
        return category.id
