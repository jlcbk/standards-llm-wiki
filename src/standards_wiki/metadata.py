"""Metadata extraction — extract candidate metadata fields from source text and paths."""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classifier import classify_standard_type, classify_by_filename
from .utils import slugify


def extract_metadata(
    source_text: str,
    source_path: str | Path,
    document_type: str = "unknown",
    source_url: str | None = None,
    sha256: str | None = None,
) -> dict:
    """Extract candidate metadata fields from source text and path information.

    Args:
        source_text: The extracted text content from the source file.
        source_path: Path to the source file (raw or source text).
        document_type: Known document type (overrides detection if provided).
        source_url: Original URL if sourced from web.
        sha256: SHA256 hash of the raw file.

    Returns:
        dict with candidate metadata fields.
    """
    source_path = Path(source_path)

    # Extract title from first heading or fallback to filename
    title = _extract_title(source_text) or source_path.stem.replace("-", " ").title()

    # Extract standard ID
    standard_id = _extract_standard_id(source_text) or _extract_standard_id_from_path(source_path)

    # Classify document type
    if document_type == "unknown":
        document_type = classify_standard_type(title)
        if document_type == "unknown" and standard_id:
            document_type = classify_standard_type(standard_id)

    # Extract dates
    release_date = _extract_date(source_text, patterns=_RELEASE_DATE_PATTERNS)
    effective_date = _extract_date(source_text, patterns=_EFFECTIVE_DATE_PATTERNS)

    # Extract publisher/issuer
    publisher = _extract_publisher(source_text)

    return {
        "title": title,
        "document_type": document_type,
        "standard_id": standard_id,
        "publisher": publisher,
        "release_date": release_date,
        "effective_date": effective_date,
        "source_url": source_url,
        "raw_path": str(source_path),
        "source_text": None,  # To be filled by caller
        "sha256": sha256,
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "confidence": "low",  # Default until reviewed
        "review_status": "draft",
    }


# Date extraction patterns
_RELEASE_DATE_PATTERNS = [
    r"(?:发布|发布日期|release(?:d)?|issued|公布)\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*(?:发布|发布日期|release)",
    r"(\d{4}\d{2}\d{2})\s*(?:发布|发布日期|release)",
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}).*?(?:发布|发布日期|release)",
    r"(?:发布|发布日期|release(?:d)?|issued|公布)\s*[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日)",
]

_EFFECTIVE_DATE_PATTERNS = [
    r"(?:实施|实施日期|effective(?: date)?|生效|施行)\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})",
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})\s*(?:实施|实施日期|effective|生效|施行)",
    r"(\d{4}\d{2}\d{2})\s*(?:实施|实施日期|effective|生效|施行)",
    r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}).*?(?:实施|实施日期|effective|生效|施行)",
    r"(?:实施|实施日期|effective(?: date)?|生效|施行)\s*[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日)",
]


def _extract_title(text: str) -> str | None:
    """Extract title from the first heading in the text."""
    # Look for # heading (Markdown)
    match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Look for HTML <h1>
    match = re.search(r"<h1[^>]*>(.+?)</h1>", text, re.IGNORECASE | re.DOTALL)
    if match:
        return match.group(1).strip()

    return None


def _extract_standard_id(text: str) -> str | None:
    """Extract standard ID from text (e.g., GB 7258-2017, ISO 26262:2018)."""
    # GB standards
    match = re.search(r"(GB\s*/?\s*T?\s*\d+(?:\.\d+)?[-:]\d{4})", text, re.IGNORECASE)
    if match:
        return match.group(1).upper().replace(" ", "")

    # ISO standards
    match = re.search(r"(ISO\s*\d+(?:\:\d{4})?)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper().replace(" ", "")

    # IEC standards
    match = re.search(r"(IEC\s*\d+(?:[-:]\d{4})?)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper().replace(" ", "")

    # ECE regulations
    match = re.search(r"(ECE\s*R\s*\d+(?:\s*Rev\.\d+)?)", text, re.IGNORECASE)
    if match:
        return match.group(1).upper().replace(" ", "")

    return None


def _extract_standard_id_from_path(path: Path) -> str | None:
    """Try to extract standard ID from the filename."""
    filename = path.stem
    # Look for patterns like gb-7258-2017, iso-26262-2018
    match = re.search(r"([a-z]+[-/]\d+(?:[-/]\d{4})?)", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()
    return None


def _extract_date(text: str, patterns: list[str]) -> str | None:
    """Extract a date from text using the given patterns."""
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            date_str = match.group(1)
            # Normalize date format
            return _normalize_date(date_str)
    return None


def _normalize_date(date_str: str) -> str:
    """Normalize date string to YYYY-MM-DD format."""
    # Handle YYYY-MM-DD or YYYY/MM/DD
    match = re.match(r"(\d{4})[-/](\d{1,2})[-/](\d{1,2})", date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    # Handle compact YYYYMMDD
    match = re.match(r"(\d{4})(\d{2})(\d{2})", date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month}-{day}"

    # Handle YYYY年MM月DD日
    match = re.match(r"(\d{4})年(\d{1,2})月(\d{1,2})日", date_str)
    if match:
        year, month, day = match.groups()
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"

    return date_str


def _extract_publisher(text: str) -> str | None:
    """Extract publisher/issuer from text."""
    # Chinese publishers - look for "发布部门：XXX" pattern
    match = re.search(r"发布部门\s*[:：]\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Look for known Chinese government bodies
    cn_bodies = [
        r"(?:中华人民共和国)?(?:工信部|市场监管总局|国家标准化管理委员会|国家发展和改革委员会)",
    ]
    for pattern in cn_bodies:
        match = re.search(pattern, text)
        if match:
            return match.group(0)

    # English publishers
    match = re.search(r"(?:published by|issued by)\s*:?\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Standalone organization names
    match = re.search(r"\b(ISO|IEC|UNECE|SAC|SAE)\b", text)
    if match:
        return match.group(1)

    return None
