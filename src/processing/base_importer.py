"""Shared helpers for importers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set

from sqlalchemy.orm import Session


class BaseImporter:
    """Provides normalized result type filtering and session management."""

    def __init__(
        self,
        *,
        result_types: Optional[Iterable[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
    ) -> None:
        if session_factory is None:
            raise ValueError(f"{self.__class__.__name__} requires a session_factory")

        self._session_factory = session_factory
        self.result_types: Optional[Set[str]] = self._normalize_result_types(result_types)

    @staticmethod
    def _normalize_result_types(result_types: Optional[Iterable[str]]) -> Optional[Set[str]]:
        if not result_types:
            return None

        normalized = {
            label.strip().lower()
            for label in result_types
            if label and label.strip()
        }
        return normalized or None

    def _should_import(self, label: str) -> bool:
        if not self.result_types:
            return True
        return label.strip().lower() in self.result_types

    @contextmanager
    def session_scope(self):
        """Context manager that manages commit/rollback for a session."""
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class BaseFolderImporter(BaseImporter):
    """Adds folder scanning and progress reporting helpers."""

    def __init__(
        self,
        *,
        folder_path: str,
        result_types: Optional[Iterable[str]] = None,
        session_factory: Optional[Callable[[], Session]] = None,
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> None:
        super().__init__(result_types=result_types, session_factory=session_factory)

        self.folder_path = Path(folder_path)
        if not self.folder_path.exists() or not self.folder_path.is_dir():
            raise ValueError(f"Invalid folder path: {folder_path}")

        self.progress_callback = progress_callback
        self.excel_files = self._find_excel_files()

    def _find_excel_files(self) -> List[Path]:
        files: List[Path] = []
        for pattern in ("*.xlsx", "*.xls"):
            files.extend(self.folder_path.glob(pattern))
        return sorted(f for f in files if not f.name.startswith("~$"))

    def _report_progress(self, message: str, current: int, total: int) -> None:
        if self.progress_callback:
            self.progress_callback(message, current, total)
