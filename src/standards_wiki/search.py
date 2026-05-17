"""Deterministic local search over collected records."""

from dataclasses import dataclass

from .indexer import IndexResult, collect_records

_CANDIDATES_DIR = "_candidates"
_DRAFTS_DIR = "documents/drafts"


@dataclass
class SearchResult:
    """A single search hit."""

    record_type: str  # document, provision, requirement
    record_id: str
    title: str
    review_status: str
    source: str
    matched_field: str
    matched_text: str


def search(
    query: str,
    candidates_dir: str = _CANDIDATES_DIR,
    drafts_dir: str = _DRAFTS_DIR,
    limit: int = 20,
) -> list[SearchResult]:
    """Search documents, provisions, and requirements by query string.

    Searches document title, document_id, standard_id;
    provision label, provision text;
    requirement evidence quote.

    Args:
        query: Search query (case-insensitive substring match).
        candidates_dir: Root candidates directory.
        drafts_dir: Draft documents directory.
        limit: Maximum number of results.

    Returns:
        List of SearchResult sorted by record_type then record_id.
    """
    result = collect_records(
        candidates_dir=candidates_dir,
        drafts_dir=drafts_dir,
    )

    hits: list[SearchResult] = []
    q = query.lower()

    for doc in result.documents:
        for field_name, field_value in [
            ("title", doc.get("title", "")),
            ("document_id", doc.get("document_id", "")),
            ("standard_id", doc.get("standard_id", "")),
        ]:
            if q in field_value.lower():
                hits.append(SearchResult(
                    record_type="document",
                    record_id=doc.get("document_id", ""),
                    title=doc.get("title", "unknown"),
                    review_status=doc.get("review_status", "draft"),
                    source=doc.get("source", ""),
                    matched_field=field_name,
                    matched_text=field_value,
                ))
                break

    for prov in result.provisions:
        for field_name, field_value in [
            ("label", prov.get("label", "")),
            ("text", prov.get("text", "")),
        ]:
            if q in field_value.lower():
                hits.append(SearchResult(
                    record_type="provision",
                    record_id=prov.get("provision_id", ""),
                    title=prov.get("label", "unknown"),
                    review_status=prov.get("review_status", "machine_extracted"),
                    source=prov.get("source", ""),
                    matched_field=field_name,
                    matched_text=field_value[:200],
                ))
                break

    for req in result.requirements:
        quote = req.get("evidence_quote", "")
        if q in quote.lower():
            hits.append(SearchResult(
                record_type="requirement",
                record_id=req.get("requirement_id", ""),
                title=req.get("modality", "unknown"),
                review_status=req.get("review_status", "machine_extracted"),
                source=req.get("source", ""),
                matched_field="evidence_quote",
                matched_text=quote[:200],
            ))

    # Sort deterministically: type order, then ID
    type_order = {"document": 0, "provision": 1, "requirement": 2}
    hits.sort(key=lambda h: (type_order.get(h.record_type, 99), h.record_id))

    return hits[:limit]


def format_results(hits: list[SearchResult]) -> str:
    """Format search results for CLI output."""
    if not hits:
        return "No results found."

    lines = []
    for h in hits:
        lines.append(f"[{h.record_type}] {h.record_id}")
        lines.append(f"  title: {h.title}")
        lines.append(f"  status: {h.review_status}")
        lines.append(f"  matched: {h.matched_field} = {h.matched_text[:100]}")
        lines.append(f"  source: {h.source}")
        lines.append("")

    lines.append(f"Total: {len(hits)} result(s)")
    return "\n".join(lines)
