"""Deterministic candidate evaluation — run checks against extracted data."""

import json
from pathlib import Path


def load_checks(path: str | Path) -> list[dict]:
    """Load check definitions from a JSONL file.

    Each line must contain at least id, type, and expected fields.

    Args:
        path: Path to the checks JSONL file.

    Returns:
        List of check dicts.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Checks file not found: {path}")

    checks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            checks.append(record)
    return checks


def run_checks(checks: list[dict], context: dict) -> dict:
    """Run checks against extracted data context.

    Args:
        checks: List of check dicts, each with id, type, expected.
        context: Dict with documents, provisions, and/or requirements lists.

    Returns:
        Result dict with total, passed, failed, and failures list.
    """
    documents = context.get("documents", [])
    provisions = context.get("provisions", [])
    requirements = context.get("requirements", [])

    failures = []
    for check in checks:
        check_id = check["id"]
        check_type = check["type"]
        expected = check["expected"]
        passed, reason = _run_single(check_type, expected, documents, provisions, requirements)
        if not passed:
            failures.append({"id": check_id, "type": check_type, "reason": reason})

    return {
        "total": len(checks),
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }


def _run_single(check_type, expected, documents, provisions, requirements):
    """Execute a single check. Returns (passed, reason)."""
    if check_type == "document_id_exists":
        return _check_document_id(expected, documents, provisions, requirements)
    if check_type == "provision_label_exists":
        return _check_provision_label(expected, provisions)
    if check_type == "keyword_search":
        return _check_keyword(expected, provisions, requirements)
    return False, f"Unknown check type: {check_type}"


def _check_document_id(expected, documents, provisions, requirements):
    """Check that a document_id exists in context data."""
    target_id = expected if isinstance(expected, str) else expected.get("document_id", "")
    if not target_id:
        return False, "Missing document_id in expected"

    for records in (documents, provisions, requirements):
        for rec in records:
            if rec.get("document_id") == target_id:
                return True, ""

    return False, f"document_id '{target_id}' not found"


def _check_provision_label(expected, provisions):
    """Check that a provision with given document_id and label exists."""
    doc_id = expected.get("document_id", "")
    label = expected.get("label", "")

    if not doc_id:
        return False, "Missing document_id in expected"
    if not label:
        return False, "Missing label in expected"

    for p in provisions:
        if p.get("document_id") == doc_id and p.get("label") == label:
            return True, ""

    return False, f"No provision with document_id='{doc_id}' label='{label}'"


def _check_keyword(expected, provisions, requirements):
    """Check keyword hit count across provisions and requirements."""
    keyword = expected.get("keyword", "")
    min_count = expected.get("min_count", 0)

    if not keyword:
        return False, "Missing keyword in expected"

    hits = 0
    for p in provisions:
        hits += _count_keyword_hits(p, keyword)
    for r in requirements:
        hits += _count_keyword_hits(r, keyword)

    if hits >= min_count:
        return True, ""

    return False, f"keyword '{keyword}' found {hits} times, need >= {min_count}"


def _count_keyword_hits(record, keyword):
    """Count keyword occurrences in text, title, and evidence.quote fields."""
    count = 0
    for field in ("text", "title"):
        value = record.get(field, "")
        if value:
            count += value.count(keyword)

    evidence = record.get("evidence")
    if isinstance(evidence, dict):
        quote = evidence.get("quote", "")
        if quote:
            count += quote.count(keyword)
    elif isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                quote = item.get("quote", "")
                if quote:
                    count += quote.count(keyword)

    return count
