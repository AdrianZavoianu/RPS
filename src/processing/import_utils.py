"""Shared parsing and validation helpers for importers."""

from __future__ import annotations

from typing import Callable, Iterable


def sheet_available(sheet_name: str, validator: Callable[[str], bool]) -> bool:
    """Return True if the given sheet is available via validator."""
    return validator(sheet_name)


def any_sheet_available(sheet_names: Iterable[str], validator: Callable[[str], bool]) -> bool:
    """Return True if any of the given sheet names are available."""
    return any(validator(name) for name in sheet_names)


def all_sheets_available(sheet_names: Iterable[str], validator: Callable[[str], bool]) -> bool:
    """Return True if all of the given sheet names are available."""
    return all(validator(name) for name in sheet_names)


def require_sheets(
    sheet_names: Iterable[str],
    validator: Callable[[str], bool],
    *,
    require_all: bool = True,
) -> bool:
    """Validate required sheets exist, honoring require_all flag."""
    return all_sheets_available(sheet_names, validator) if require_all else any_sheet_available(sheet_names, validator)
