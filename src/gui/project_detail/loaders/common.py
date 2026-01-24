"""Shared helpers for project detail view loaders."""

from __future__ import annotations

from typing import TYPE_CHECKING

from config.analysis_types import AnalysisType

if TYPE_CHECKING:
    from ..window import ProjectDetailWindow


def _is_pushover_context(window: "ProjectDetailWindow") -> bool:
    """Check if the current analysis context is Pushover."""
    return window.controller.get_active_context() == AnalysisType.PUSHOVER
