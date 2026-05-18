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
            "requirements": [
                {
                    "id": f"{doc_id}-1-r1",
                    "topics": ["braking", "safety"],
                    "entities": ["brake-system"],
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
        assert result["provision_topics"] == 0
        assert result["provision_entities"] == 0
        assert result["requirement_topics"] == 0
        assert result["requirement_entities"] == 0
        assert out.exists()

    # --- junction table tests ---

    def test_junction_tables_exist(self, tmp_path):
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

        assert "provision_topics" in tables
        assert "provision_entities" in tables
        assert "requirement_topics" in tables
        assert "requirement_entities" in tables

    def test_provision_junction_rows(self, tmp_path):
        cand = _write_fixtures(tmp_path, with_topic_tags=True)
        out = tmp_path / "kb.sqlite"
        result = export_sqlite(str(cand), str(out))

        assert result["provision_topics"] == 2
        assert result["provision_entities"] == 1

        conn = sqlite3.connect(str(out))
        topics = sorted(
            r[0]
            for r in conn.execute(
                "SELECT topic FROM provision_topics WHERE provision_id='gb-test-2024-1'"
            )
        )
        entities = sorted(
            r[0]
            for r in conn.execute(
                "SELECT entity FROM provision_entities WHERE provision_id='gb-test-2024-1'"
            )
        )
        conn.close()

        assert topics == ["safety", "vehicle"]
        assert entities == ["motor-vehicle"]

    def test_requirement_junction_rows(self, tmp_path):
        cand = _write_fixtures(tmp_path, with_topic_tags=True)
        out = tmp_path / "kb.sqlite"
        result = export_sqlite(str(cand), str(out))

        assert result["requirement_topics"] == 2
        assert result["requirement_entities"] == 1

        conn = sqlite3.connect(str(out))
        topics = sorted(
            r[0]
            for r in conn.execute(
                "SELECT topic FROM requirement_topics WHERE requirement_id='gb-test-2024-1-r1'"
            )
        )
        entities = sorted(
            r[0]
            for r in conn.execute(
                "SELECT entity FROM requirement_entities WHERE requirement_id='gb-test-2024-1-r1'"
            )
        )
        conn.close()

        assert topics == ["braking", "safety"]
        assert entities == ["brake-system"]

    def test_missing_topic_tags_empty_junctions(self, tmp_path):
        cand = _write_fixtures(tmp_path, with_topic_tags=False)
        out = tmp_path / "kb.sqlite"
        result = export_sqlite(str(cand), str(out))

        assert result["provision_topics"] == 0
        assert result["provision_entities"] == 0
        assert result["requirement_topics"] == 0
        assert result["requirement_entities"] == 0

        conn = sqlite3.connect(str(out))
        for table in [
            "provision_topics",
            "provision_entities",
            "requirement_topics",
            "requirement_entities",
        ]:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            assert count == 0, f"{table} should be empty"
        conn.close()

    def test_duplicate_topic_entity_dedup(self, tmp_path):
        cand = _write_fixtures(tmp_path, with_topic_tags=True)
        tt_dir = cand / "topic-tags"

        # Write a second topic-tags file for the same doc with overlapping entries
        tt_data2 = {
            "document_id": "gb-test-2024",
            "provisions": [
                {
                    "id": "gb-test-2024-1",
                    "topics": ["safety", "new-topic"],
                    "entities": ["motor-vehicle", "new-entity"],
                }
            ],
        }
        (tt_dir / "gb-test-2024-extra.json").write_text(
            json.dumps(tt_data2, ensure_ascii=False), encoding="utf-8"
        )

        out = tmp_path / "kb.sqlite"
        result = export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        topics = sorted(
            r[0]
            for r in conn.execute(
                "SELECT topic FROM provision_topics WHERE provision_id='gb-test-2024-1'"
            )
        )
        entities = sorted(
            r[0]
            for r in conn.execute(
                "SELECT entity FROM provision_entities WHERE provision_id='gb-test-2024-1'"
            )
        )
        conn.close()

        # "safety" appears in both files but should be deduplicated
        assert topics == ["new-topic", "safety", "vehicle"]
        assert entities == ["motor-vehicle", "new-entity"]

    def test_join_topic_to_provision(self, tmp_path):
        cand = _write_fixtures(tmp_path, with_topic_tags=True)
        out = tmp_path / "kb.sqlite"
        export_sqlite(str(cand), str(out))

        conn = sqlite3.connect(str(out))
        rows = conn.execute(
            "SELECT p.provision_id, p.title "
            "FROM provisions p "
            "JOIN provision_topics pt ON p.provision_id = pt.provision_id "
            "WHERE pt.topic = 'safety'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "gb-test-2024-1"
        assert rows[0][1] == "总则"
