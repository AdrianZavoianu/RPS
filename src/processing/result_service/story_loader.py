from __future__ import annotations

from typing import Dict, List, Tuple


class StoryProvider:
    """Caches story metadata for reuse across services."""

    def __init__(self, story_repo, project_id: int):
        self._story_repo = story_repo
        self._project_id = project_id
        self._stories: List[object] = []
        self._story_index: Dict[int, Tuple[int, str]] = {}
        self._loaded = False

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        stories = self._story_repo.get_by_project(self._project_id)
        self._stories = stories
        self._story_index = {
            story.id: (idx, story.name or "") for idx, story in enumerate(stories)
        }
        self._loaded = True

    @property
    def stories(self) -> List[object]:
        self.ensure_loaded()
        return self._stories

    @property
    def story_index(self) -> Dict[int, Tuple[int, str]]:
        self.ensure_loaded()
        return self._story_index
