"""Tests for Excel parser."""

import pytest
from pathlib import Path
from processing.excel_parser import ExcelParser

SAMPLE_ROOT = Path("test_input")


def _get_sample_excel_files() -> list[Path]:
    if not SAMPLE_ROOT.exists():
        return []
    files = list(SAMPLE_ROOT.rglob("*.xlsx"))
    return sorted(files, key=lambda path: path.stat().st_size)


def test_excel_parser_init():
    """Test ExcelParser initialization with non-existent file."""
    with pytest.raises(FileNotFoundError):
        parser = ExcelParser("nonexistent.xlsx")


def test_get_available_sheets():
    """Test getting available sheets from sample Excel file."""
    # Find a sample Excel file
    sample_files = _get_sample_excel_files()

    if not sample_files:
        pytest.skip("No sample Excel files found in 'test_input' directory")

    parser = ExcelParser(str(sample_files[0]))
    sheets = parser.get_available_sheets()

    assert isinstance(sheets, list)
    assert len(sheets) > 0


def test_validate_sheet_exists():
    """Test sheet validation."""
    sample_files = _get_sample_excel_files()

    if not sample_files:
        pytest.skip("No sample Excel files found in 'test_input' directory")

    parser = ExcelParser(str(sample_files[0]))
    sheets = parser.get_available_sheets()

    # First sheet should exist
    if sheets:
        assert parser.validate_sheet_exists(sheets[0]) is True

    # Non-existent sheet should return False
    assert parser.validate_sheet_exists("NonExistentSheet12345") is False
