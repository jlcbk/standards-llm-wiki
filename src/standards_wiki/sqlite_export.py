"""Export IndexResult to SQLite with FTS5 full-text search."""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .indexer import IndexResult

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS documents (
    document_id   TEXT PRIMARY KEY,
    title         TEXT NOT NULL DEFAULT '',
    document_type TEXT NOT NULL DEFAULT '',
    standard_id   TEXT NOT NULL DEFAULT '',
    publisher     TEXT NOT NULL DEFAULT '',
    release_date  TEXT NOT NULL DEFAULT '',
    effective_date TEXT NOT NULL DEFAULT '',
    source_path   TEXT NOT NULL DEFAULT '',
    source_text   TEXT NOT NULL DEFAULT '',
    source_url    TEXT NOT NULL DEFAULT '',
    confidence    TEXT NOT NULL DEFAULT 'low',
    review_status TEXT NOT NULL DEFAULT 'draft',
    path          TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS provisions (
    provision_id   TEXT PRIMARY KEY,
    document_id    TEXT NOT NULL DEFAULT '',
    label          TEXT NOT NULL DEFAULT '',
    kind           TEXT NOT NULL DEFAULT '',
    title          TEXT NOT NULL DEFAULT '',
    text           TEXT NOT NULL DEFAULT '',
    source_locator TEXT NOT NULL DEFAULT '',
    confidence     TEXT NOT NULL DEFAULT 'low',
    review_status  TEXT NOT NULL DEFAULT 'machine_extracted',
    path           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS requirements (
    requirement_id TEXT PRIMARY KEY,
    document_id    TEXT NOT NULL DEFAULT '',
    provision_id   TEXT NOT NULL DEFAULT '',
    modality       TEXT NOT NULL DEFAULT '',
    subject        TEXT NOT NULL DEFAULT '',
    action         TEXT NOT NULL DEFAULT '',
    object         TEXT NOT NULL DEFAULT '',
    condition      TEXT NOT NULL DEFAULT '',
    exception      TEXT NOT NULL DEFAULT '',
    evidence_quote TEXT NOT NULL DEFAULT '',
    confidence     TEXT NOT NULL DEFAULT 'low',
    review_status  TEXT NOT NULL DEFAULT 'machine_extracted',
    path           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS provision_topics (
    provision_id TEXT NOT NULL,
    topic        TEXT NOT NULL,
    PRIMARY KEY (provision_id, topic)
);

CREATE TABLE IF NOT EXISTS provision_entities (
    provision_id TEXT NOT NULL,
    entity       TEXT NOT NULL,
    PRIMARY KEY (provision_id, entity)
);

CREATE TABLE IF NOT EXISTS requirement_topics (
    requirement_id TEXT NOT NULL,
    topic          TEXT NOT NULL,
    PRIMARY KEY (requirement_id, topic)
);

CREATE TABLE IF NOT EXISTS requirement_entities (
    requirement_id TEXT NOT NULL,
    entity         TEXT NOT NULL,
    PRIMARY KEY (requirement_id, entity)
);

CREATE VIRTUAL TABLE IF NOT EXISTS provisions_fts USING fts5(
    provision_id UNINDEXED,
    title,
    text,
    content='provisions',
    content_rowid='rowid',
    tokenize='trigram'
);

CREATE VIRTUAL TABLE IF NOT EXISTS requirements_fts USING fts5(
    requirement_id UNINDEXED,
    evidence_quote,
    subject,
    action,
    content='requirements',
    content_rowid='rowid',
    tokenize='trigram'
);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    document_id UNINDEXED,
    title,
    content='documents',
    content_rowid='rowid',
    tokenize='trigram'
);

CREATE TABLE IF NOT EXISTS export_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)


def _insert_documents(conn: sqlite3.Connection, documents: list[dict]) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO documents
           (document_id, title, document_type, standard_id, publisher,
            release_date, effective_date, source_path, source_text,
            source_url, confidence, review_status, path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                d.get("document_id", ""),
                d.get("title", ""),
                d.get("document_type", ""),
                d.get("standard_id", ""),
                d.get("publisher", ""),
                d.get("release_date") or "",
                d.get("effective_date") or "",
                d.get("raw_path", ""),
                d.get("source_text", ""),
                d.get("source_url", ""),
                d.get("confidence", "low"),
                d.get("review_status", "draft"),
                d.get("draft_path", "") or d.get("source", ""),
            )
            for d in documents
        ],
    )


