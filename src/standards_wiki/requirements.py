"""Requirement extractor — rule-based modality detector for provision text."""

import re
import sys
from pathlib import Path

from .candidates import read_jsonl, write_jsonl

_CANDIDATES_DIR = Path("_candidates")

# Chinese modality signals (order matters: check longer/negative patterns first)
_CN_MODALITY_MAP = [
    (re.compile(r"不得|禁止|不应|不可|严禁"), "must_not"),
    (re.compile(r"必须|应当|须要|须"), "must"),
    (re.compile(r"应"), "must"),
    (re.compile(r"宜|建议"), "should"),
    (re.compile(r"可[以以]?|允许"), "may"),
    (re.compile(r"是指|定义为|是指下列"), "define"),
]

# English modality signals
_EN_MODALITY_MAP = [
    (re.compile(r"shall\s+not|must\s+not|prohibited|is\s+not\s+(?:allowed|permitted)", re.IGNORECASE), "must_not"),
    (re.compile(r"shall|must|is\s+required\s+to", re.IGNORECASE), "must"),
    (re.compile(r"should|recommended|it\s+is\s+recommended", re.IGNORECASE), "should"),
    (re.compile(r"may|permitted|can|it\s+is\s+permitted", re.IGNORECASE), "may"),
    (re.compile(r"means|refers\s+to|is\s+defined\s+as", re.IGNORECASE), "define"),
]


def detect_modality(text: str) -> str:
    """Detect the strongest modality signal in text.

    Checks Chinese signals first, then English.

    Args:
        text: Provision text to analyze.

    Returns:
        Modality string: must, must_not, should, may, define, or unknown.
    """
    for pattern, modality in _CN_MODALITY_MAP:
        if pattern.search(text):
            return modality

    for pattern, modality in _EN_MODALITY_MAP:
        if pattern.search(text):
            return modality

    return "unknown"


def extract_requirements_from_provision(
    provision: dict,
    req_counter: int = 1,
) -> list[dict]:
    """Extract requirement candidates from a single provision.

    Args:
        provision: Provision candidate dict.
        req_counter: Starting counter for requirement IDs within this provision.

    Returns:
        List of requirement candidate dicts. May be empty if no modality detected.
    """
    text = provision.get("text", "")
    document_id = provision.get("document_id", "unknown")
    provision_id = provision.get("provision_id", "unknown")

    modality = detect_modality(text)

    # If no modality detected and no explicit request for unknown, skip
    if modality == "unknown":
        return []

    requirement_id = f"{provision_id}-r{req_counter}"

    source_text = provision.get("source_text", "unknown")
    raw_path = provision.get("raw_path", "unknown")
    locator = provision.get("locator", {})
    evidence_quote = provision.get("evidence", {}).get("quote", text[:200].strip())

    return [{
        "requirement_id": requirement_id,
        "document_id": document_id,
        "provision_id": provision_id,
        "modality": modality,
        "subject": "unknown",
        "action": "unknown",
        "object": "unknown",
        "condition": "unknown",
        "exception": "unknown",
        "evidence": {
            "quote": evidence_quote,
            "source_text": source_text,
            "raw_path": raw_path,
            "locator": locator,
        },
        "confidence": provision.get("confidence", "low"),
        "review_status": "machine_extracted",
    }]


def extract_requirements_from_provisions(
    provisions: list[dict],
) -> list[dict]:
    """Extract requirements from a list of provision candidates.

    Args:
        provisions: List of provision candidate dicts.

    Returns:
        List of requirement candidate dicts.
    """
    all_requirements = []
    req_counter = 1

    for provision in provisions:
        reqs = extract_requirements_from_provision(provision, req_counter=req_counter)
        all_requirements.extend(reqs)
        req_counter += len(reqs)

    return all_requirements


def extract_requirements_from_jsonl(
    document_id: str,
    candidates_dir: str | Path = _CANDIDATES_DIR,
) -> list[dict]:
    """Load provisions JSONL and extract requirements.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory.

    Returns:
        List of requirement candidate dicts.
    """
    candidates_dir = Path(candidates_dir)
    provisions_path = candidates_dir / "provisions" / f"{document_id}.jsonl"

    provisions = read_jsonl(provisions_path)
    return extract_requirements_from_provisions(provisions)


def main():
    """CLI entry point for extract_requirements."""
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python tools/extract_requirements.py <document_id>")
        sys.exit(1)

    document_id = sys.argv[1]

    try:
        requirements = extract_requirements_from_jsonl(document_id)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    output_path = Path("_candidates") / "requirements" / f"{document_id}.jsonl"
    write_jsonl(requirements, output_path)

    print(f"Document ID: {document_id}")
    print(f"Requirements: {len(requirements)}")
    print(f"Output: {output_path}")

    modalities = {}
    for r in requirements:
        m = r["modality"]
        modalities[m] = modalities.get(m, 0) + 1
    for modality, count in sorted(modalities.items()):
        print(f"  {modality}: {count}")


if __name__ == "__main__":
    main()
