"""Development hot-reload runner for RPS."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Set, Tuple

from watchfiles import Change, DefaultFilter, run_process


def _print_changes(changes: Set[Tuple[Change, str]]) -> None:
    """Pretty-print a summary of the changes that triggered a reload."""
    if not changes:
        return
    print("\nReload triggered by:")
    for change, path in sorted(changes, key=lambda item: item[1]):
        print(f"  - {change.name.title():<7} {path}")
    print("-" * 50)


def main() -> None:
    """Run the application with auto-reload on file changes."""
    project_root = Path(__file__).parent.resolve()
    src_path = project_root / "src"

    os.environ.setdefault("RPS_ENV", "dev")

    # Ensure the command runs from project root
    os.chdir(project_root)

    ignore_dirs = ["data", "Old_scripts", ".git", "__pycache__", "tests"]
    ignore_patterns = ["*.pyc", "*.db", "*.db-journal"]
    watch_filter = DefaultFilter(
        ignore_dirs=ignore_dirs,
        ignore_entity_patterns=ignore_patterns,
    )

    print("RPS hot-reload development mode")
    print(f"Watching directory: {src_path}")
    print("Auto-reload on save (Ctrl+C to stop)")
    print("-" * 50)

    try:
        run_process(
            src_path,
            target="python src/main.py",
            target_type="command",
            watch_filter=watch_filter,
            grace_period=0.8,  # allow app to start before watching
            debounce=800,      # coalesce rapid save bursts (ms)
            callback=_print_changes,
        )
    except KeyboardInterrupt:
        print("\nHot-reload stopped")
        sys.exit(0)


if __name__ == "__main__":
    main()
