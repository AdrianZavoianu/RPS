"""Project data loading helpers."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def load_project_data(window):
    """Load project data and populate browser."""
    from services.data_access import DataAccessService

    window.session.expire_all()
    window.result_service.invalidate_all()
    window.controller.reset_pushover_mapping()
    try:
        data_service = window.data_service or DataAccessService(window.context.session)
        result_sets = data_service.get_result_sets(window.project_id)

        if result_sets and not window.controller.selection.result_set_id:
            window.controller.update_selection(result_set_id=result_sets[0].id)

        stories = data_service.get_stories(window.project_id)
        elements = data_service.get_elements(window.project_id)

        comparison_sets = data_service.get_comparison_sets(window.project_id)

        pushover_cases = {}
        logger.debug("Checking %s result sets for pushover analysis type", len(result_sets))
        pushover_result_set_ids = [
            rs.id for rs in result_sets if getattr(rs, 'analysis_type', None) == 'Pushover'
        ]
        if pushover_result_set_ids:
            pushover_cases = data_service.get_pushover_cases_by_result_sets(pushover_result_set_ids)
            for rs_id, cases in pushover_cases.items():
                logger.debug(
                    "Found %s pushover cases for result set %s",
                    len(cases) if cases else 0,
                    rs_id,
                )
                if cases:
                    window.controller.get_pushover_mapping(rs_id)

        available_result_types = window._get_available_result_types(result_sets)

        # Query time series load cases for each result set
        time_series_load_cases = data_service.get_time_series_load_cases(
            window.project_id,
            [rs.id for rs in result_sets],
        )

        window.browser.populate_tree(
            result_sets, stories, elements, available_result_types,
            comparison_sets, pushover_cases, time_series_load_cases
        )

        logger.info(
            "Loaded project: %s (%d stories, %d result sets, %d comparisons, %d elements)",
            window.project_name, len(stories), len(result_sets), len(comparison_sets), len(elements)
        )
    except Exception as e:
        logger.error("Error loading project data: %s", str(e))


__all__ = ["load_project_data"]
