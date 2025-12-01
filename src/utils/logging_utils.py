"""Centralized structured logging utilities for RPS."""

from __future__ import annotations

import json
import logging
from logging import Handler
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_LOG_FILE = LOG_DIR / "rps.log"

_CONFIGURED = False


class StructuredFormatter(logging.Formatter):
    """Emit log records as single-line JSON for easier parsing."""

    _BASE_FIELDS = {
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        for key, value in record.__dict__.items():
            if key in self._BASE_FIELDS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        try:
            return json.dumps(payload, default=str)
        except TypeError:
            sanitized = {k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
                         for k, v in payload.items()}
            return json.dumps(sanitized)


def _build_handlers(log_file: Path) -> list[Handler]:
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(StructuredFormatter())

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    )

    return [file_handler, console_handler]


def setup_logging(level: int = logging.INFO, log_file: Optional[Path] = None) -> Path:
    """Configure root logging once and return the log file path."""

    global _CONFIGURED

    if _CONFIGURED:
        return DEFAULT_LOG_FILE if log_file is None else log_file

    target_log_file = log_file or DEFAULT_LOG_FILE
    target_log_file.parent.mkdir(parents=True, exist_ok=True)

    handlers = _build_handlers(target_log_file)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    for handler in handlers:
        root_logger.addHandler(handler)

    _CONFIGURED = True
    return target_log_file


def get_log_file_path() -> Path:
    """Return the path to the primary log file."""

    return DEFAULT_LOG_FILE
