"""SQLite FTS5 export — build a full-text searchable database from candidate data."""

import json
import sqlite3
from pathlib import Path

import yaml

from .candidates import read_jsonl

# Prefer trigram tokenizer for CJK substring matching (available in SQLite ≥ 3.34.0
# with SQLITE_ENABLE_FTS5_TRIGRAM).  Falls back to unicode61 if trigram is not
# compiled into the local SQLite build.
_FTS_TOKENIZER = "unicode61"


def _detect_trigram_support() -> str:
    """Return 'trigram' if the runtime SQLite supports it, else 'unicode61'."""
    import sqlite3 as _sq

    conn = _sq.connect(":memory:")
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE _trigram_test USING fts5(x, tokenize='trigram')"
        )
        return "trigram"
    except Exception:
        return "unicode61"
    finally:
        conn.close()


# One-time detection at import time.
try:
    _FTS_TOKENIZER = _detect_trigram_support()
except Exception:
    pass


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_topic_tags(candidates_dir: Path) -> dict:
    """Load topic-tags/{doc_id}.json.

    Returns dict with 'provisions' and 'requirements' keys,
    each mapping id -> {topics, entities}.
    """
    tt_dir = candidates_dir / "topic-tags"
    if not tt_dir.exists():
        return {"provisions": {}, "requirements": {}}

    provisions: dict[str, dict] = {}
    requirements: dict[str, dict] = {}

    for tt_path in sorted(tt_dir.glob("*.json")):
        try:
            data = json.loads(tt_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for prov in data.get("provisions", []):
            pid = prov.get("id", "")
            if pid:
                new_topics = prov.get("topics", [])
                new_entities = prov.get("entities", [])
                if pid in provisions:
                    provisions[pid] = {
                        "topics": sorted(set(provisions[pid]["topics"]) | set(new_topics)),
                        "entities": sorted(set(provisions[pid]["entities"]) | set(new_entities)),
                    }
                else:
                    provisions[pid] = {
                        "topics": list(new_topics),
                        "entities": list(new_entities),
                    }
        for req in data.get("requirements", []):
            rid = req.get("id", "")
            if rid:
                new_topics = req.get("topics", [])
                new_entities = req.get("entities", [])
                if rid in requirements:
                    requirements[rid] = {
                        "topics": sorted(set(requirements[rid]["topics"]) | set(new_topics)),
                        "entities": sorted(set(requirements[rid]["entities"]) | set(new_entities)),
                    }
                else:
                    requirements[rid] = {
                        "topics": list(new_topics),
                        "entities": list(new_entities),
                    }

    return {"provisions": provisions, "requirements": requirements}


def _create_schema(conn: sqlite3.Connection) -> None:
    tok = _FTS_TOKENIZER
    conn.executescript(f"""
        DROP TABLE IF EXISTS requirement_entities;
        DROP TABLE IF EXISTS requirement_topics;
        DROP TABLE IF EXISTS provision_entities;
        DROP TABLE IF EXISTS provision_topics;
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
            metadata_json TEXT NOT NULL DEFAULT '{{}}'
        );

        CREATE VIRTUAL TABLE documents_fts USING fts5(
            document_id UNINDEXED,
            title,
            source_text,
            tokenize='{tok}'
        );

        CREATE TABLE provisions (
            provision_id  TEXT PRIMARY KEY,
            document_id   TEXT NOT NULL DEFAULT '',
            label         TEXT NOT NULL DEFAULT '',
            kind          TEXT NOT NULL DEFAULT '',
            title         TEXT NOT NULL DEFAULT '',
            text          TEXT NOT NULL DEFAULT '',
            locator_json  TEXT NOT NULL DEFAULT '{{}}',
            confidence    TEXT NOT NULL DEFAULT '',
            review_status TEXT NOT NULL DEFAULT '',
            path          TEXT NOT NULL DEFAULT '',
            record_json   TEXT NOT NULL DEFAULT '{{}}',
            topics_json   TEXT NOT NULL DEFAULT '[]',
            entities_json TEXT NOT NULL DEFAULT '[]'
        );

        CREATE VIRTUAL TABLE provisions_fts USING fts5(
            provision_id UNINDEXED,
            document_id  UNINDEXED,
            label,
            title,
            text,
            tokenize='{tok}'
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
            record_json    TEXT NOT NULL DEFAULT '{{}}',
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
            tokenize='{tok}'
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
    conn: sqlite3.Connection, candidates_dir: Path, prov_tags: dict[str, dict]
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
            tt = prov_tags.get(pid, {})
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
    conn: sqlite3.Connection, candidates_dir: Path, req_tags: dict[str, dict],
    prov_tags: dict[str, dict],
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
            # requirement-specific tags take priority; fall back to provision tags
            tt = req_tags.get(rid) or prov_tags.get(prov_id, {})

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


def _insert_junction_tables(
    conn: sqlite3.Connection, topic_tags: dict,
) -> dict[str, int]:
    """Insert rows into the 4 junction tables. Returns counts per table."""
    prov_tags = topic_tags.get("provisions", {})
    req_tags = topic_tags.get("requirements", {})

    counts = {
        "provision_topics": 0,
        "provision_entities": 0,
        "requirement_topics": 0,
        "requirement_entities": 0,
    }

    for pid, tt in sorted(prov_tags.items()):
        for topic in tt.get("topics", []):
            before = conn.total_changes
            conn.execute(
                "INSERT OR IGNORE INTO provision_topics (provision_id, topic) "
                "VALUES (?, ?)",
                (pid, topic),
            )
            if conn.total_changes > before:
                counts["provision_topics"] += 1
        for entity in tt.get("entities", []):
            before = conn.total_changes
            conn.execute(
                "INSERT OR IGNORE INTO provision_entities (provision_id, entity) "
                "VALUES (?, ?)",
                (pid, entity),
            )
            if conn.total_changes > before:
                counts["provision_entities"] += 1

    for rid, tt in sorted(req_tags.items()):
        for topic in tt.get("topics", []):
            before = conn.total_changes
            conn.execute(
                "INSERT OR IGNORE INTO requirement_topics (requirement_id, topic) "
                "VALUES (?, ?)",
                (rid, topic),
            )
            if conn.total_changes > before:
                counts["requirement_topics"] += 1
        for entity in tt.get("entities", []):
            before = conn.total_changes
            conn.execute(
                "INSERT OR IGNORE INTO requirement_entities (requirement_id, entity) "
                "VALUES (?, ?)",
                (rid, entity),
            )
            if conn.total_changes > before:
                counts["requirement_entities"] += 1

    return counts


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
    prov_tags = topic_tags.get("provisions", {})
    req_tags = topic_tags.get("requirements", {})

    conn = sqlite3.connect(str(out_path))
    try:
        _create_schema(conn)
        doc_count = _insert_documents(conn, candidates_dir)
        prov_count = _insert_provisions(conn, candidates_dir, prov_tags)
        req_count = _insert_requirements(conn, candidates_dir, req_tags, prov_tags)
        junc_counts = _insert_junction_tables(conn, topic_tags)
        conn.commit()
    finally:
        conn.close()

    return {
        "documents": doc_count,
        "provisions": prov_count,
        "requirements": req_count,
        "provision_topics": junc_counts["provision_topics"],
        "provision_entities": junc_counts["provision_entities"],
        "requirement_topics": junc_counts["requirement_topics"],
        "requirement_entities": junc_counts["requirement_entities"],
        "path": str(out_path),
    }
