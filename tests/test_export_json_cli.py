"""Tests for export_json CLI."""

import json

import yaml

from standards_wiki.candidates import write_jsonl


def _write_fixtures(tmp_path, doc_id="gb-test-2024"):
    """Create minimal candidate fixtures."""
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


class TestExportJsonCLI:
    def test_exports_all_json_files(self, tmp_path):
        from tools.export_json import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "json"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--output-dir", str(out),
        ])

        assert (out / "documents.json").exists()
        assert (out / "provisions.json").exists()
        assert (out / "requirements.json").exists()
        assert (out / "manifest.json").exists()

    def test_documents_json_content(self, tmp_path):
        from tools.export_json import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "json"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--output-dir", str(out),
        ])

        docs = json.loads((out / "documents.json").read_text(encoding="utf-8"))
        assert len(docs) == 1
        assert docs[0]["document_id"] == "gb-test-2024"

    def test_manifest_record_counts(self, tmp_path):
        from tools.export_json import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "db" / "json"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--output-dir", str(out),
        ])

        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["documents"] == 1
        assert manifest["provisions"] == 1
        assert manifest["requirements"] == 1

    def test_empty_dirs_produces_empty_json(self, tmp_path):
        from tools.export_json import main

        out = tmp_path / "db" / "json"
        main([
            "--candidates-dir", str(tmp_path / "cand"),
            "--drafts-dir", str(tmp_path / "drafts"),
            "--output-dir", str(out),
        ])

        docs = json.loads((out / "documents.json").read_text(encoding="utf-8"))
        assert docs == []
