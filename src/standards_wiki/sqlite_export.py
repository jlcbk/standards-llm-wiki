"""SQLite FTS5 export — build a full-text searchable database from candidate data."""

import json
import sqlite3
from pathlib import Path

import yaml

from .candidates import read_jsonl


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_topic_tags(candidates_dir: Path) -> dict[str, dict]:
    """Load topic-tags/{doc_id}.json, keyed by provision_id."""
    tt_dir = candidates_dir / "topic-tags"
    if not tt_dir.exists():
        return {}

    result: dict[str, dict] = {}
    for tt_path in sorted(tt_dir.glob("*.json")):
        try:
            data = json.loads(tt_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for prov in data.get("provisions", []):
            pid = prov.get("id", "")
            if pid:
                result[pid] = {
                    "topics": prov.get("topics", []),
                    "entities": prov.get("entities", []),
                }
    return result


def _create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        DROP TABLE IF EXISTS requirements;
        DROP TABLE IF EXISTS requirements_fts;
        DROP TABLE IF EXISTS provisions;
        DROP TABLE IF EXISTS provisions_fts;
        DROP TABLE IF EXISTS documents;
        DROP TABLE IF EXISTS documents_fts;

        CREATE TABLE documents (
            document_id   TEXT PRIMARY KEY,
            title         TEXT NOT NULL DEFAULT '',
            document_type TEXT NOT NULL DEFAULT '',
            standard_id   TEXT NOT NULL DEFAULT '',
            publisher     TEXT NOT NULL DEFAULT '',
            source_text   TEXT NOT NULL DEFAULT '',
            raw_path      TEXT NOT NULL DEFAULT '',
            confidence    TEXT NOT NULL DEFAULT '',
            review_status TEXT NOT NULL DEFAULT '',
            path          TEXT NOT NULL DEFAULT '',
            metadata_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE VIRTUAL TABLE documents_fts USING fts5(
            document_id UNINDEXED,
            title,
            source_text,
            tokenize='unicode61'
        );

        CREATE TABLE provisions (
            provision_id  TEXT PRIMARY KEY,
            document_id   TEXT NOT NULL DEFAULT '',
            label         TEXT NOT NULL DEFAULT '',
            kind          TEXT NOT NULL DEFAULT '',
            title         TEXT NOT NULL DEFAULT '',
            text          TEXT NOT NULL DEFAULT '',
            locator_json  TEXT NOT NULL DEFAULT '{}',
            confidence    TEXT NOT NULL DEFAULT '',
            review_status TEXT NOT NULL DEFAULT '',
            path          TEXT NOT NULL DEFAULT '',
            record_json   TEXT NOT NULL DEFAULT '{}',
            topics_json   TEXT NOT NULL DEFAULT '[]',
            entities_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE VIRTUAL TABLE provisions_fts USING fts5(
            provision_id UNINDEXED,
            document_id  UNINDEXED,
            label,
            title,
            text,
            tokenize='unicode61'
        );

        CREATE TABLE requirements (
            requirement_id TEXT PRIMARY KEY,
            document_id    TEXT NOT NULL DEFAULT '',
            provision_id   TEXT NOT NULL DEFAULT '',
            modality       TEXT NOT NULL DEFAULT '',
            subject        TEXT NOT NULL DEFAULT '',
            action         TEXT NOT NULL DEFAULT '',
            object         TEXT NOT NULL DEFAULT '',
            evidence_quote TEXT NOT NULL DEFAULT '',
            record_json    TEXT NOT NULL DEFAULT '{}',
            topics_json    TEXT NOT NULL DEFAULT '[]',
            entities_json  TEXT NOT NULL DEFAULT '[]'
        );

        CREATE VIRTUAL TABLE requirements_fts USING fts5(
            requirement_id UNINDEXED,
            document_id    UNINDEXED,
            provision_id   UNINDEXED,
            modality,
            subject,
            action,
            object,
            evidence_quote,
            tokenize='unicode61'
        );
    """)


def _insert_documents(
    conn: sqlite3.Connection, candidates_dir: Path
) -> int:
    meta_dir = candidates_dir / "metadata"
    if not meta_dir.exists():
        return 0

    count = 0
    for meta_path in sorted(meta_dir.glob("*.yaml")):
        doc_id = meta_path.stem
        meta = _load_yaml(meta_path)
        if not meta:
            continue

        row = {
            "document_id": doc_id,
            "title": meta.get("title", ""),
            "document_type": meta.get("document_type", ""),
            "standard_id": meta.get("standard_id", ""),
            "publisher": meta.get("publisher", ""),
            "source_text": meta.get("source_text", ""),
            "raw_path": meta.get("raw_path", ""),
            "confidence": meta.get("confidence", ""),
            "review_status": meta.get("review_status", ""),
            "path": str(meta_path),
            "metadata_json": json.dumps(meta, ensure_ascii=False),
        }

        conn.execute(
            "INSERT INTO documents VALUES (:document_id,:title,:document_type,"
            ":standard_id,:publisher,:source_text,:raw_path,:confidence,"
            ":review_status,:path,:metadata_json)",
            row,
        )
        conn.execute(
            "INSERT INTO documents_fts VALUES (:document_id,:title,:source_text)",
            row,
        )
        count += 1

    return count


def _insert_provisions(
    conn: sqlite3.Connection, candidates_dir: Path, topic_tags: dict[str, dict]
) -> int:
    prov_dir = candidates_dir / "provisions"
    if not prov_dir.exists():
        return 0

    count = 0
    for jsonl_path in sorted(prov_dir.glob("*.jsonl")):
        try:
            records = read_jsonl(jsonl_path)
        except Exception:
            continue

        for rec in records:
            pid = rec.get("provision_id", "")
            tt = topic_tags.get(pid, {})
            locator = rec.get("locator", {})

            row = {
                "provision_id": pid,
                "document_id": rec.get("document_id", ""),
                "label": rec.get("label", ""),
                "kind": rec.get("kind", ""),
                "title": rec.get("title", ""),
                "text": rec.get("text", ""),
                "locator_json": json.dumps(locator, ensure_ascii=False),
                "confidence": rec.get("confidence", ""),
                "review_status": rec.get("review_status", ""),
                "path": str(jsonl_path),
                "record_json": json.dumps(rec, ensure_ascii=False),
                "topics_json": json.dumps(tt.get("topics", []), ensure_ascii=False),
                "entities_json": json.dumps(tt.get("entities", []), ensure_ascii=False),
            }

            conn.execute(
                "INSERT INTO provisions VALUES (:provision_id,:document_id,:label,"
                ":kind,:title,:text,:locator_json,:confidence,:review_status,"
                ":path,:record_json,:topics_json,:entities_json)",
                row,
            )
            conn.execute(
                "INSERT INTO provisions_fts VALUES (:provision_id,:document_id,"
                ":label,:title,:text)",
                row,
            )
            count += 1

    return count


def _insert_requirements(
    conn: sqlite3.Connection, candidates_dir: Path, topic_tags: dict[str, dict]
) -> int:
    req_dir = candidates_dir / "requirements"
    if not req_dir.exists():
        return 0

    count = 0
    for jsonl_path in sorted(req_dir.glob("*.jsonl")):
        try:
            records = read_jsonl(jsonl_path)
        except Exception:
            continue

        for rec in records:
            rid = rec.get("requirement_id", "")
            evidence = rec.get("evidence", {})
            prov_id = rec.get("provision_id", "")
            tt = topic_tags.get(prov_id, {})

            row = {
                "requirement_id": rid,
                "document_id": rec.get("document_id", ""),
                "provision_id": prov_id,
                "modality": rec.get("modality", ""),
                "subject": rec.get("subject", ""),
                "action": rec.get("action", ""),
                "object": rec.get("object", ""),
                "evidence_quote": evidence.get("quote", ""),
                "record_json": json.dumps(rec, ensure_ascii=False),
                "topics_json": json.dumps(tt.get("topics", []), ensure_ascii=False),
                "entities_json": json.dumps(tt.get("entities", []), ensure_ascii=False),
            }

            conn.execute(
                "INSERT INTO requirements VALUES (:requirement_id,:document_id,"
                ":provision_id,:modality,:subject,:action,:object,:evidence_quote,"
                ":record_json,:topics_json,:entities_json)",
                row,
            )
            conn.execute(
                "INSERT INTO requirements_fts VALUES (:requirement_id,:document_id,"
                ":provision_id,:modality,:subject,:action,:object,:evidence_quote)",
                row,
            )
            count += 1

    return count


def export_sqlite(candidates_dir: str | Path, out_path: str | Path) -> dict:
    """Build SQLite database with FTS5 from candidate data.

    Args:
        candidates_dir: Root candidates directory containing metadata/,
            provisions/, requirements/, and optionally topic-tags/ subdirs.
        out_path: Output path for the SQLite database file.

    Returns:
        Dict with counts and the resolved output path.
    """
    candidates_dir = Path(candidates_dir)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists():
        out_path.unlink()

    topic_tags = _load_topic_tags(candidates_dir)

    conn = sqlite3.connect(str(out_path))
    try:
        _create_schema(conn)
        doc_count = _insert_documents(conn, candidates_dir)
        prov_count = _insert_provisions(conn, candidates_dir, topic_tags)
        req_count = _insert_requirements(conn, candidates_dir, topic_tags)
        conn.commit()
    finally:
        conn.close()

    return {
        "documents": doc_count,
        "provisions": prov_count,
        "requirements": req_count,
        "path": str(out_path),
    }
