"""SQLite FTS5 search — query the exported database."""

import re
import sqlite3
from pathlib import Path

SNIPPET_MAX_LENGTH = 200

_HAS_CJK_RE = re.compile(r"[一-鿿]")


def _has_cjk(text: str) -> bool:
    return bool(_HAS_CJK_RE.search(text))


def _truncate(text: str, max_len: int = SNIPPET_MAX_LENGTH) -> str:
    if len(text) <= max_len:
        return text
    return text[:max_len] + "…"


def _escape_fts(query: str) -> str:
    return query.replace('"', '""')


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _has_junction_tables(conn: sqlite3.Connection) -> bool:
    """Check whether junction tables exist (Phase 5.5-02+ schema)."""
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='provision_topics'"
    ).fetchone()
    return row is not None


def _build_topic_entity_where(
    table_alias: str, table_prefix: str, id_col: str,
    topic: str | None, entity: str | None,
) -> tuple[str, list]:
    """Build WHERE additions for topic/entity junction filters.

    Args:
        table_alias: SQL alias for the main table (e.g. 'p' or 'provisions').
        table_prefix: Junction table prefix (e.g. 'provision' or 'requirement').
        id_col: ID column name (e.g. 'provision_id' or 'requirement_id').
        topic: Optional topic filter value.
        entity: Optional entity filter value.

    Returns:
        (sql_fragments, params)
    """
    parts: list[str] = []
    params: list = []

    if topic is not None:
        jtable = f"{table_prefix}_topics"
        parts.append(
            f"EXISTS (SELECT 1 FROM {jtable} WHERE {jtable}.{id_col} = {table_alias}.{id_col} AND {jtable}.topic = ?)"
        )
        params.append(topic)

    if entity is not None:
        jtable = f"{table_prefix}_entities"
        parts.append(
            f"EXISTS (SELECT 1 FROM {jtable} WHERE {jtable}.{id_col} = {table_alias}.{id_col} AND {jtable}.entity = ?)"
        )
        params.append(entity)

    sql = ""
    if parts:
        sql = " AND " + " AND ".join(parts)
    return sql, params


def _search_documents(conn, query, document_id, review_status, limit, topic, entity):
    # documents mode: topic/entity not supported — return empty when specified
    if topic is not None or entity is not None:
        return []

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
    if rows:
        return _rows_to_documents(rows)

    # LIKE fallback for CJK short words
    if _has_cjk(query):
        return _like_fallback_documents(conn, query, document_id, review_status, limit)

    return _rows_to_documents(rows)


def _like_fallback_documents(conn, query, document_id, review_status, limit):
    sql = """
        SELECT document_id, title, source_text,
               document_type, review_status
        FROM documents WHERE 1=1
    """
    params: list = []
    sql += " AND (title LIKE ? ESCAPE '\\' OR source_text LIKE ? ESCAPE '\\')"
    like_pat = f"%{_escape_like(query)}%"
    params.extend([like_pat, like_pat])

    if document_id is not None:
        sql += " AND document_id = ?"
        params.append(document_id)
    if review_status is not None:
        sql += " AND review_status = ?"
        params.append(review_status)

    sql += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return _rows_to_documents(rows)


def _rows_to_documents(rows):
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


def _search_provisions(conn, query, document_id, review_status, limit, topic, entity):
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

    # Topic/entity filters via EXISTS on junction tables
    if topic is not None or entity is not None:
        if _has_junction_tables(conn):
            te_sql, te_params = _build_topic_entity_where(
                "p", "provision", "provision_id", topic, entity
            )
            sql += te_sql
            params.extend(te_params)
        else:
            return []

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    if rows:
        return _rows_to_provisions(rows)

    if _has_cjk(query):
        return _like_fallback_provisions(conn, query, document_id, review_status, limit, topic, entity)

    return _rows_to_provisions(rows)


