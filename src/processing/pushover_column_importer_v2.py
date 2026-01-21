"""
Pushover Column Results Importer (v2 - using Template Method pattern)

Imports pushover column hinge rotations into the database.
This version extends PushoverElementBaseImporter for reduced code duplication.
"""

import logging
from pathlib import Path
from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from database.models import Element, Story, LoadCase, ColumnRotation
from processing.pushover_element_base import (
    PushoverElementBaseImporter,
    ResultTypeConfig,
)
from processing.pushover_column_parser import PushoverColumnParser

logger = logging.getLogger(__name__)


class PushoverColumnImporterV2(PushoverElementBaseImporter):
    """Importer for pushover column hinge rotations.

    Imports column rotation values (R2 and R3) from Excel files
    for both X and Y directions.

    This is a refactored version using the Template Method pattern,
    reducing ~400 lines to ~80 lines.
    """

    def _get_element_type(self) -> str:
        return 'Column'

    def _create_parser(self):
        return PushoverColumnParser(self.file_path)

    def _get_story_mapping_sheet(self) -> str:
        return 'Fiber Hinge States'

    def _get_result_types(self) -> List[ResultTypeConfig]:
        return [
            ResultTypeConfig(
                name='R2',
                attr_name='rotations_r2',
                cache_suffix='_R2',
                model_field='rotation',
                model_class=ColumnRotation,
            ),
            ResultTypeConfig(
                name='R3',
                attr_name='rotations_r3',
                cache_suffix='_R3',
                model_field='rotation',
                model_class=ColumnRotation,
            ),
        ]

    def _create_result_record(
        self,
        config: ResultTypeConfig,
        element: Element,
        story: Story,
        load_case: LoadCase,
        value: float,
        story_sort_order: int,
    ) -> ColumnRotation:
        return ColumnRotation(
            element_id=element.id,
            story_id=story.id,
            load_case_id=load_case.id,
            direction=config.name,  # 'R2' or 'R3'
            rotation=value,
            story_sort_order=story_sort_order,
        )

    def _get_cache_base_name(self) -> str:
        return 'ColumnRotations'

    def _get_cache_query_filters(self, config: ResultTypeConfig, model_class) -> list:
        """Filter by direction for column rotations."""
        return [model_class.direction == config.name]


# Alias for backward compatibility
PushoverColumnImporter = PushoverColumnImporterV2
