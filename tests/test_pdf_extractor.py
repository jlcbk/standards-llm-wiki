"""Tests for PDF extractor."""

from pathlib import Path

import pytest

from standards_wiki.extractors import pdf as pdf_extractor
from standards_wiki.extractors.pdf import _clean_artifacts, _rewrite_marker_asset_links, extract_pdf


def _make_text_pdf(tmp_path, content: str, pages: int = 1, ensure_text_density: bool = True) -> Path:
    """Helper to create a simple text-based PDF with exactly `pages` pages.

    Args:
        content: Text content to put in the PDF. If empty and ensure_text_density=True,
                 generates enough text per page to pass OCR detection.
        pages: Number of pages.
        ensure_text_density: If True, ensures each page has >50 chars for OCR detection.
    """
    doc_path = tmp_path / "test.pdf"
    doc = __import__("pymupdf").open()

    if ensure_text_density and not content.strip():
        for i in range(pages):
            page = doc.new_page()
            y = 72
            page_text = (
                f"Page {i + 1} — This is substantial content for testing the PDF extractor. "
                "It contains enough text to exceed the minimum threshold for OCR detection. "
                "Additional details about the document structure and formatting are included here. "
                "This ensures the text density check works correctly for multi-page documents."
            )
            page.insert_text((72, y), page_text)
            y += 20
            for j in range(5):
                page.insert_text((72, y), f"  Detail line {j + 1}: Additional context for page {i + 1}.")
                y += 18
    else:
        lines = content.split("\n")
        for i in range(pages):
            page = doc.new_page()
            y = 72
            page_lines = lines[i::pages] if pages > 1 else lines
            for line in page_lines:
                if y > 750:
                    break
                page.insert_text((72, y), line)
                y += 18

    doc.save(doc_path)
    doc.close()
    return doc_path


# ── _clean_artifacts unit tests ──────────────────────────────────────────


class TestCleanArtifacts:
    def test_removes_picture_markers(self):
        text = "Some text\n**==> picture [114 x 58] intentionally omitted <==**\nMore text"
        result = _clean_artifacts(text)
        assert "intentionally omitted" not in result
        assert "Some text" in result
        assert "More text" in result

    def test_unwraps_em_dash_bracket(self):
        text = "GB 7258[—] 2017"
        result = _clean_artifacts(text)
        assert "GB 7258—2017" in result

    def test_unwraps_gb_t_slash_artifact(self):
        text = "GB[/] T 13594[—] 2025"
        result = _clean_artifacts(text)
        assert "GB/T 13594—2025" in result

    def test_unwraps_cjk_word_brackets(self):
        text = "2012[年版的] 3.2"
        result = _clean_artifacts(text)
        assert "2012年版的 3.2" in result

    def test_unwraps_punctuation_brackets(self):
        text = "3.2[)] and 3.2[,] 2012[年版的]"
        result = _clean_artifacts(text)
        assert "3.2) and 3.2, 2012年版的" in result

    def test_unwraps_cjk_punctuation(self):
        text = "内容[。]下一句[，]继续[、]还有[：]说明"
        result = _clean_artifacts(text)
        assert "内容。下一句，继续、还有：说明" in result

    def test_unwraps_chinese_words_in_brackets(self):
        text = "[发布] [实施] [本标准的全部技术内容为强制性]"
        result = _clean_artifacts(text)
        assert "发布 实施 本标准的全部技术内容为强制性" in result

    def test_preserves_real_reference_brackets(self):
        text = "See reference [1] and [GB 7258] for details."
        result = _clean_artifacts(text)
        assert "[1]" in result
        assert "[GB 7258]" in result

    def test_removes_br_tags(self):
        text = "|前言<br>………………………………………………………………|Ⅲ|"
        result = _clean_artifacts(text)
        assert "<br>" not in result
        assert "前言" in result

    def test_splits_concatenated_english(self):
        text = "TechnicalSpecificationsForSafety"
        result = _clean_artifacts(text)
        assert "Technical Specifications For Safety" in result

    def test_collapses_marker_cjk_character_spacing(self):
        text = "# 中 华 人 民 共 和 国 国 家 标 准"
        result = _clean_artifacts(text)
        assert "# 中华人民共和国国家标准" in result

    def test_removes_repeated_standard_headers_but_keeps_first(self):
        text = "GB/T 13594—2025\n\n正文\n\nGB/T 13594—2025\n\n更多正文"
        result = _clean_artifacts(text)
        assert result.count("GB/T 13594—2025") == 1

    def test_removes_stray_roman_numeral_headers(self):
        text = "Some text\nⅠ\nMore text\nⅤ\nEnd"
        result = _clean_artifacts(text)
        assert "Ⅰ" not in result
        assert "Ⅴ" not in result
        assert "Some text" in result
        assert "More text" in result

    def test_collapses_excess_blank_lines(self):
        text = "Line 1\n\n\n\n\nLine 2"
        result = _clean_artifacts(text)
        assert "\n\n\n\n" not in result
        assert "Line 2" in result


