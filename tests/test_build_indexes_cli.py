"""Tests for build_indexes CLI."""

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

    return cand, drafts


class TestBuildIndexesCLI:
    def test_generates_index_files(self, tmp_path):
        from tools.build_indexes import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "indexes"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--output-dir", str(out),
        ])

        assert (out / "documents-index.md").exists()
        assert (out / "provisions-index.md").exists()
        assert (out / "requirements-index.md").exists()
        assert (out / "effective-dates-index.md").exists()

    def test_documents_index_contains_doc(self, tmp_path):
        from tools.build_indexes import main

        cand, drafts = _write_fixtures(tmp_path)
        out = tmp_path / "indexes"

        main([
            "--candidates-dir", str(cand),
            "--drafts-dir", str(drafts),
            "--output-dir", str(out),
        ])

        content = (out / "documents-index.md").read_text(encoding="utf-8")
        assert "gb-test-2024" in content

    def test_empty_dirs_no_error(self, tmp_path):
        from tools.build_indexes import main

        out = tmp_path / "indexes"
        main([
            "--candidates-dir", str(tmp_path / "cand"),
            "--drafts-dir", str(tmp_path / "drafts"),
            "--output-dir", str(out),
        ])
        assert (out / "documents-index.md").exists()