def _like_fallback_provisions(conn, query, document_id, review_status, limit, topic=None, entity=None):
    sql = """
        SELECT provision_id, document_id, label, kind,
               title, text, confidence, review_status
        FROM provisions WHERE 1=1
    """
    params: list = []
    sql += " AND (label LIKE ? ESCAPE '\\' OR title LIKE ? ESCAPE '\\' OR text LIKE ? ESCAPE '\\')"
    like_pat = f"%{_escape_like(query)}%"
    params.extend([like_pat, like_pat, like_pat])

    if document_id is not None:
        sql += " AND document_id = ?"
        params.append(document_id)
    if review_status is not None:
        sql += " AND review_status = ?"
        params.append(review_status)

    if topic is not None or entity is not None:
        if _has_junction_tables(conn):
            te_sql, te_params = _build_topic_entity_where(
                "provisions", "provision", "provision_id", topic, entity
            )
            sql += te_sql
            params.extend(te_params)
        else:
            return []

    sql += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return _rows_to_provisions(rows)


def _rows_to_provisions(rows):
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


def _search_requirements(conn, query, document_id, review_status, limit, topic, entity):
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

    if topic is not None or entity is not None:
        if _has_junction_tables(conn):
            te_sql, te_params = _build_topic_entity_where(
                "r", "requirement", "requirement_id", topic, entity
            )
            sql += te_sql
            params.extend(te_params)
        else:
            return []

    sql += " ORDER BY rank LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    if rows:
        return _rows_to_requirements(rows)

    if _has_cjk(query):
        return _like_fallback_requirements(conn, query, document_id, limit, topic, entity)

    return _rows_to_requirements(rows)


def _like_fallback_requirements(conn, query, document_id, limit, topic=None, entity=None):
    sql = """
        SELECT requirement_id, document_id, provision_id,
               modality, subject, action, object, evidence_quote
        FROM requirements WHERE 1=1
    """
    params: list = []
    sql += (
        " AND (modality LIKE ? ESCAPE '\\' OR subject LIKE ? ESCAPE '\\' "
        "OR action LIKE ? ESCAPE '\\' OR object LIKE ? ESCAPE '\\' "
        "OR evidence_quote LIKE ? ESCAPE '\\')"
    )
    like_pat = f"%{_escape_like(query)}%"
    params.extend([like_pat, like_pat, like_pat, like_pat, like_pat])

    if document_id is not None:
        sql += " AND document_id = ?"
        params.append(document_id)

    if topic is not None or entity is not None:
        if _has_junction_tables(conn):
            te_sql, te_params = _build_topic_entity_where(
                "requirements", "requirement", "requirement_id", topic, entity
            )
            sql += te_sql
            params.extend(te_params)
        else:
            return []

    sql += " LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return _rows_to_requirements(rows)


def _rows_to_requirements(rows):
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
    topic: str | None = None,
    entity: str | None = None,
) -> list[dict]:
    """Search the exported SQLite database using FTS5.

    Args:
        db_path: Path to the SQLite database file.
        query: FTS5 search query string.
        mode: Search mode — 'provisions', 'documents', 'requirements', or 'all'.
        document_id: Optional filter to restrict results to a specific document.
        limit: Maximum number of results to return.
        review_status: Optional filter on review_status (ignored for requirements).
        topic: Optional filter on topic tag (via junction tables).
        entity: Optional filter on entity tag (via junction tables).

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
            for mode_name, searcher in _SEARCHERS.items():
                # documents mode returns [] when topic/entity specified
                merged.extend(
                    searcher(conn, query, document_id, review_status, limit, topic, entity)
                )
            merged.sort(
                key=lambda r: (_TYPE_ORDER.get(r["type"], 99), r["id"])
            )
            return merged[:limit]

        if mode in _SEARCHERS:
            return _SEARCHERS[mode](
                conn, query, document_id, review_status, limit, topic, entity
            )

        raise ValueError(
            f"Invalid mode: {mode!r}. "
            f"Use 'provisions', 'documents', 'requirements', or 'all'."
        )
    finally:
        conn.close()
