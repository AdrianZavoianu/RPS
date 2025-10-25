"""Shared helpers for importing directional result data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from sqlalchemy.orm import Session

from database.repository import LoadCaseRepository, StoryRepository


@dataclass
class ResultImportHelper:
    """Caches story/load-case lookups while preserving Excel-defined ordering."""

    session: Session
    project_id: int
    stories: Iterable[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.story_repo = StoryRepository(self.session)
        self.load_case_repo = LoadCaseRepository(self.session)
        self._story_cache: Dict[str, object] = {}
        self._load_case_cache: Dict[str, object] = {}
        self._story_order = {
            name: idx for idx, name in enumerate(self.stories or [])
        }

    def get_story(self, name: str):
        """Return (and cache) a story model, applying Excel sort order."""
        if not name:
            raise ValueError("Row is missing a Story value")

        cached = self._story_cache.get(name)
        if cached:
            return cached

        sort_order = self._story_order.get(name)
        story = self.story_repo.get_or_create(
            project_id=self.project_id,
            name=name,
            sort_order=sort_order,
        )
        self._story_cache[name] = story
        return story

    def get_load_case(self, name: str, case_type: Optional[str] = None):
        """Return (and cache) a load case model."""
        if not name:
            raise ValueError("Row is missing a LoadCase value")

        cached = self._load_case_cache.get(name)
        if cached:
            return cached

        load_case = self.load_case_repo.get_or_create(
            project_id=self.project_id,
            name=name,
            case_type=case_type,
        )
        self._load_case_cache[name] = load_case
        return load_case
