"""Environment helpers for runtime configuration."""

import os
from functools import lru_cache


@lru_cache
def is_dev_mode() -> bool:
    """Return True when the app runs in development mode."""
    value = os.environ.get("RPS_ENV") or os.environ.get("RPS_DEV_MODE")
    if not value:
        return False
    normalized = value.strip().lower()
    return normalized in {"dev", "development", "1", "true", "yes"}


__all__ = ["is_dev_mode"]
