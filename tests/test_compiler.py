"""Tests for document compiler module."""

import pytest
import yaml

from standards_wiki.compiler import compile_document


def _write_candidates(tmp_path, doc_id, metadata, doc_content):
    """Helper: write candidate metadata and document under tmp_path."""
    meta_dir = tmp_path / "_candidates" / "metadata"
    doc_dir = tmp_path / "_candidates" / "documents"
    meta_dir.mkdir(parents=True, exist_ok=True)
    doc_dir.mkdir(parents=True, exist_ok=True)

    (meta_dir / f"{doc_id}.yaml").write_text(
        yaml.dump(metadata, allow_unicode=True), encoding="utf-8"
    )
    (doc_dir / f"{doc_id}.md").write_text(doc_content, encoding="utf-8")


class TestCompileDocument:
    def test_compiles_with_complete_metadata(self, tmp_path):
        meta = {
            "title": "GB 7258-2017",
            "document_type": "gb",
            "standard_id": "GB7258-2017",
            "source_text": "sources/standards/gb-7258-2017.md",
            "raw_path": "raw/standards/gb-7258-2017.pdf",
            "confidence": "low",
        }
        doc = "# 机动车运行安全技术条件\n\nBody text."
        _write_candidates(tmp_path, "gb-7258-2017", meta, doc)

        result = compile_document(
            "gb-7258-2017",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        assert result["document_id"] == "gb-7258-2017"
        assert result["title"] == "GB 7258-2017"
        assert result["review_status"] == "draft"
        assert result["generated_from"] == "candidate"

        page = (tmp_path / "output" / "gb-7258-2017.md").read_text(encoding="utf-8")
        assert "机动车运行安全技术条件" in page
        assert "Body text." in page

    def test_frontmatter_has_required_fields(self, tmp_path):
        meta = {
            "title": "Test Standard",
            "document_type": "iso",
            "standard_id": "ISO26262:2018",
            "source_text": "sources/test.md",
            "raw_path": "raw/test.pdf",
            "confidence": "medium",
        }
        _write_candidates(tmp_path, "test-std", meta, "Body.")

        compile_document(
            "test-std",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        page = (tmp_path / "output" / "test-std.md").read_text(encoding="utf-8")
        fm_end = page.index("---", 3)
        fm = yaml.safe_load(page[3:fm_end])

        assert fm["document_id"] == "test-std"
        assert fm["review_status"] == "draft"
        assert fm["confidence"] == "medium"
        assert fm["generated_from"] == "candidate"
        assert fm["standard_id"] == "ISO26262:2018"

    def test_handles_unknown_optional_fields(self, tmp_path):
        meta = {"title": "Minimal"}
        _write_candidates(tmp_path, "minimal", meta, "Minimal body.")

        result = compile_document(
            "minimal",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        page = (tmp_path / "output" / "minimal.md").read_text(encoding="utf-8")
        fm_end = page.index("---", 3)
        fm = yaml.safe_load(page[3:fm_end])

        assert fm["document_type"] == "unknown"
        assert fm["standard_id"] == "unknown"
        assert fm["source_text"] == "unknown"
        assert fm["raw_path"] == "unknown"

    def test_preserves_body_content(self, tmp_path):
        meta = {"title": "T"}
        body = "# Heading\n\nParagraph 1\n\nParagraph 2\n\n- list item"
        _write_candidates(tmp_path, "body-test", meta, body)

        compile_document(
            "body-test",
            candidates_dir=tmp_path / "_candidates",
            output_dir=tmp_path / "output",
        )

        page = (tmp_path / "output" / "body-test.md").read_text(encoding="utf-8")
        assert "Paragraph 1" in page
        assert "Paragraph 2" in page
        assert "- list item" in page

    def test_refuses_overwrite_without_flag(self, tmp_path):
        meta = {"title": "T"}
        _write_candidates(tmp_path, "dup", meta, "Body.")

        output_dir = tmp_path / "output"
        compile_document("dup", candidates_dir=tmp_path / "_candidates", output_dir=output_dir)

        with pytest.raises(FileExistsError, match="already exists"):
            compile_document("dup", candidates_dir=tmp_path / "_candidates", output_dir=output_dir)

    def test_overwrite_with_flag(self, tmp_path):
        meta = {"title": "T"}
        _write_candidates(tmp_path, "ow", meta, "Body v1.")

        output_dir = tmp_path / "output"
        compile_document("ow", candidates_dir=tmp_path / "_candidates", output_dir=output_dir)

        meta["title"] = "T v2"
        _write_candidates(tmp_path, "ow", meta, "Body v2.")

        result = compile_document(
            "ow",
            candidates_dir=tmp_path / "_candidates",
            output_dir=output_dir,
            overwrite=True,
        )

        assert result["title"] == "T v2"
        page = (output_dir / "ow.md").read_text(encoding="utf-8")
        assert "Body v2." in page

    def test_missing_metadata_raises(self, tmp_path):
        doc_dir = tmp_path / "_candidates" / "documents"
        doc_dir.mkdir(parents=True)
        (doc_dir / "missing.md").write_text("Body", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Metadata file not found"):
            compile_document(
                "missing",
                candidates_dir=tmp_path / "_candidates",
                output_dir=tmp_path / "output",
            )

    def test_missing_document_raises(self, tmp_path):
        meta_dir = tmp_path / "_candidates" / "metadata"
        meta_dir.mkdir(parents=True)
        (meta_dir / "missing.yaml").write_text("title: T\n", encoding="utf-8")

        with pytest.raises(FileNotFoundError, match="Candidate document not found"):
            compile_document(
                "missing",
                candidates_dir=tmp_path / "_candidates",
                output_dir=tmp_path / "output",
            )

    def test_deterministic_output(self, tmp_path):
        meta = {"title": "Det", "document_type": "gb", "confidence": "low"}
        _write_candidates(tmp_path, "det", meta, "Deterministic body.")

        output_dir = tmp_path / "output"
        compile_document("det", candidates_dir=tmp_path / "_candidates", output_dir=output_dir)
        first = (output_dir / "det.md").read_text(encoding="utf-8")

        (output_dir / "det.md").unlink()
        compile_document("det", candidates_dir=tmp_path / "_candidates", output_dir=output_dir)
        second = (output_dir / "det.md").read_text(encoding="utf-8")

        assert first == second
