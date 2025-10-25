"""Utilities for generating filesystem-safe slugs."""

import re
from typing import Optional

SLUG_INVALID = re.compile(r"[^a-z0-9]+")


def slugify(text: str, default: Optional[str] = None) -> str:
    """Convert text to a lowercase slug composed of a-z, 0-9 and hyphen."""
    text = (text or "").strip().lower()
    if not text:
        if default:
            text = default.strip().lower()
        else:
            raise ValueError("Cannot slugify empty text")

    text = SLUG_INVALID.sub("-", text).strip("-")
    return text or (default or "project")
