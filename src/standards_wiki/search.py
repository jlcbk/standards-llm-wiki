"""Deterministic local search over collected records."""

import sqlite3
from dataclasses import dataclass
from pathlib import Path

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


def _search_sqlite(
    query: str,
    db_path: str | Path,
    limit: int,
) -> list[SearchResult]:
    """Search using SQLite FTS5 + LIKE fallback for short queries."""
    db_path = Path(db_path)
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    hits: list[SearchResult] = []

    # Documents: title LIKE
    like = f"%{query}%"
    for row in conn.execute(
        "SELECT document_id, title, review_status, source_path FROM documents WHERE title LIKE ? LIMIT ?",
        (like, limit),
    ):
        hits.append(SearchResult(
            record_type="document",
            record_id=row["document_id"],
            title=row["title"],
            review_status=row["review_status"],
            source=row["source_path"],
            matched_field="title",
            matched_text=row["title"],
        ))

    # Provisions: FTS for 3+ char queries, LIKE for shorter
    prov_rows = _fts_or_like(
        conn, "provisions_fts", "provisions",
        "provision_id", "title", "text", query, limit,
    )
    for row in prov_rows:
        matched = row["title"] if query.lower() in (row["title"] or "").lower() else row["text"]
        hits.append(SearchResult(
            record_type="provision",
            record_id=row["provision_id"],
            title=row["label"] or "",
            review_status=row["review_status"],
            source=row["path"],
            matched_field="text" if matched == row["text"] else "title",
            matched_text=(matched or "")[:200],
        ))

    # Requirements: FTS for 3+ char queries, LIKE for shorter
    req_rows = _fts_or_like(
        conn, "requirements_fts", "requirements",
        "requirement_id", "evidence_quote", "subject", query, limit,
    )
    for row in req_rows:
        hits.append(SearchResult(
            record_type="requirement",
            record_id=row["requirement_id"],
            title=row["modality"] or "",
            review_status=row["review_status"],
            source=row["path"],
            matched_field="evidence_quote",
            matched_text=(row["evidence_quote"] or "")[:200],
        ))

    conn.close()

    type_order = {"document": 0, "provision": 1, "requirement": 2}
    hits.sort(key=lambda h: (type_order.get(h.record_type, 99), h.record_id))
    return hits[:limit]


def _fts_or_like(
    conn: sqlite3.Connection,
    fts_table: str,
    main_table: str,
    id_col: str,
    col1: str,
    col2: str,
    query: str,
    limit: int,
) -> list[sqlite3.Row]:
    """Try FTS MATCH for 3+ char queries, fall back to LIKE."""
    like = f"%{query}%"

    if len(query) >= 3:
        try:
            rows = conn.execute(
                f"SELECT m.* FROM {main_table} m "
                f"JOIN {fts_table} f ON m.rowid = f.rowid "
                f"WHERE {fts_table} MATCH ? LIMIT ?",
                (query, limit),
            ).fetchall()
            if rows:
                return rows
        except sqlite3.OperationalError:
            pass

    return conn.execute(
        f"SELECT * FROM {main_table} WHERE {col1} LIKE ? OR {col2} LIKE ? LIMIT ?",
        (like, like, limit),
    ).fetchall()


def search(
    query: str,
    *,
    candidates_dir: str = _CANDIDATES_DIR,
    drafts_dir: str = _DRAFTS_DIR,
    db_path: str | None = None,
    limit: int = 20,
) -> list[SearchResult]:
    """Search documents, provisions, and requirements by query string.

    When db_path is provided and the file exists, uses SQLite FTS5
    for search. Otherwise falls back to in-memory collect_records scan.

    Args:
        query: Search query (case-insensitive substring match).
        candidates_dir: Root candidates directory.
        drafts_dir: Draft documents directory.
        db_path: Optional path to SQLite database for faster search.
        limit: Maximum number of results.

    Returns:
        List of SearchResult sorted by record_type then record_id.
    """
    if db_path is not None:
        return _search_sqlite(query, db_path, limit)

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
