"""Simple timing helpers for collecting phase durations with optional context."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Dict, List, Optional


class PhaseTimer:
    """Collects simple duration metrics for named phases."""

    def __init__(self, base_context: Optional[Dict[str, Any]] = None) -> None:
        self._base_context = base_context or {}
        self._entries: List[Dict[str, Any]] = []

    def as_list(self) -> List[Dict[str, Any]]:
        return list(self._entries)

    def measure(self, phase: str, extra: Optional[Dict[str, Any]] = None):
        """Context manager recording elapsed wall time for a phase."""

        class _TimerCtx:
            def __init__(self, outer: "PhaseTimer") -> None:
                self.outer = outer
                self.phase = phase
                self.extra = extra or {}
                self.start = perf_counter()

            def __enter__(self):
                return None

            def __exit__(self, exc_type, exc, tb):
                duration = perf_counter() - self.start
                entry: Dict[str, Any] = {"phase": self.phase, "duration": duration}
                entry.update(self.outer._base_context)
                if self.extra:
                    entry.update(self.extra)
                self.outer._entries.append(entry)
                return False

        return _TimerCtx(self)
