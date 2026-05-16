"""Archive module — store raw files with SHA256 fingerprints."""

import hashlib
import shutil
from pathlib import Path
from typing import Literal

from .utils import ensure_parent

_RAW_DIR = Path("raw")

DocType = Literal["standard", "regulation", "policy", "rule", "interpretation", "web"]


def _doc_type_to_subdir(doc_type: DocType) -> str:
    """Map document type to its raw subdirectory."""
    mapping = {
        "standard": "standards",
        "regulation": "regulations",
        "policy": "policies",
        "rule": "rules",
        "interpretation": "interpretations",
        "web": "web",
    }
    return mapping.get(doc_type, "web")


def compute_sha256(file_path: str | Path) -> str:
    """Compute SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def archive_pdf(
    source_path: str | Path,
    doc_type: DocType = "standard",
    slug: str = "",
) -> dict:
    """Archive a local PDF file into raw/standards/ (or appropriate subdir).

    Returns dict with raw_path, sha256, and subdir info.
    """
    source = Path(source_path)
    if not source.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    subdir = _doc_type_to_subdir(doc_type)
    target_dir = _RAW_DIR / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{slug}{source.suffix}" if slug else source.name
    target_path = target_dir / filename

    shutil.copy2(source, target_path)
    sha256 = compute_sha256(target_path)

    return {
        "raw_path": str(target_path),
        "sha256": sha256,
        "doc_type": doc_type,
        "subdir": subdir,
        "original_name": source.name,
    }


def archive_html(
    html_content: str,
    slug: str,
    source_url: str | None = None,
) -> dict:
    """Archive an HTML snapshot into raw/web/.

    Returns dict with raw_path, sha256, and source_url.
    """
    target_dir = _RAW_DIR / "web"
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{slug}.html"
    target_path = target_dir / filename

    with open(target_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    sha256 = compute_sha256(target_path)

    return {
        "raw_path": str(target_path),
        "sha256": sha256,
        "source_url": source_url,
    }