def _insert_provisions(conn: sqlite3.Connection, provisions: list[dict]) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO provisions
           (provision_id, document_id, label, kind, title, text,
            source_locator, confidence, review_status, path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                p.get("provision_id", ""),
                p.get("document_id", ""),
                p.get("label", ""),
                p.get("kind", ""),
                p.get("title", ""),
                p.get("text", ""),
                json.dumps(p.get("locator", {}), ensure_ascii=False),
                p.get("confidence", "low"),
                p.get("review_status", "machine_extracted"),
                p.get("source", ""),
            )
            for p in provisions
        ],
    )


def _insert_requirements(conn: sqlite3.Connection, requirements: list[dict]) -> None:
    conn.executemany(
        """INSERT OR REPLACE INTO requirements
           (requirement_id, document_id, provision_id, modality,
            subject, action, object, condition, exception,
            evidence_quote, confidence, review_status, path)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (
                r.get("requirement_id", ""),
                r.get("document_id", ""),
                r.get("provision_id", ""),
                r.get("modality", ""),
                r.get("subject", ""),
                r.get("action", ""),
                r.get("object", ""),
                r.get("condition", ""),
                r.get("exception", ""),
                r.get("evidence_quote", ""),
                r.get("confidence", "low"),
                r.get("review_status", "machine_extracted"),
                r.get("source", ""),
            )
            for r in requirements
        ],
    )


def _insert_topic_tags(
    conn: sqlite3.Connection, topic_tags: dict[tuple[str, str], dict]
) -> None:
    for (record_type, record_id), tags in topic_tags.items():
        topics = tags.get("topics", [])
        entities = tags.get("entities", [])
        if record_type == "provision":
            conn.executemany(
                "INSERT OR IGNORE INTO provision_topics (provision_id, topic) VALUES (?, ?)",
                [(record_id, t) for t in topics],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO provision_entities (provision_id, entity) VALUES (?, ?)",
                [(record_id, e) for e in entities],
            )
        elif record_type == "requirement":
            conn.executemany(
                "INSERT OR IGNORE INTO requirement_topics (requirement_id, topic) VALUES (?, ?)",
                [(record_id, t) for t in topics],
            )
            conn.executemany(
                "INSERT OR IGNORE INTO requirement_entities (requirement_id, entity) VALUES (?, ?)",
                [(record_id, e) for e in entities],
            )


def _rebuild_fts(conn: sqlite3.Connection) -> None:
    conn.execute("INSERT INTO provisions_fts(provisions_fts) VALUES('rebuild')")
    conn.execute("INSERT INTO requirements_fts(requirements_fts) VALUES('rebuild')")
    conn.execute("INSERT INTO documents_fts(documents_fts) VALUES('rebuild')")


def _write_meta(conn: sqlite3.Connection, stats: dict[str, Any]) -> None:
    now = datetime.now(timezone.utc).isoformat()
    for key, value in [
        ("exported_at", now),
        ("documents", str(stats.get("documents", 0))),
        ("provisions", str(stats.get("provisions", 0))),
        ("requirements", str(stats.get("requirements", 0))),
        ("topic_tags", str(stats.get("topic_tags", 0))),
    ]:
        conn.execute(
            "INSERT OR REPLACE INTO export_meta (key, value) VALUES (?, ?)",
            (key, value),
        )


def export_sqlite(
    result: IndexResult,
    output_path: str | Path,
) -> dict[str, Any]:
    """Export IndexResult to a SQLite database with FTS5.

    Creates tables, inserts records, populates FTS indexes,
    and writes export metadata.

    Args:
        result: IndexResult from collect_records.
        output_path: Path for the .sqlite file.

    Returns:
        Dict with export stats (record counts, path, etc.).
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists():
        output_path.unlink()

    conn = _connect(output_path)
    try:
        _create_tables(conn)
        _insert_documents(conn, result.documents)
        _insert_provisions(conn, result.provisions)
        _insert_requirements(conn, result.requirements)
        _insert_topic_tags(conn, result.topic_tags)
        _rebuild_fts(conn)

        stats = {
            "documents": len(result.documents),
            "provisions": len(result.provisions),
            "requirements": len(result.requirements),
            "topic_tags": len(result.topic_tags),
        }
        _write_meta(conn, stats)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    stats["path"] = str(output_path)
    return stats
