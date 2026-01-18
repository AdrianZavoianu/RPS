"""Coverage for structured import logging helpers."""

import logging

from processing.import_logging import (
    log_import_complete,
    log_import_failure,
    log_phase_timings,
    log_import_start,
)


def test_log_import_start_sets_context(caplog):
    logger = logging.getLogger("rps.import.logging.start")
    with caplog.at_level(logging.INFO, logger=logger.name):
        log_import_start(
            logger=logger,
            project_name="Tower",
            result_set_name="DES",
            file_name="file.xlsx",
            result_types=["Drifts"],
        )

    record = caplog.records[-1]
    assert record.project == "Tower"
    assert record.result_set == "DES"
    assert record.file == "file.xlsx"
    assert record.event == "import.start"


def test_log_import_complete_includes_error_count(caplog):
    logger = logging.getLogger("rps.import.logging.complete")
    stats = {
        "drifts": 2,
        "accelerations": 0,
        "forces": 0,
        "displacements": 0,
        "soil_pressures": 0,
        "load_cases": 1,
        "stories": 2,
        "errors": ["bad"],
    }

    with caplog.at_level(logging.INFO, logger=logger.name):
        log_import_complete(
            logger=logger,
            project_name="Tower",
            result_set_name="DES",
            file_name="file.xlsx",
            stats=stats,
        )

    record = caplog.records[-1]
    assert record.event == "import.complete"
    assert record.errors == 1
    assert record.records["drifts"] == 2


def test_log_phase_timings_emits_debug(caplog):
    logger = logging.getLogger("rps.import.logging.phase")
    phases = [{"phase": "story_drifts", "duration_ms": 12}]

    with caplog.at_level(logging.DEBUG, logger=logger.name):
        log_phase_timings(
            logger=logger,
            project_name="Tower",
            result_set_name="DES",
            file_name="file.xlsx",
            phase_timings=phases,
        )

    assert any(rec.event == "import.phase" for rec in caplog.records)


def test_log_import_failure_records_exception(caplog):
    logger = logging.getLogger("rps.import.logging.failure")
    with caplog.at_level(logging.ERROR, logger=logger.name):
        log_import_failure(
            logger=logger,
            project_name="Tower",
            result_set_name="DES",
            file_name="file.xlsx",
            error=RuntimeError("boom"),
        )

    record = caplog.records[-1]
    assert record.event == "import.failure"
    assert "boom" in record.error
