"""Shared helpers for aggregating import statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional


@dataclass
class ImportStatsAggregator:
    """Accumulate per-file stats into a single dictionary."""

    base_stats: Dict[str, float] = field(default_factory=dict)

    def merge(self, stats: Optional[Dict[str, float]]) -> None:
        if not stats:
            return

        for key, value in stats.items():
            if key == "errors" or key == "phase_timings":
                continue  # handled elsewhere
            if isinstance(value, (int, float)):
                self.base_stats[key] = self.base_stats.get(key, 0) + value

    def extend_errors(self, errors: Iterable[str]) -> None:
        if not errors:
            return
        self.base_stats.setdefault("errors", [])
        self.base_stats["errors"].extend(errors)

    def as_dict(self) -> Dict[str, float]:
        return dict(self.base_stats)
