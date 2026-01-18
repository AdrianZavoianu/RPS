"""Basic repository hygiene checks for unexpected top-level directories.

Run manually or in CI to catch stray artifacts (e.g., extracted paths or temp folders)
that clutter the workspace and confuse tooling.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, Set

ROOT = Path(__file__).resolve().parents[1]

# Directories we expect to live at the repository root.
DEFAULT_ALLOWED_DIRS: Set[str] = {
    ".claude",
    ".codex",
    ".cursor",
    ".git",
    ".pytest_cache",
    "Typical NLTHA DES",
    "Typical NLTHA MCE",
    "Typical Pushover Results",
    "Typical TH Data",
    "Old_scripts",
    "alembic",
    "build",
    "data",
    "dist",
    "docs",
    "gui",
    "resources",
    "scripts",
    "src",
    "tests",
}


def _load_extra_allowed() -> Set[str]:
    """Load optional extra allowed directories from env (comma-separated)."""
    raw = os.getenv("RPS_HYGIENE_ALLOW")
    if not raw:
        return set()
    return {name.strip() for name in raw.split(",") if name.strip()}


def _find_unexpected_dirs(allowed: Iterable[str]) -> list[Path]:
    allowed_set = set(allowed)
    unexpected: list[Path] = []
    for path in ROOT.iterdir():
        if path.is_dir() and path.name not in allowed_set:
            unexpected.append(path)
    return unexpected


def main() -> int:
    allowed_dirs = DEFAULT_ALLOWED_DIRS | _load_extra_allowed()
    unexpected = _find_unexpected_dirs(allowed_dirs)
    if unexpected:
        print("Unexpected top-level directories detected:")
        for path in unexpected:
            print(f" - {path.name!r} ({str(path)!r})")
        print("\nRemove these or add to RPS_HYGIENE_ALLOW if intentional.")
        return 1

    print("Repository hygiene check passed (no unexpected top-level directories).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
