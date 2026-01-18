"""Task runner helpers for structured imports.

These utilities centralize the logic for checking sheet availability,
running declarative import tasks, and merging per-task stats. They can be
shared by different importer entry points (single-file or folder-based)
to keep orchestration consistent.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Iterable, Optional, Sequence

from .import_tasks import ImportTask

logger = logging.getLogger(__name__)


def task_sheets_available(task: ImportTask, sheet_available: Callable[[str], bool]) -> bool:
    """Return True if the sheets required by this task are present."""
    if not task.sheets:
        return True

    checks = [sheet_available(name) for name in task.sheets]
    return all(checks) if task.require_all_sheets else any(checks)


def merge_task_stats(stats: Dict, task_stats: Optional[Dict]) -> None:
    """Merge per-task stats into the aggregate stats dict."""
    if not task_stats:
        return

    for key, value in task_stats.items():
        if key == "errors" and value:
            if isinstance(value, list):
                stats.setdefault("errors", []).extend(value)
            else:
                stats.setdefault("errors", []).append(value)
            continue

        if isinstance(value, (int, float)):
            stats[key] = stats.get(key, 0) + value
        else:
            stats[key] = value


def run_import_tasks(
    *,
    tasks: Sequence[ImportTask],
    should_import: Callable[[str], bool],
    sheet_available: Callable[[str], bool],
    get_handler: Callable[[str], Optional[Callable]],
    phase_timer,
    session,
    project_id: int,
    stats: Dict,
    file_name: str,
) -> None:
    """Execute import tasks with timing and sheet checks."""
    for task in tasks:
        if not should_import(task.label):
            continue
        if not task_sheets_available(task, sheet_available):
            logger.debug(
                "Skipping task: sheet missing",
                extra={"event": "import.task.skip", "task": task.label, "file": file_name},
            )
            continue

        handler = get_handler(task.handler)
        if handler is None:
            logger.warning(
                "Handler missing for task",
                extra={"event": "import.task.missing", "task": task.label, "handler": task.handler},
            )
            continue

        with phase_timer.measure(task.phase, {"task": task.label}):
            task_stats = handler(session, project_id)

        merge_task_stats(stats, task_stats)
