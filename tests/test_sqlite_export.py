"""Tests for SQLite FTS5 export module."""

import json
import sqlite3

from standards_wiki.indexer import IndexResult, collect_records
from standards_wiki.sqlite_export import export_sqlite


def _make_result() -> IndexResult:
    return IndexResult(
        documents=[
            {
                "document_id": "gb-test-2024",
                "title": "测试标准",
                "document_type": "standard",
                "standard_id": "GB-TEST-2024",
                "publisher": "测试机构",
                "release_date": "2024-01-01",
                "effective_date": "2024-07-01",
                "raw_path": "raw/test.pdf",
                "source_text": "sources/test.md",
                "source_url": "",
                "confidence": "low",
                "review_status": "draft",
                "source": "meta.yaml",
            },
        ],
        provisions=[
            {
                "provision_id": "gb-test-2024-3-1",
                "document_id": "gb-test-2024",
                "label": "3.1",
                "kind": "clause",
                "title": "术语",
                "text": "机动车制动系统应符合要求",
                "locator": {"label": "3.1"},
                "confidence": "low",
                "review_status": "machine_extracted",
                "source": "prov.jsonl",
            },
            {
                "provision_id": "gb-test-2024-4-1",
                "document_id": "gb-test-2024",
                "label": "4.1",
                "kind": "clause",
                "title": "整车",
                "text": "乘用车座椅应可调节",
                "locator": {"label": "4.1"},
                "confidence": "low",
                "review_status": "machine_extracted",
                "source": "prov.jsonl",
            },
        ],
        requirements=[
            {
                "requirement_id": "gb-test-2024-3-1-r1",
                "document_id": "gb-test-2024",
                "provision_id": "gb-test-2024-3-1",
                "modality": "must",
                "subject": "制动系统",
                "action": "符合",
                "object": "要求",
                "condition": "",
                "exception": "",
                "evidence_quote": "机动车制动系统应符合要求",
                "confidence": "low",
                "review_status": "machine_extracted",
                "source": "req.jsonl",
            },
        ],
        topic_tags={
            ("provision", "gb-test-2024-3-1"): {
                "topics": ["braking-system"],
                "entities": ["vehicle"],
            },
            ("provision", "gb-test-2024-4-1"): {
                "topics": ["seats"],
                "entities": ["component"],
            },
            ("requirement", "gb-test-2024-3-1-r1"): {
                "topics": ["braking-system"],
                "entities": ["vehicle"],
            },
        },
    )


class TestSchemaCreation:
    def test_creates_all_tables(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = IndexResult()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()

        expected = {
            "documents", "provisions", "requirements",
            "provision_topics", "provision_entities",
            "requirement_topics", "requirement_entities",
            "export_meta",
        }
        assert expected.issubset(tables)

    def test_creates_fts_tables(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = IndexResult()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()

        assert "provisions_fts" in tables
        assert "requirements_fts" in tables
        assert "documents_fts" in tables


class TestDocumentInsertion:
    def test_inserts_document(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT document_id, title, standard_id FROM documents"
        ).fetchone()
        conn.close()

        assert row == ("gb-test-2024", "测试标准", "GB-TEST-2024")


class TestProvisionInsertion:
    def test_inserts_provisions(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT provision_id, label, text FROM provisions ORDER BY provision_id"
        ).fetchall()
        conn.close()

        assert len(rows) == 2
        assert rows[0][0] == "gb-test-2024-3-1"
        assert rows[1][0] == "gb-test-2024-4-1"


class TestRequirementInsertion:
    def test_inserts_requirement(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT requirement_id, modality, evidence_quote FROM requirements"
        ).fetchone()
        conn.close()

        assert row[0] == "gb-test-2024-3-1-r1"
        assert row[1] == "must"


class TestTopicTagInsertion:
    def test_populates_junction_tables(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        pt = conn.execute(
            "SELECT provision_id, topic FROM provision_topics ORDER BY provision_id"
        ).fetchall()
        pe = conn.execute(
            "SELECT provision_id, entity FROM provision_entities ORDER BY provision_id"
        ).fetchall()
        conn.close()

        assert ("gb-test-2024-3-1", "braking-system") in pt
        assert ("gb-test-2024-4-1", "seats") in pt
        assert ("gb-test-2024-3-1", "vehicle") in pe
        assert ("gb-test-2024-4-1", "component") in pe

    def test_requirement_topic_junctions(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        rt = conn.execute("SELECT requirement_id, topic FROM requirement_topics").fetchall()
        conn.close()

        assert ("gb-test-2024-3-1-r1", "braking-system") in rt


class TestFTSProvisionSearch:
    def test_chinese_fts_3char_search(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        # trigram tokenizer requires 3+ characters for CJK
        rows = conn.execute(
            "SELECT provision_id FROM provisions_fts WHERE text MATCH '制动系'"
        ).fetchall()
        conn.close()

        assert len(rows) >= 1
        assert rows[0][0] == "gb-test-2024-3-1"

    def test_like_fallback_for_short_queries(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        # 2-char queries use LIKE
        rows = conn.execute(
            "SELECT provision_id FROM provisions WHERE text LIKE ?",
            ("%制动%",),
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "gb-test-2024-3-1"


class TestFTSRequirementSearch:
    def test_requirement_fts_3char(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT requirement_id FROM requirements_fts WHERE evidence_quote MATCH '制动系'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1


class TestFTSDocumentsSearch:
    def test_document_fts_3char(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            "SELECT document_id FROM documents_fts WHERE title MATCH '测试标'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "gb-test-2024"


class TestEmptyExport:
    def test_empty_result(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = IndexResult()
        stats = export_sqlite(result, db_path)

        assert stats["documents"] == 0
        assert stats["provisions"] == 0
        assert stats["requirements"] == 0
        assert db_path.exists()


class TestExportMeta:
    def test_meta_populated(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        meta = dict(conn.execute("SELECT key, value FROM export_meta").fetchall())
        conn.close()

        assert meta["documents"] == "1"
        assert meta["provisions"] == "2"
        assert meta["requirements"] == "1"
        assert "exported_at" in meta


class TestIdempotentExport:
    def test_replaces_previous_data(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        result2 = IndexResult(
            documents=[{"document_id": "new-doc", "title": "新文档"}],
        )
        export_sqlite(result2, db_path)

        conn = sqlite3.connect(str(db_path))
        doc_ids = {r[0] for r in conn.execute("SELECT document_id FROM documents")}
        conn.close()

        assert doc_ids == {"new-doc"}


class TestTopicFilterSQL:
    def test_join_query_by_topic(self, tmp_path):
        db_path = tmp_path / "test.sqlite"
        result = _make_result()
        export_sqlite(result, db_path)

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute(
            """SELECT p.provision_id, p.label
               FROM provisions p
               JOIN provision_topics pt ON p.provision_id = pt.provision_id
               WHERE pt.topic = 'braking-system'"""
        ).fetchall()
        conn.close()

        assert len(rows) == 1
        assert rows[0][0] == "gb-test-2024-3-1"
