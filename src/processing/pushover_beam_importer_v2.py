"""
Pushover Beam Results Importer (v2 - using Template Method pattern)

Imports pushover beam hinge rotations into the database.
This version extends PushoverElementBaseImporter for reduced code duplication.
"""

import logging
from pathlib import Path
from typing import Callable, List, Optional

from sqlalchemy.orm import Session

from database.models import Element, Story, LoadCase, BeamRotation
from processing.pushover_element_base import (
    PushoverElementBaseImporter,
    ResultTypeConfig,
)
from processing.pushover_beam_parser import PushoverBeamParser

logger = logging.getLogger(__name__)


class PushoverBeamImporterV2(PushoverElementBaseImporter):
    """Importer for pushover beam hinge rotations.

    Imports beam plastic rotation values (R3 Plastic) from Excel files
    for both X and Y directions.

    This is a refactored version using the Template Method pattern,
    reducing ~300 lines to ~60 lines.
    """

    def _get_element_type(self) -> str:
        return 'Beam'

    def _create_parser(self):
        return PushoverBeamParser(self.file_path)

    def _get_story_mapping_sheet(self) -> str:
        return 'Hinge States'

    def _get_result_types(self) -> List[ResultTypeConfig]:
        return [
            ResultTypeConfig(
                name='rotations',
                attr_name='rotations',
                cache_suffix='',  # BeamRotations (no suffix)
                model_field='r3_plastic',
                model_class=BeamRotation,
            )
        ]

    def _create_result_record(
        self,
        config: ResultTypeConfig,
        element: Element,
        story: Story,
        load_case: LoadCase,
        value: float,
        story_sort_order: int,
    ) -> BeamRotation:
        return BeamRotation(
            element_id=element.id,
            story_id=story.id,
            load_case_id=load_case.id,
            r3_plastic=value,
            story_sort_order=story_sort_order,
        )

    def _get_cache_base_name(self) -> str:
        return 'BeamRotations'


# Alias for backward compatibility
PushoverBeamImporter = PushoverBeamImporterV2
