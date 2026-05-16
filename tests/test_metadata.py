"""Tests for metadata extraction module."""

from pathlib import Path
from unittest.mock import patch

import pytest

from standards_wiki.metadata import (
    extract_metadata,
    _extract_title,
    _extract_standard_id,
    _extract_standard_id_from_path,
    _extract_date,
    _normalize_date,
    _extract_publisher,
)


class TestExtractTitle:
    def test_extracts_markdown_heading(self):
        text = "# GB 7258-2017 机动车运行安全技术条件\n\nSome content."
        assert _extract_title(text) == "GB 7258-2017 机动车运行安全技术条件"

    def test_extracts_html_h1(self):
        text = "<html><body><h1>ISO 26262:2018</h1><p>Content</p></body></html>"
        assert _extract_title(text) == "ISO 26262:2018"

    def test_returns_none_when_no_heading(self):
        assert _extract_title("Just plain text without headings") is None

    def test_strips_whitespace(self):
        text = "#   Title with spaces   \n\nContent"
        assert _extract_title(text) == "Title with spaces"


class TestExtractStandardId:
    def test_gb_standard(self):
        assert _extract_standard_id("GB 7258-2017 机动车运行安全技术条件") == "GB7258-2017"

    def test_gb_t_standard(self):
        assert _extract_standard_id("GB/T 12345-2020") == "GB/T12345-2020"

    def test_iso_standard(self):
        assert _extract_standard_id("ISO 26262:2018") == "ISO26262:2018"

    def test_iec_standard(self):
        # IEC pattern matches "IEC 61851" but not the "-1" suffix
        assert _extract_standard_id("IEC 61851-1") == "IEC61851"

    def test_ece_regulation(self):
        # ECE pattern captures "ECE R100 Rev.3" - the Rev.3 is part of the version
        assert _extract_standard_id("ECE R100 Rev.3") == "ECER100REV.3"

    def test_returns_none_when_no_match(self):
        assert _extract_standard_id("Just a generic document") is None


class TestExtractStandardIdFromPath:
    def test_from_gb_filename(self):
        # Extracts full standard ID from filename including year
        assert _extract_standard_id_from_path(Path("gb-7258-2017.pdf")) == "GB-7258-2017"

    def test_from_iso_filename(self):
        # Extracts full standard ID from filename including year
        assert _extract_standard_id_from_path(Path("iso-26262-2018.pdf")) == "ISO-26262-2018"

    def test_returns_none_when_no_match(self):
        assert _extract_standard_id_from_path(Path("generic-document.pdf")) is None


class TestExtractDate:
    def test_extracts_release_date_yyyymmdd(self):
        text = "发布日期：2017-09-29"
        result = _extract_date(text, patterns=[r"发布日期\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"])
        assert result == "2017-09-29"

    def test_extracts_effective_date_yyyymmdd(self):
        text = "实施日期：2018-01-01"
        result = _extract_date(text, patterns=[r"实施日期\s*[:：]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2})"])
        assert result == "2018-01-01"

    def test_extracts_compact_date_before_chinese_label(self):
        text = "20170929发布"
        result = _extract_date(text, patterns=[r"(\d{4}\d{2}\d{2})\s*发布"])
        assert result == "2017-09-29"

    def test_extracts_chinese_date_format(self):
        text = "发布日期：2017年9月29日"
        result = _extract_date(text, patterns=[r"发布日期\s*[:：]?\s*(\d{4}年\d{1,2}月\d{1,2}日)"])
        assert result == "2017-09-29"

    def test_returns_none_when_no_match(self):
        assert _extract_date("No dates here", patterns=[r"(\d{4})"]) is None


class TestNormalizeDate:
    def test_normalizes_yyyymmdd_with_hyphens(self):
        assert _normalize_date("2017-09-29") == "2017-09-29"

    def test_normalizes_yyyymmdd_with_slashes(self):
        assert _normalize_date("2017/09/29") == "2017-09-29"

    def test_normalizes_chinese_date(self):
        assert _normalize_date("2017年9月29日") == "2017-09-29"

    def test_pads_single_digit_month_day(self):
        assert _normalize_date("2017-1-5") == "2017-01-05"

    def test_normalizes_compact_date(self):
        assert _normalize_date("20170929") == "2017-09-29"


class TestExtractPublisher:
    def test_extracts_chinese_publisher(self):
        text = "发布部门：中华人民共和国工业和信息化部"
        assert _extract_publisher(text) == "中华人民共和国工业和信息化部"

    def test_extracts_abbreviation(self):
        text = "Published by ISO"
        assert _extract_publisher(text) == "ISO"

    def test_returns_none_when_no_match(self):
        assert _extract_publisher("No publisher info") is None


class TestExtractMetadata:
    def test_extracts_basic_metadata(self, tmp_path):
        source_text = """# GB 7258-2017 机动车运行安全技术条件

发布日期：2017-09-29
实施日期：2018-01-01
发布部门：中华人民共和国工业和信息化部

Some content here."""

        source_path = tmp_path / "gb-7258-2017.pdf"
        source_path.write_text("dummy")

        result = extract_metadata(
            source_text,
            source_path,
            sha256="abc123",
        )

        assert "GB 7258-2017" in result["title"]
        assert result["standard_id"] == "GB7258-2017"
        assert result["release_date"] == "2017-09-29"
        assert result["effective_date"] == "2018-01-01"
        assert result["sha256"] == "abc123"
        assert result["confidence"] == "low"
        assert result["review_status"] == "draft"

    def test_includes_source_url(self, tmp_path):
        source_text = "# Test Document\n\nContent."
        source_path = tmp_path / "test.html"
        source_path.write_text("dummy")

        result = extract_metadata(
            source_text,
            source_path,
            source_url="https://example.com/doc.html",
        )

        assert result["source_url"] == "https://example.com/doc.html"

    def test_fallback_title_from_filename(self, tmp_path):
        source_text = "No headings here, just plain text."
        source_path = tmp_path / "my-standard-doc.pdf"
        source_path.write_text("dummy")

        result = extract_metadata(source_text, source_path)

        assert "My Standard Doc" in result["title"]

    def test_classifies_document_type_from_title(self, tmp_path):
        source_text = "# GB/T 12345-2020 测试标准\n\nContent."
        source_path = tmp_path / "gb-t-12345-2020.pdf"
        source_path.write_text("dummy")

        result = extract_metadata(source_text, source_path)

        assert result["document_type"] == "gb-t"

    def test_classifies_document_type_from_standard_id_when_title_is_generic(self, tmp_path):
        source_text = """# 中华人民共和国国家标准

GB 7258—2017

20170929发布
20180101实施
"""
        source_path = tmp_path / "gb-7258-2017.pdf"
        source_path.write_text("dummy")

        result = extract_metadata(source_text, source_path)

        assert result["document_type"] == "gb"
        assert result["release_date"] == "2017-09-29"
        assert result["effective_date"] == "2018-01-01"

    def test_uses_provided_document_type(self, tmp_path):
        source_text = "# Some Document\n\nContent."
        source_path = tmp_path / "test.pdf"
        source_path.write_text("dummy")

        result = extract_metadata(source_text, source_path, document_type="policy_notice")

        assert result["document_type"] == "policy_notice"
