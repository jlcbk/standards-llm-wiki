"""Deterministic candidate evaluation — run checks against extracted data."""

import json
from pathlib import Path

# ---------------------------------------------------------------------------
# Category inference for backward compatibility (missing category field)
# ---------------------------------------------------------------------------
_TYPE_CATEGORY_MAP = {
    "document_id_exists": "missed_document",
    "provision_label_exists": "missed_provision",
    "keyword_search": "missed_provision",
    "requirement_modality_exists": "missed_requirement",
    "evidence_quote_exists": "citation_missing",
    "metadata_field_equals": "metadata_mismatch",
    "topic_tag_exists": "topic_mismatch",
}

_VALID_SEVERITIES = {"info", "warn", "error"}


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
            Optional fields: category, severity, notes.
        context: Dict with documents, provisions, requirements, and/or
            topic_tags data.

    Returns:
        Result dict with total, passed, failed, and failures list.
        Each failure contains id, type, category, severity, reason.
    """
    documents = context.get("documents", [])
    provisions = context.get("provisions", [])
    requirements = context.get("requirements", [])
    topic_tags = context.get("topic_tags", {})

    failures = []
    for check in checks:
        check_id = check.get("id", "")
        check_type = check.get("type", "")
        expected = check.get("expected")

        # Lightweight validation
        if not check_id:
            failures.append({
                "id": "",
                "type": check_type or "",
                "category": "missed_document",
                "severity": "error",
                "reason": "Missing id in check",
            })
            continue
        if not check_type:
            failures.append({
                "id": check_id,
                "type": "",
                "category": "missed_document",
                "severity": "error",
                "reason": "Missing type in check",
            })
            continue
        if expected is None:
            failures.append({
                "id": check_id,
                "type": check_type,
                "category": _infer_category(check_type),
                "severity": "error",
                "reason": "Missing expected in check",
            })
            continue

        passed, reason = _run_single(
            check_type, expected, documents, provisions, requirements, topic_tags,
        )
        if not passed:
            # Infer category/severity for backward compat
            category = check.get("category") or _infer_category(check_type)
            severity = check.get("severity", "error")
            if severity not in _VALID_SEVERITIES:
                severity = "error"
            failures.append({
                "id": check_id,
                "type": check_type,
                "category": category,
                "severity": severity,
                "reason": reason,
            })

    return {
        "total": len(checks),
        "passed": len(checks) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }


def _infer_category(check_type: str) -> str:
    """Infer failure category from check type."""
    return _TYPE_CATEGORY_MAP.get(check_type, "missed_document")


def _run_single(check_type, expected, documents, provisions, requirements, topic_tags):
    """Execute a single check. Returns (passed, reason)."""
    if check_type == "document_id_exists":
        return _check_document_id(expected, documents, provisions, requirements)
    if check_type == "provision_label_exists":
        return _check_provision_label(expected, provisions)
    if check_type == "keyword_search":
        return _check_keyword(expected, provisions, requirements)
    if check_type == "requirement_modality_exists":
        return _check_requirement_modality(expected, requirements)
    if check_type == "evidence_quote_exists":
        return _check_evidence_quote(expected, provisions, requirements)
    if check_type == "metadata_field_equals":
        return _check_metadata_field(expected, documents)
    if check_type == "topic_tag_exists":
        return _check_topic_tag(expected, topic_tags)
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


def _check_requirement_modality(expected, requirements):
    """Check that at least one requirement has the specified modality."""
    doc_id = expected.get("document_id", "")
    modality = expected.get("modality", "")

    if not doc_id:
        return False, "Missing document_id in expected"
    if not modality:
        return False, "Missing modality in expected"

    for r in requirements:
        if r.get("document_id") == doc_id and r.get("modality") == modality:
            return True, ""

    return False, f"No requirement with document_id='{doc_id}' modality='{modality}'"


def _check_evidence_quote(expected, provisions, requirements):
    """Check that a provision/requirement contains an evidence quote substring.

    expected supports:
      - document_id (required)
      - quote_substring (required)
      - label (optional, matches provision label)
      - id (optional, matches provision_id/requirement_id)
    """
    doc_id = expected.get("document_id", "")
    quote_sub = expected.get("quote_substring", "")

    if not doc_id:
        return False, "Missing document_id in expected"
    if not quote_sub:
        return False, "Missing quote_substring in expected"

    # Search in provisions
    for p in provisions:
        if p.get("document_id") != doc_id:
            continue
        # If label filter given, must match
        if "label" in expected and p.get("label") != expected["label"]:
            continue
        # If id filter given, must match provision_id or id
        if "id" in expected:
            if p.get("provision_id") != expected["id"] and p.get("id") != expected["id"]:
                continue
        if _record_has_quote_substring(p, quote_sub):
            return True, ""

    # Search in requirements
    for r in requirements:
        if r.get("document_id") != doc_id:
            continue
        # If id filter given, must match requirement_id or id
        if "id" in expected:
            if r.get("requirement_id") != expected["id"] and r.get("id") != expected["id"]:
                continue
        # Label filter is less common for requirements but check provision_id label portion
        if "label" in expected:
            # Match against provision_id label portion if available
            prov_id = r.get("provision_id", "")
            if not prov_id.endswith("-" + expected["label"]) and expected["label"] not in prov_id:
                continue
        if _record_has_quote_substring(r, quote_sub):
            return True, ""

    return False, (
        f"No evidence containing '{quote_sub}' for document_id='{doc_id}'"
    )


def _record_has_quote_substring(record, substring):
    """Check if a record's evidence.quote, text, or title contains substring."""
    # Check text and title
    for field in ("text", "title"):
        value = record.get(field, "")
        if value and substring in value:
            return True

    # Check evidence
    evidence = record.get("evidence")
    if isinstance(evidence, dict):
        quote = evidence.get("quote", "")
        if quote and substring in quote:
            return True
    elif isinstance(evidence, list):
        for item in evidence:
            if isinstance(item, dict):
                quote = item.get("quote", "")
                if quote and substring in quote:
                    return True

    return False


def _check_metadata_field(expected, documents):
    """Check that a document's metadata field equals expected value."""
    doc_id = expected.get("document_id", "")
    field = expected.get("field", "")
    value = expected.get("value")

    if not doc_id:
        return False, "Missing document_id in expected"
    if not field:
        return False, "Missing field in expected"
    if "value" not in expected:
        return False, "Missing value in expected"

    for doc in documents:
        if doc.get("document_id") == doc_id or doc.get("standard_id") == doc_id:
            actual = doc.get(field)
            if actual == value:
                return True, ""
            return False, (
                f"Metadata field '{field}' is '{actual}', expected '{value}'"
            )

    return False, f"Document '{doc_id}' not found in context"


def _check_topic_tag(expected, topic_tags):
    """Check that a topic tag exists in topic-tags data.

    Searches through provisions and requirements in topic_tags for the
    expected topic.
    """
    doc_id = expected.get("document_id", "")
    topic = expected.get("topic", "")

    if not doc_id:
        return False, "Missing document_id in expected"
    if not topic:
        return False, "Missing topic in expected"

    # Verify document_id matches
    if topic_tags.get("document_id") != doc_id:
        return False, f"Topic tags for document_id='{doc_id}' not found"

    # Search provisions topics
    for item in topic_tags.get("provisions", []):
        if topic in item.get("topics", []):
            return True, ""

    # Search requirements topics
    for item in topic_tags.get("requirements", []):
        if topic in item.get("topics", []):
            return True, ""

    return False, f"Topic '{topic}' not found in topic-tags for '{doc_id}'"
