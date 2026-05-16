"""Document classifier — deterministic rules for document type and standard family."""

import re
from pathlib import Path
from typing import Literal

DocStandardType = Literal[
    "gb",
    "gb-t",
    "gb-z",
    "iso",
    "iec",
    "sae",
    "ece",
    "unece",
    "cn-policy",
    "cn-administrative",
    "unknown",
]


def classify_standard_type(text: str) -> DocStandardType:
    """Classify document type from title or filename text.

    Uses deterministic pattern matching (no LLM).
    Priority: more specific patterns first.
    """
    upper = text.upper()

    # GB/T (recommended standard)
    if re.search(r"GB\s*/\s*T", upper):
        return "gb-t"

    # GB/Z (guideline)
    if re.search(r"GB\s*/\s*Z", upper):
        return "gb-z"

    # GB (mandatory national standard)
    if re.search(r"\bGB\b", upper):
        return "gb"

    # ISO
    if re.search(r"\bISO\b", upper):
        return "iso"

    # IEC
    if re.search(r"\bIEC\b", upper):
        return "iec"

    # SAE
    if re.search(r"\bSAE\b", upper):
        return "sae"

    # UNECE / UN ECE / UN R
    if re.search(r"UNECE|UN\s*ECE|UN\s*R\s*\d", upper):
        return "unece"

    # ECE R (ECE regulation)
    if re.search(r"ECE\s*R\s*\d", upper):
        return "ece"

    return "unknown"


def classify_by_filename(filename: str) -> DocStandardType:
    """Classify document type from filename (slug or original name)."""
    return classify_standard_type(filename)


def classify_by_path(path: str | Path) -> DocStandardType:
    """Classify document type from file path."""
    return classify_standard_type(str(path))
