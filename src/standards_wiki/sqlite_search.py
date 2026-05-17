"""SQLite FTS5 search — query the exported database."""

import sqlite3
from pathlib import Path

SNIPPET_MAX_LENGTH = 200


def _truncate(text: str, max_len: int = SNIPPET_MAX_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def _escape_fts(query: str) -> str:
    return query.replace('"', '""')


def _search_documents(conn, query, document_id, review_status, limit):
    sql = """
        SELECT d.document_id, d.title, d.source_text,
               d.document_type, d.review_status
        FROM documents_fts f
        JOIN documents d ON f.document_id = d.document_id
        WHERE documents_fts MATCH ?
    """
    params: list = [_escape_fts(query)]

    if document_id is not None:
        sql += " AND d.document_id = ?"
        params.append(document_id)
    if review_status is not None:
        sql += " AND d.review_status = ?"
        params.append(review_status)

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "type": "document",
            "id": r[0],
            "document_id": r[0],
            "title": r[1],
            "snippet": _truncate(r[2]),
            "document_type": r[3],
            "review_status": r[4],
        }
        for r in rows
    ]


def _search_provisions(conn, query, document_id, review_status, limit):
    sql = """
        SELECT p.provision_id, p.document_id, p.label, p.kind,
               p.title, p.text, p.confidence, p.review_status
        FROM provisions_fts f
        JOIN provisions p ON f.provision_id = p.provision_id
        WHERE provisions_fts MATCH ?
    """
    params: list = [_escape_fts(query)]

    if document_id is not None:
        sql += " AND p.document_id = ?"
        params.append(document_id)
    if review_status is not None:
        sql += " AND p.review_status = ?"
        params.append(review_status)

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "type": "provision",
            "id": r[0],
            "document_id": r[1],
            "label": r[2],
            "kind": r[3],
            "title": r[4],
            "snippet": _truncate(r[5]),
            "confidence": r[6],
            "review_status": r[7],
        }
        for r in rows
    ]


def _search_requirements(conn, query, document_id, review_status, limit):
    sql = """
        SELECT r.requirement_id, r.document_id, r.provision_id,
               r.modality, r.subject, r.action, r.object, r.evidence_quote
        FROM requirements_fts f
        JOIN requirements r ON f.requirement_id = r.requirement_id
        WHERE requirements_fts MATCH ?
    """
    params: list = [_escape_fts(query)]

    if document_id is not None:
        sql += " AND r.document_id = ?"
        params.append(document_id)
    # requirements table has no review_status column — filter ignored

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return [
        {
            "type": "requirement",
            "id": r[0],
            "document_id": r[1],
            "provision_id": r[2],
            "modality": r[3],
            "subject": r[4],
            "action": r[5],
            "object": r[6],
            "snippet": _truncate(r[7]),
        }
        for r in rows
    ]


_SEARCHERS = {
    "documents": _search_documents,
    "provisions": _search_provisions,
    "requirements": _search_requirements,
}

_TYPE_ORDER = {"provision": 0, "document": 1, "requirement": 2}


def search_sqlite(
    db_path: str | Path,
    query: str,
    mode: str = "provisions",
    document_id: str | None = None,
    limit: int = 20,
    review_status: str | None = None,
) -> list[dict]:
    """Search the exported SQLite database using FTS5.

    Args:
        db_path: Path to the SQLite database file.
        query: FTS5 search query string.
        mode: Search mode — 'provisions', 'documents', 'requirements', or 'all'.
        document_id: Optional filter to restrict results to a specific document.
        limit: Maximum number of results to return.
        review_status: Optional filter on review_status (ignored for requirements).

    Returns:
        List of dicts with search results.

    Raises:
        FileNotFoundError: If the database file does not exist.
        ValueError: If mode is not one of the supported values.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found: {db_path}\n"
            f"Run 'python tools/export_sqlite.py' first to create it."
        )

    conn = sqlite3.connect(str(db_path))
    try:
        if mode == "all":
            merged: list[dict] = []
            for searcher in _SEARCHERS.values():
                merged.extend(
                    searcher(conn, query, document_id, review_status, limit)
                )
            merged.sort(
                key=lambda r: (_TYPE_ORDER.get(r["type"], 99), r["id"])
            )
            return merged[:limit]

        if mode in _SEARCHERS:
            return _SEARCHERS[mode](
                conn, query, document_id, review_status, limit
            )

        raise ValueError(
            f"Invalid mode: {mode!r}. "
            f"Use 'provisions', 'documents', 'requirements', or 'all'."
        )
    finally:
        conn.close()
