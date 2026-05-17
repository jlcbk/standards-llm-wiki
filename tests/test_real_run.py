"""Tests for the real sample runner."""

import json

import pytest
import yaml

from standards_wiki.candidates import write_jsonl
from standards_wiki.real_run import run_phase2


def _setup_candidates(tmp_path, doc_id="test-doc"):
    """Create minimal candidate fixtures for a successful pipeline run."""
    cdir = tmp_path / "_candidates"
    (cdir / "metadata").mkdir(parents=True)
    (cdir / "documents").mkdir(parents=True)

    meta = {
        "document_id": doc_id,
        "title": "Test Standard",
        "review_status": "draft",
        "document_type": "gb",
        "standard_id": "TEST-001",
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
        "confidence": "medium",
    }
    (cdir / "metadata" / f"{doc_id}.yaml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8",
    )
    (cdir / "documents" / f"{doc_id}.md").write_text(
        "# Test\n\n4.1 应安装制动装置。\n\n4.2 不得改装。\n",
        encoding="utf-8",
    )
    return cdir


class TestRunPhase2:
    def test_successful_run(self, tmp_path):
        cdir = _setup_candidates(tmp_path)
        report = run_phase2(
            "test-doc",
            candidates_dir=cdir,
            draft_dir=tmp_path / "drafts",
            provision_pages_dir=tmp_path / "pages",
            review_dir=tmp_path / "reviews",
            overwrite=True,
        )

        assert report["status"] == "ok"
        assert report["document_id"] == "test-doc"
        assert report["counts"]["provisions"] >= 2
        assert report["counts"]["requirements"] >= 1
        assert "draft_document" in report["outputs"]
        assert "provisions_jsonl" in report["outputs"]
        assert "requirements_jsonl" in report["outputs"]

    def test_writes_review_report(self, tmp_path):
        cdir = _setup_candidates(tmp_path)
        review_dir = tmp_path / "reviews"
        run_phase2(
            "test-doc",
            candidates_dir=cdir,
            draft_dir=tmp_path / "drafts",
            provision_pages_dir=tmp_path / "pages",
            review_dir=review_dir,
            overwrite=True,
        )

        report_path = review_dir / "test-doc.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["document_id"] == "test-doc"
        assert "status" in data
        assert "counts" in data

    def test_missing_metadata_fails(self, tmp_path):
        report = run_phase2(
            "nonexistent",
            candidates_dir=tmp_path / "_candidates",
            draft_dir=tmp_path / "drafts",
            provision_pages_dir=tmp_path / "pages",
            review_dir=tmp_path / "reviews",
        )

        assert report["status"] == "failed"
        assert len(report["errors"]) > 0

    def test_overwrite_false_skips_existing(self, tmp_path):
        cdir = _setup_candidates(tmp_path)
        draft_dir = tmp_path / "drafts"

        run_phase2(
            "test-doc",
            candidates_dir=cdir,
            draft_dir=draft_dir,
            provision_pages_dir=tmp_path / "pages",
            review_dir=tmp_path / "reviews",
            overwrite=True,
        )
        report = run_phase2(
            "test-doc",
            candidates_dir=cdir,
            draft_dir=draft_dir,
            provision_pages_dir=tmp_path / "pages",
            review_dir=tmp_path / "reviews",
            overwrite=False,
        )

        # Second run hits FileExistsError on compile → failed
        assert report["status"] == "failed"
        assert any("already exists" in e for e in report["errors"])

    def test_validation_errors_counted(self, tmp_path):
        cdir = _setup_candidates(tmp_path)

        # Write a provisions JSONL with a missing evidence quote to trigger validation error
        prov_dir = cdir / "provisions"
        bad_provisions = [{"provision_id": "test-doc-4-1", "document_id": "test-doc"}]
        write_jsonl(bad_provisions, prov_dir / "test-doc.jsonl")

        report = run_phase2(
            "test-doc",
            candidates_dir=cdir,
            draft_dir=tmp_path / "drafts",
            provision_pages_dir=tmp_path / "pages",
            review_dir=tmp_path / "reviews",
            overwrite=True,
        )

        # Pipeline succeeds but validation may catch issues
        assert "validation_errors" in report["counts"]

    def test_report_has_all_fields(self, tmp_path):
        cdir = _setup_candidates(tmp_path)
        report = run_phase2(
            "test-doc",
            candidates_dir=cdir,
            draft_dir=tmp_path / "drafts",
            provision_pages_dir=tmp_path / "pages",
            review_dir=tmp_path / "reviews",
            overwrite=True,
        )

        assert "document_id" in report
        assert "status" in report
        assert "outputs" in report
        assert "counts" in report
        assert "warnings" in report
        assert "errors" in report
        for key in ("provisions", "requirements", "validation_errors", "validation_warnings"):
            assert key in report["counts"]
