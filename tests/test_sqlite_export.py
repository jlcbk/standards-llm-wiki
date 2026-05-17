"""Tests for standards_wiki.sqlite_export."""

import json
import sqlite3

import yaml

from standards_wiki.candidates import write_jsonl
from standards_wiki.sqlite_export import export_sqlite


def _write_fixtures(tmp_path, doc_id="gb-test-2024", with_topic_tags=True):
    """Create minimal candidate fixtures."""
    cand = tmp_path / "_candidates"

    meta_dir = cand / "metadata"
    meta_dir.mkdir(parents=True)
    meta = {
        "title": "测试标准",
        "document_type": "national",
        "standard_id": "GB-TEST-2024",
        "publisher": "测试出版社",
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
        "confidence": "low",
        "review_status": "draft",
    }
    (meta_dir / f"{doc_id}.yaml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8"
    )

    prov_dir = cand / "provisions"
    prov_dir.mkdir(parents=True)
    write_jsonl(
        [
            {
                "provision_id": f"{doc_id}-1",
                "document_id": doc_id,
                "label": "1",
                "kind": "section",
                "title": "总则",
                "text": "本标准规定了机动车运行安全技术条件。vehiclesafety",
                "locator": {"label": "1", "occurrence": 1},
                "confidence": "low",
                "review_status": "machine_extracted",
            }
        ],
        prov_dir / f"{doc_id}.jsonl",
    )

    req_dir = cand / "requirements"
    req_dir.mkdir(parents=True)
    write_jsonl(
        [
            {
                "requirement_id": f"{doc_id}-1-r1",
                "document_id": doc_id,
                "provision_id": f"{doc_id}-1",
                "modality": "must",
                "subject": "机动车",
                "action": "符合",
                "object": "安全技术条件",
                "evidence": {"quote": "机动车必须符合安全技术条件"},
                "confidence": "low",
                "review_status": "machine_extracted",
            }
        ],
        req_dir / f"{doc_id}.jsonl",
    )

    if with_topic_tags:
        tt_dir = cand / "topic-tags"
        tt_dir.mkdir(parents=True)
        tt_data = {
            "document_id": doc_id,
            "provisions": [
                {
                    "id": f"{doc_id}-1",
                    "topics": ["safety", "vehicle"],
                    "entities": ["motor-vehicle"],
                }
            ],
        }
        (tt_dir / f"{doc_id}.json").write_text(
            json.dumps(tt_data, ensure_ascii=False), encoding="utf-8"
        )

    return cand


class TestExportSqlite:
    def test_creates_database_file(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "kb.sqlite"

        result = export_sqlite(str(cand), str(out))

        assert out.exists()
        assert result["path"] == str(out)

    def test_tables_exist(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"
        export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()

        expected = {
            "documents", "documents_fts",
            "provisions", "provisions_fts",
            "requirements", "requirements_fts",
        }
        assert expected.issubset(tables)

    def test_row_counts(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"

        result = export_sqlite(str(cand), str(out))

        assert result["documents"] == 1
        assert result["provisions"] == 1
        assert result["requirements"] == 1

        conn = sqlite3.connect(str(out))
        assert conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM provisions").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0] == 1
        conn.close()

    def test_document_fields(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"
        export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        cols = [d[0] for d in conn.execute("SELECT * FROM documents LIMIT 0").description]
        conn.close()

        assert "document_id" in cols
        assert "title" in cols
        assert "metadata_json" in cols

    def test_fts_document_search(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"
        export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        rows = conn.execute(
            "SELECT document_id FROM documents_fts WHERE documents_fts MATCH '测试标准'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "gb-test-2024"

    def test_fts_provision_search(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"
        export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        rows = conn.execute(
            "SELECT provision_id FROM provisions_fts WHERE provisions_fts MATCH 'vehiclesafety'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1

    def test_fts_requirement_search(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"
        export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        rows = conn.execute(
            "SELECT requirement_id FROM requirements_fts "
            "WHERE requirements_fts MATCH '安全技术条件'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "gb-test-2024-1-r1"

    def test_topic_tags_enrichment(self, tmp_path):
        cand = _write_fixtures(tmp_path, with_topic_tags=True)
        out = tmp_path / "kb.sqlite"
        export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        row = conn.execute(
            "SELECT topics_json, entities_json FROM provisions WHERE provision_id='gb-test-2024-1'"
        ).fetchone()
        conn.close()

        topics = json.loads(row[0])
        entities = json.loads(row[1])
        assert "safety" in topics
        assert "motor-vehicle" in entities

    def test_missing_topic_tags_still_works(self, tmp_path):
        cand = _write_fixtures(tmp_path, with_topic_tags=False)
        out = tmp_path / "kb.sqlite"

        result = export_sqlite(str(cand), str(out))

        assert result["documents"] == 1
        assert result["provisions"] == 1
        assert result["requirements"] == 1

        conn = sqlite3.connect(str(out))
        row = conn.execute(
            "SELECT topics_json, entities_json FROM provisions WHERE provision_id='gb-test-2024-1'"
        ).fetchone()
        conn.close()

        assert json.loads(row[0]) == []
        assert json.loads(row[1]) == []

    def test_idempotent_rebuild(self, tmp_path):
        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"

        r1 = export_sqlite(str(cand), str(out))
        r2 = export_sqlite(str(cand), str(out))

        assert r1["documents"] == r2["documents"]
        assert r1["provisions"] == r2["provisions"]
        assert r1["requirements"] == r2["requirements"]

    def test_empty_candidates_dir(self, tmp_path):
        empty_cand = tmp_path / "empty"
        empty_cand.mkdir()
        out = tmp_path / "kb.sqlite"

        result = export_sqlite(str(empty_cand), str(out))

        assert result["documents"] == 0
        assert result["provisions"] == 0
        assert result["requirements"] == 0
        assert out.exists()
