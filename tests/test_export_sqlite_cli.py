"""Tests for export_sqlite CLI."""

import json
import sqlite3

import yaml

from standards_wiki.candidates import write_jsonl


def _write_fixtures(tmp_path, doc_id="gb-test-2024"):
    """Create minimal candidate fixtures."""
    cand = tmp_path / "_candidates"

    meta_dir = cand / "metadata"
    meta_dir.mkdir(parents=True)
    meta = {
        "title": "测试标准",
        "standard_id": "GB-TEST-2024",
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
                "confidence": "low",
                "review_status": "machine_extracted",
                "evidence": {"quote": "test"},
            }
        ],
        req_dir / f"{doc_id}.jsonl",
    )

    return cand


class TestExportSqliteCLI:
    def test_creates_sqlite_file(self, tmp_path, capsys):
        from tools.export_sqlite import main

        cand = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "kb.sqlite"

        main(["--candidates-dir", str(cand), "--out", str(out)])

        assert out.exists()

    def test_prints_counts(self, tmp_path, capsys):
        from tools.export_sqlite import main

        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"

        main(["--candidates-dir", str(cand), "--out", str(out)])

        captured = capsys.readouterr()
        assert "Documents: 1" in captured.out
        assert "Provisions: 1" in captured.out
        assert "Requirements: 1" in captured.out

    def test_database_has_fts_tables(self, tmp_path, capsys):
        from tools.export_sqlite import main

        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"

        main(["--candidates-dir", str(cand), "--out", str(out)])

        conn = sqlite3.connect(str(out))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        conn.close()

        assert "documents_fts" in tables
        assert "provisions_fts" in tables
        assert "requirements_fts" in tables

    def test_fts_query_works(self, tmp_path, capsys):
        from tools.export_sqlite import main

        cand = _write_fixtures(tmp_path)
        out = tmp_path / "kb.sqlite"

        main(["--candidates-dir", str(cand), "--out", str(out)])

        conn = sqlite3.connect(str(out))
        rows = conn.execute(
            "SELECT document_id FROM documents_fts WHERE documents_fts MATCH '测试标准'"
        ).fetchall()
        conn.close()

        assert len(rows) == 1
