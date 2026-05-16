"""Utility helpers for path handling, slugs, and timestamps."""

import re
from datetime import datetime, timezone
from pathlib import Path


def slugify(text: str) -> str:
    """Convert text to a stable lowercase slug for safe filenames.

    Keeps ASCII letters, digits, Chinese characters, and hyphens.
    Replaces other characters with hyphens, collapses multiple hyphens,
    and strips leading/trailing hyphens.
    """
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\-]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    slug = slug.strip("-")
    return slug


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string ending with 'Z'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_parent(path: str) -> None:
    """Create parent directories for the given path if they don't exist."""
    parent = Path(path).parent
    if parent != Path("."):
        parent.mkdir(parents=True, exist_ok=True)
