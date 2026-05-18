"""Tests for export_sqlite CLI."""

import sqlite3

import yaml

from standards_wiki.candidates import write_jsonl


def _write_fixtures(tmp_path, doc_id="gb-test-2024"):
    cand = tmp_path / "_candidates"
    drafts = tmp_path / "documents" / "drafts"

    meta_dir = cand / "metadata"
    meta_dir.mkdir(parents=True)
    meta = {"title": "测试标准", "standard_id": "GB-TEST-2024", "review_status": "draft"}
    (meta_dir / f"{doc_id}.yaml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8"
    )

    drafts.mkdir(parents=True)
    fm_yaml = yaml.dump(
        {"document_id": doc_id, "title": "测试标准", "review_status": "draft"},
        default_flow_style=False,
        allow_unicode=True,
    )
    (drafts / f"{doc_id}.md").write_text(
        f"---\n{fm_yaml}---\n\n正文", encoding="utf-8"
    )

    prov_dir = cand / "provisions"
    prov_dir.mkdir(parents=True)
    write_jsonl(
        [{"provision_id": f"{doc_id}-1", "document_id": doc_id, "label": "1",
          "kind": "section", "confidence": "low", "review_status": "machine_extracted",
          "evidence": {"quote": "test"}}],
        prov_dir / f"{doc_id}.jsonl",
    )

    req_dir = cand / "requirements"
    req_dir.mkdir(parents=True)
    write_jsonl(
        [{"requirement_id": f"{doc_id}-1-r1", "document_id": doc_id,
          "provision_id": f"{doc_id}-1", "modality": "must",
          "confidence": "low", "review_status": "machine_extracted",
          "evidence": {"quote": "test"}}],
        req_dir / f"{doc_id}.jsonl",
    )

    return cand, drafts


class TestExportSqliteCLI:
    def test_creates_sqlite_file(self, tmp_path):
        from tools.export_sqlite import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "kb.sqlite"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--out", str(out),
        ])

        assert out.exists()

    def test_contains_records(self, tmp_path):
        from tools.export_sqlite import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "kb.sqlite"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--out", str(out),
        ])

        conn = sqlite3.connect(str(out))
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        prov_count = conn.execute("SELECT COUNT(*) FROM provisions").fetchone()[0]
        req_count = conn.execute("SELECT COUNT(*) FROM requirements").fetchone()[0]
        conn.close()

        assert doc_count == 1
        assert prov_count == 1
        assert req_count == 1

    def test_meta_table_populated(self, tmp_path):
        from tools.export_sqlite import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "kb.sqlite"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--out", str(out),
        ])

        conn = sqlite3.connect(str(out))
        meta = dict(conn.execute("SELECT key, value FROM export_meta").fetchall())
        conn.close()

        assert meta["documents"] == "1"
        assert meta["provisions"] == "1"
        assert meta["requirements"] == "1"
        assert "exported_at" in meta

    def test_empty_dirs_produces_valid_db(self, tmp_path):
        from tools.export_sqlite import main

        out = tmp_path / "db" / "kb.sqlite"
        main([
            "--candidates-dir", str(tmp_path / "cand"),
            "--drafts-dir", str(tmp_path / "drafts"),
            "--out", str(out),
        ])

        conn = sqlite3.connect(str(out))
        doc_count = conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        conn.close()

        assert doc_count == 0
        assert out.exists()
