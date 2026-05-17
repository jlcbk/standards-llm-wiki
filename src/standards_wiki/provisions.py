"""Provision splitter — split candidate document text into provision candidates."""

import re
import sys
from pathlib import Path

from .candidates import load_metadata, load_candidate_document, write_jsonl

_CANDIDATES_DIR = Path("_candidates")

# Numeric labels: 1, 4.1, 4.1.1, 11.6, etc.
_NUMERIC_LABEL_RE = re.compile(
    r"^(?P<label>\d+(?:\.\d+)*)(?:\s+|[.．、]\s*)", re.MULTILINE
)

# Chinese article labels: 第一条, 第二条, etc.
_ARTICLE_LABEL_RE = re.compile(
    r"^(?P<label>第[一二三四五六七八九十百千零\d]+条)\s*", re.MULTILINE
)

# Annex labels: 附录 A, 附录A, Annex A, Annex 1, etc.
_ANNEX_LABEL_RE = re.compile(
    r"^(?P<label>(?:附录|Annex|Appendix)\s*[A-Za-z\d]+)\s*[\.:：]\s*", re.MULTILINE
)

# Combined pattern for detecting any provision heading
_PROVISION_LABEL_RES = [
    ("numeric", _NUMERIC_LABEL_RE),
    ("article", _ARTICLE_LABEL_RE),
    ("annex", _ANNEX_LABEL_RE),
]


def _make_provision_id(document_id: str, label: str) -> str:
    """Create a path-safe provision ID from document ID and label."""
    safe_label = label.strip().replace(" ", "-").replace(".", "-").lower()
    return f"{document_id}-{safe_label}"


def _classify_kind(label: str) -> str:
    """Classify provision kind from its label."""
    if re.match(r"第.+条", label):
        return "article"
    if re.match(r"(?:附录|Annex|Appendix)", label, re.IGNORECASE):
        return "annex"
    # Numeric labels with subsections
    parts = label.split(".")
    if len(parts) == 1:
        return "section"
    return "clause"


def _detect_labels(text: str) -> list[tuple[str, str, int, int]]:
    """Detect all provision labels in text.

    Returns:
        List of (label_type, label_text, start_position, content_start_position).
    """
    results = []
    for label_type, pattern in _PROVISION_LABEL_RES:
        for m in pattern.finditer(text):
            results.append((label_type, m.group("label"), m.start(), m.end()))

    results.sort(key=lambda x: x[2])
    return results


def split_provisions(
    text: str,
    document_id: str,
    source_text: str = "unknown",
    raw_path: str = "unknown",
    confidence: str = "medium",
) -> list[dict]:
    """Split document text into provision candidates.

    Args:
        text: Full document body text.
        document_id: Document identifier.
        source_text: Path to source text file.
        raw_path: Path to raw file.
        confidence: Default confidence level for extracted provisions.

    Returns:
        List of provision candidate dicts.
    """
    labels = _detect_labels(text)

    if not labels:
        return [_make_fallback_provision(document_id, text, source_text, raw_path)]

    provisions = []
    for i, (label_type, label, start, content_start) in enumerate(labels):
        # Content ends at next label or end of text
        if i + 1 < len(labels):
            content_end = labels[i + 1][2]
        else:
            content_end = len(text)

        raw_content = text[content_start:content_end].strip()
        title, content = _split_heading_tail(raw_content)
        if not content:
            continue

        provision_id = _make_provision_id(document_id, label)
        kind = _classify_kind(label)

        provisions.append({
            "document_id": document_id,
            "provision_id": provision_id,
            "label": label,
            "kind": kind,
            "title": title,
            "text": content,
            "locator": {"label": label},
            "source_text": source_text,
            "raw_path": raw_path,
            "confidence": confidence,
            "review_status": "machine_extracted",
            "evidence": {"quote": content},
        })

    # Keep IDs unique without losing the original source label.
    id_counts = {}
    for p in provisions:
        base_id = p["provision_id"]
        id_counts[base_id] = id_counts.get(base_id, 0) + 1
        if id_counts[base_id] > 1:
            p["provision_id"] = f"{base_id}-dup-{id_counts[base_id]}"
            p["confidence"] = "low"

    return provisions


def _make_fallback_provision(
    document_id: str, text: str, source_text: str, raw_path: str
) -> dict:
    """Create a low-confidence fallback provision when no labels are found."""
    snippet = text[:200].strip() if text else ""
    return {
        "document_id": document_id,
        "provision_id": f"{document_id}-fallback",
        "label": "fallback",
        "kind": "unknown",
        "title": "unknown",
        "text": text.strip(),
        "locator": {"label": "fallback"},
        "source_text": source_text,
        "raw_path": raw_path,
        "confidence": "low",
        "review_status": "machine_extracted",
        "evidence": {"quote": snippet},
    }


def _split_heading_tail(raw_content: str) -> tuple[str, str]:
    """Split same-line heading text from following body when both exist."""
    if "\n" not in raw_content:
        return "unknown", raw_content

    first_line, rest = raw_content.split("\n", 1)
    body = rest.strip()
    if body:
        return first_line.strip() or "unknown", body
    return "unknown", first_line.strip()


def split_provisions_from_candidates(
    document_id: str,
    candidates_dir: str | Path = _CANDIDATES_DIR,
) -> list[dict]:
    """Load candidate data and split into provisions.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory.

    Returns:
        List of provision candidate dicts.
    """
    candidates_dir = Path(candidates_dir)

    meta_path = candidates_dir / "metadata" / f"{document_id}.yaml"
    doc_path = candidates_dir / "documents" / f"{document_id}.md"

    metadata = load_metadata(meta_path)
    _frontmatter, body = load_candidate_document(doc_path)

    return split_provisions(
        text=body,
        document_id=document_id,
        source_text=metadata.get("source_text", "unknown"),
        raw_path=metadata.get("raw_path", "unknown"),
        confidence=metadata.get("confidence", "medium"),
    )


def main():
    """CLI entry point for split_provisions."""
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python tools/split_provisions.py <document_id>")
        sys.exit(1)

    document_id = sys.argv[1]

    try:
        provisions = split_provisions_from_candidates(document_id)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    output_path = Path("_candidates") / "provisions" / f"{document_id}.jsonl"
    write_jsonl(provisions, output_path)

    print(f"Document ID: {document_id}")
    print(f"Provisions: {len(provisions)}")
    print(f"Output: {output_path}")

    kinds = {}
    for p in provisions:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    for kind, count in sorted(kinds.items()):
        print(f"  {kind}: {count}")


if __name__ == "__main__":
    main()
