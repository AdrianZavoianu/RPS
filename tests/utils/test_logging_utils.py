"""Tests for structured logging utilities."""

from __future__ import annotations

import json
import logging

from utils import logging_utils


def test_setup_logging_writes_json(tmp_path, monkeypatch):
    log_file = tmp_path / "structured.log"
    monkeypatch.setattr(logging_utils, "_CONFIGURED", False)

    configured = logging_utils.setup_logging(log_file=log_file)
    assert configured == log_file

    logging.getLogger("tests.logging").info("hello world", extra={"event": "test"})

    contents = log_file.read_text().strip().splitlines()
    assert contents
    payload = json.loads(contents[-1])
    assert payload["message"] == "hello world"
    assert payload["event"] == "test"


def test_get_log_file_path_matches_setup(tmp_path, monkeypatch):
    log_file = tmp_path / "structured.log"
    monkeypatch.setattr(logging_utils, "_CONFIGURED", False)
    logging_utils.setup_logging(log_file=log_file)

    assert logging_utils.get_log_file_path() != log_file  # default path