class TestMarkerAssetLinks:
    def test_rewrites_marker_image_links_and_copies_assets(self, tmp_path):
        marker_dir = tmp_path / "marker"
        marker_dir.mkdir()
        image = marker_dir / "_page_0_Picture_1.jpeg"
        image.write_bytes(b"image-bytes")

        target_dir = tmp_path / "sources" / "standards"
        target_dir.mkdir(parents=True)

        result, assets = _rewrite_marker_asset_links(
            "![](_page_0_Picture_1.jpeg)\n\nText",
            marker_dir=marker_dir,
            target_dir=target_dir,
            slug="gb-7258-2017",
        )

        assert "![](gb-7258-2017_assets/_page_0_Picture_1.jpeg)" in result
        assert len(assets) == 1
        assert (target_dir / "gb-7258-2017_assets" / "_page_0_Picture_1.jpeg").exists()


class TestEngineSelection:
    def test_auto_selects_marker_for_larger_text_pdf_when_available(self, monkeypatch):
        monkeypatch.setattr(pdf_extractor, "_resolve_marker_single", lambda: "/bin/marker_single")
        assert pdf_extractor._select_pdf_engine("auto", page_count=20, ocr_required=False) == "marker"

    def test_auto_keeps_pymupdf_for_ocr_suspect_pdf(self, monkeypatch):
        monkeypatch.setattr(pdf_extractor, "_resolve_marker_single", lambda: "/bin/marker_single")
        assert pdf_extractor._select_pdf_engine("auto", page_count=20, ocr_required=True) == "pymupdf4llm"


# ── extract_pdf integration tests ───────────────────────────────────────


class TestExtractPdf:
    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            extract_pdf(tmp_path / "nonexistent.pdf", slug="test", output_base=tmp_path)

    def test_extracts_text_pdf(self, tmp_path):
        doc_path = _make_text_pdf(tmp_path, content="", pages=4, ensure_text_density=True)

        result = extract_pdf(doc_path, slug="test-doc", sources_dir="standards", output_base=tmp_path / "sources")

        assert result["page_count"] == 4
        assert result["text_pages"] >= 3
        assert result["ocr_required"] is False
        assert result["extracted_chars"] > 0
        assert result["extraction_method"] == "pymupdf4llm"

    def test_detects_ocr_required_for_low_text(self, tmp_path):
        doc_path = tmp_path / "scanned.pdf"
        doc = __import__("pymupdf").open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), "x")
        doc.save(doc_path)
        doc.close()

        result = extract_pdf(doc_path, slug="scanned-doc", sources_dir="standards", output_base=tmp_path / "sources")

        assert result["ocr_required"] is True
        assert result["text_pages"] == 0

    def test_writes_markdown_file(self, tmp_path):
        content = "# Test Heading\n\nSome paragraph text with details."
        doc_path = _make_text_pdf(tmp_path, content)

        output_base = tmp_path / "sources"
        result = extract_pdf(doc_path, slug="test-md", sources_dir="standards", output_base=output_base)

        md_path = Path(result["source_text"])
        assert md_path.exists()
        content = md_path.read_text()
        assert "Test Heading" in content
        assert "Source:" in content

    def test_ocr_warning_in_output(self, tmp_path):
        doc_path = tmp_path / "scanned.pdf"
        doc = __import__("pymupdf").open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), "x")
        doc.save(doc_path)
        doc.close()

        output_base = tmp_path / "sources"
        result = extract_pdf(doc_path, slug="ocr-test", sources_dir="standards", output_base=output_base)

        md_path = Path(result["source_text"])
        content = md_path.read_text()
        assert "OCR required" in content

    def test_multi_page_pdf(self, tmp_path):
        content = "\n".join([f"Page {i} content line {j}." for i in range(1, 5) for j in range(10)])
        doc_path = _make_text_pdf(tmp_path, content, pages=4)

        result = extract_pdf(doc_path, slug="multi-page", sources_dir="standards", output_base=tmp_path / "sources")

        assert result["page_count"] == 4
        assert result["text_pages"] == 4

    def test_output_path_uses_slug(self, tmp_path):
        content = "Test content."
        doc_path = _make_text_pdf(tmp_path, content)

        output_base = tmp_path / "sources"
        result = extract_pdf(doc_path, slug="my-custom-slug", sources_dir="regulations", output_base=output_base)

        assert "my-custom-slug.md" in result["source_text"]

    def test_includes_extraction_method(self, tmp_path):
        content = "\n".join([f"Section {i}: This is substantial content for testing the extraction method reporting." for i in range(20)])
        doc_path = _make_text_pdf(tmp_path, content, pages=3)

        result = extract_pdf(doc_path, slug="test", sources_dir="standards", output_base=tmp_path / "sources")

        assert "pymupdf4llm" in result["extraction_method"]
        assert "quality" in result

    def test_quality_assessment(self, tmp_path):
        doc_path = tmp_path / "poor.pdf"
        doc = __import__("pymupdf").open()
        for i in range(5):
            page = doc.new_page()
            page.insert_text((72, 72), "x")
        doc.save(doc_path)
        doc.close()

        result = extract_pdf(doc_path, slug="poor", sources_dir="standards", output_base=tmp_path / "sources")

        assert result["quality"]["is_poor"] is True
        assert result["quality"]["omitted_images"] >= 0
