"""Tests for Diagnostics dialog helpers."""

from __future__ import annotations

from gui.diagnostics_dialog import read_log_tail


def test_read_log_tail_returns_full_file_when_small(tmp_path):
    log_file = tmp_path / "log.txt"
    log_file.write_text("line1\nline2", encoding="utf-8")

    text = read_log_tail(log_file, max_bytes=100)

    assert "line1" in text
    assert "line2" in text


def test_read_log_tail_truncates_to_tail(tmp_path):
    log_file = tmp_path / "log.txt"
    log_file.write_text("abcdefg", encoding="utf-8")

    text = read_log_tail(log_file, max_bytes=3)

    assert text == "efg"
