"""Loaders for combined global responses views."""

import logging
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from gui.project_detail.window import ProjectDetailWindow
    from gui.project_detail.content import ContentArea
    from services.result_service import MaxMinDataset

logger = logging.getLogger(__name__)


def load_combined_responses(window: "ProjectDetailWindow", result_set_id: int, area: "ContentArea") -> None:
    """Load combined global responses (Displacements, Drifts, Accelerations, Forces)."""
    try:
        datasets: Dict[str, "MaxMinDataset"] = {}
        
        # We need MaxMin data for each type to get the envelopes
        for result_type in ["Displacements", "Drifts", "Accelerations", "Forces"]:
            try:
                # The data processor expects both X and Y in the maxmin dataset for global responses.
                # get_maxmin_dataset typically handles fetching both directions.
                dataset = window.result_service.get_maxmin_dataset(
                    base_result_type=result_type,
                    result_set_id=result_set_id,
                )
                if dataset:
                    datasets[result_type] = dataset
            except Exception as e:
                logger.debug(f"Failed to load {result_type} dataset for combined view: {e}")
                
        if not datasets:
            logger.warning("No datasets found for combined responses view")
            return

        widget = area.show_combined_responses()
        widget.load_datasets(datasets)
        
    except Exception as e:
        logger.error(f"Failed to load combined responses view: {e}", exc_info=True)
