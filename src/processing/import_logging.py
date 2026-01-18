"""Structured logging helpers for import pipeline."""

from __future__ import annotations

import logging
from typing import Iterable, Mapping, Optional


def log_import_start(
    *,
    logger: logging.Logger,
    project_name: str,
    result_set_name: str,
    file_name: str,
    result_types: Optional[Iterable[str]],
) -> None:
    logger.info(
        "Structured import started",
        extra={
            "event": "import.start",
            "project": project_name,
            "result_set": result_set_name,
            "file": file_name,
            "result_types": list(result_types) if result_types else None,
        },
    )


def log_import_failure(
    *,
    logger: logging.Logger,
    project_name: str,
    result_set_name: str,
    file_name: str,
    error: Exception,
) -> None:
    logger.exception(
        "Import failed",
        extra={
            "event": "import.failure",
            "project": project_name,
            "result_set": result_set_name,
            "file": file_name,
            "error": str(error),
        },
    )


def log_phase_timings(
    *,
    logger: logging.Logger,
    project_name: str,
    result_set_name: str,
    file_name: str,
    phase_timings: Iterable[Mapping[str, object]],
) -> None:
    for entry in phase_timings:
        logger.debug(
            "Phase timing",
            extra={
                "event": "import.phase",
                "project": project_name,
                "result_set": result_set_name,
                "file": file_name,
                **entry,
            },
        )


def log_import_complete(
    *,
    logger: logging.Logger,
    project_name: str,
    result_set_name: str,
    file_name: str,
    stats: Mapping[str, object],
) -> None:
    logger.info(
        "Structured import finished",
        extra={
            "event": "import.complete",
            "project": project_name,
            "result_set": result_set_name,
            "file": file_name,
            "records": {k: stats.get(k) for k in ("drifts", "accelerations", "forces", "displacements", "soil_pressures")},
            "load_cases": stats.get("load_cases"),
            "stories": stats.get("stories"),
            "errors": len(stats.get("errors", [])) if isinstance(stats.get("errors"), list) else 0,
        },
    )
