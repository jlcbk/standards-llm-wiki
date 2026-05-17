"""Tests for provision page generator."""

import pytest
import yaml

from standards_wiki.compiler import generate_provision_pages
from standards_wiki.candidates import write_jsonl


def _write_provision_fixtures(tmp_path, doc_id, provisions, requirements=None):
    """Helper: write provision and optional requirement JSONL under tmp_path."""
    base = tmp_path / "_candidates"
    prov_dir = base / "provisions"
    write_jsonl(provisions, prov_dir / f"{doc_id}.jsonl")

    if requirements is not None:
        req_dir = base / "requirements"
        write_jsonl(requirements, req_dir / f"{doc_id}.jsonl")


def _make_provision(provision_id, label="4.1", text="要求内容", **kw):
    base = {
        "document_id": "test-doc",
        "provision_id": provision_id,
        "label": label,
        "kind": "clause",
        "title": "unknown",
        "text": text,
        "locator": {"label": label},
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
        "confidence": "medium",
        "review_status": "machine_extracted",
        "evidence": {"quote": text},
    }
    base.update(kw)
    return base


def _make_requirement(req_id, provision_id, modality="must", **kw):
    base = {
        "requirement_id": req_id,
        "document_id": "test-doc",
        "provision_id": provision_id,
        "modality": modality,
        "subject": "unknown",
        "action": "unknown",
        "object": "unknown",
        "condition": "unknown",
        "exception": "unknown",
        "evidence": {"quote": "应安装"},
        "confidence": "medium",
        "review_status": "machine_extracted",
    }
    base.update(kw)
    return base


class TestGenerateProvisionPages:
    def test_generates_pages_for_each_provision(self, tmp_path):
        provisions = [
            _make_provision("test-4-1", "4.1", "应安装A"),
            _make_provision("test-4-2", "4.2", "应安装B"),
        ]
        _write_provision_fixtures(tmp_path, "test-doc", provisions)

        results = generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        assert len(results) == 2
        assert all(r["status"] == "generated" for r in results)

        # Check files exist
        page1 = tmp_path / "output" / "test-doc" / "test-4-1.md"
        page2 = tmp_path / "output" / "test-doc" / "test-4-2.md"
        assert page1.exists()
        assert page2.exists()

    def test_page_has_review_status_machine_extracted(self, tmp_path):
        provisions = [_make_provision("test-4-1", "4.1", "应安装")]
        _write_provision_fixtures(tmp_path, "test-doc", provisions)

        generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        page = (tmp_path / "output" / "test-doc" / "test-4-1.md").read_text(encoding="utf-8")
        assert "machine_extracted" in page

    def test_page_has_warning_banner(self, tmp_path):
        provisions = [_make_provision("test-4-1", "4.1", "内容")]
        _write_provision_fixtures(tmp_path, "test-doc", provisions)

        generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        page = (tmp_path / "output" / "test-doc" / "test-4-1.md").read_text(encoding="utf-8")
        assert "WARNING" in page
        assert "Machine-extracted" in page or "machine" in page.lower()

    def test_page_has_source_locator(self, tmp_path):
        provisions = [_make_provision("test-4-1", "4.1", "内容")]
        _write_provision_fixtures(tmp_path, "test-doc", provisions)

        generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        page = (tmp_path / "output" / "test-doc" / "test-4-1.md").read_text(encoding="utf-8")
        assert "4.1" in page
        assert "sources/test.md" in page

    def test_embeds_requirements(self, tmp_path):
        provisions = [_make_provision("test-4-1", "4.1", "应安装ABS")]
        requirements = [
            _make_requirement("test-4-1-r1", "test-4-1", modality="must"),
        ]
        _write_provision_fixtures(tmp_path, "test-doc", provisions, requirements)

        generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        page = (tmp_path / "output" / "test-doc" / "test-4-1.md").read_text(encoding="utf-8")
        assert "test-4-1-r1" in page
        assert "must" in page

    def test_refuses_overwrite_without_flag(self, tmp_path):
        provisions = [_make_provision("test-4-1", "4.1", "内容")]
        _write_provision_fixtures(tmp_path, "test-doc", provisions)

        generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        results = generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        assert results[0]["status"] == "skipped_exists"

    def test_overwrite_with_flag(self, tmp_path):
        provisions = [_make_provision("test-4-1", "4.1", "内容")]
        _write_provision_fixtures(tmp_path, "test-doc", provisions)

        generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        results = generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
            overwrite=True,
        )

        assert results[0]["status"] == "generated"

    def test_missing_provisions_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Provisions file not found"):
            generate_provision_pages(
                "nonexistent",
                candidates_dir=tmp_path / "_candidates",
                output_dir=tmp_path / "output",
            )

    def test_output_under_candidates_dir(self, tmp_path):
        """Default output should be under _candidates/provision-pages/."""
        provisions = [_make_provision("test-4-1", "4.1", "内容")]
        _write_provision_fixtures(tmp_path, "test-doc", provisions)

        from pathlib import Path
        output_dir = tmp_path / "_candidates" / "provision-pages"

        generate_provision_pages(
            "test-doc",
            candidates_dir=tmp_path / "_candidates",
            output_dir=output_dir,
        )

        assert (output_dir / "test-doc" / "test-4-1.md").exists()
