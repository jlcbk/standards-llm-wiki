"""Tests for archive module."""

import hashlib
import os
import tempfile
from pathlib import Path

import pytest

from standards_wiki.archive import (
    archive_pdf,
    archive_html,
    compute_sha256,
    _doc_type_to_subdir,
)


class TestDocTypeToSubdir:
    def test_standard_maps_to_standards(self):
        assert _doc_type_to_subdir("standard") == "standards"

    def test_regulation_maps_to_regulations(self):
        assert _doc_type_to_subdir("regulation") == "regulations"

    def test_policy_maps_to_policies(self):
        assert _doc_type_to_subdir("policy") == "policies"

    def test_rule_maps_to_rules(self):
        assert _doc_type_to_subdir("rule") == "rules"

    def test_interpretation_maps_to_interpretations(self):
        assert _doc_type_to_subdir("interpretation") == "interpretations"

    def test_web_maps_to_web(self):
        assert _doc_type_to_subdir("web") == "web"

    def test_unknown_defaults_to_web(self):
        assert _doc_type_to_subdir("unknown") == "web"


class TestComputeSha256:
    def test_computes_hash_for_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")

        result = compute_sha256(test_file)
        expected = hashlib.sha256(b"hello world").hexdigest()
        assert result == expected

    def test_consistent_hash(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        hash1 = compute_sha256(test_file)
        hash2 = compute_sha256(test_file)
        assert hash1 == hash2

    def test_different_content_different_hash(self, tmp_path):
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content A")
        file2.write_text("content B")

        assert compute_sha256(file1) != compute_sha256(file2)


class TestArchivePdf:
    def test_archives_pdf_to_raw_standards(self, tmp_path, monkeypatch):
        # Create a dummy PDF
        source = tmp_path / "sample.pdf"
        source.write_bytes(b"%PDF-dummy content")

        # Monkeypatch the raw directory
        raw_dir = tmp_path / "raw"
        monkeypatch.setattr("standards_wiki.archive._RAW_DIR", raw_dir)

        result = archive_pdf(source, doc_type="standard", slug="gb-7258-2017")

        expected_path = raw_dir / "standards" / "gb-7258-2017.pdf"
        assert expected_path.exists()
        assert result["raw_path"] == str(expected_path)
        assert result["sha256"] == compute_sha256(expected_path)
        assert result["doc_type"] == "standard"
        assert result["original_name"] == "sample.pdf"

    def test_uses_original_name_when_no_slug(self, tmp_path, monkeypatch):
        source = tmp_path / "my-standard.pdf"
        source.write_bytes(b"%PDF-dummy")

        raw_dir = tmp_path / "raw"
        monkeypatch.setattr("standards_wiki.archive._RAW_DIR", raw_dir)

        result = archive_pdf(source, doc_type="regulation")

        expected_path = raw_dir / "regulations" / "my-standard.pdf"
        assert expected_path.exists()
        assert result["raw_path"] == str(expected_path)

    def test_raises_on_missing_file(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "raw"
        monkeypatch.setattr("standards_wiki.archive._RAW_DIR", raw_dir)

        with pytest.raises(FileNotFoundError, match="not found"):
            archive_pdf("/nonexistent/file.pdf")

    def test_creates_nested_directories(self, tmp_path, monkeypatch):
        source = tmp_path / "test.pdf"
        source.write_bytes(b"%PDF-test")

        raw_dir = tmp_path / "raw"
        monkeypatch.setattr("standards_wiki.archive._RAW_DIR", raw_dir)

        # Should create raw/standards/ even if it doesn't exist
        archive_pdf(source, doc_type="standard", slug="test-doc")

        assert (raw_dir / "standards").exists()


class TestArchiveHtml:
    def test_archives_html_to_raw_web(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "raw"
        monkeypatch.setattr("standards_wiki.archive._RAW_DIR", raw_dir)

        html = "<html><body><h1>Test</h1></body></html>"
        result = archive_html(html, slug="test-page", source_url="https://example.com")

        expected_path = raw_dir / "web" / "test-page.html"
        assert expected_path.exists()
        assert expected_path.read_text() == html
        assert result["raw_path"] == str(expected_path)
        assert result["sha256"] == compute_sha256(expected_path)
        assert result["source_url"] == "https://example.com"

    def test_creates_web_directory(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "raw"
        monkeypatch.setattr("standards_wiki.archive._RAW_DIR", raw_dir)

        archive_html("<html></html>", slug="test")

        assert (raw_dir / "web").exists()

    def test_includes_source_url(self, tmp_path, monkeypatch):
        raw_dir = tmp_path / "raw"
        monkeypatch.setattr("standards_wiki.archive._RAW_DIR", raw_dir)

        result = archive_html("<html></html>", slug="test", source_url="https://gov.cn/doc")
        assert result["source_url"] == "https://gov.cn/doc"
