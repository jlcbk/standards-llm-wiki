"""Tests for candidate writer module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from standards_wiki.writers.candidate_writer import (
    write_candidate_metadata,
    write_candidate_document,
    _CANDIDATES_DIR,
)


class TestWriteCandidateMetadata:
    def test_writes_yaml_file(self, tmp_path, monkeypatch):
        # Monkeypatch the candidates directory
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        metadata = {
            "title": "GB 7258-2017",
            "document_type": "gb",
            "standard_id": "GB7258-2017",
            "confidence": "low",
            "review_status": "draft",
        }

        result = write_candidate_metadata(metadata, "gb-7258-2017")

        expected_path = tmp_path / "_candidates" / "metadata" / "gb-7258-2017.yaml"
        assert result == str(expected_path)
        assert expected_path.exists()

        # Verify YAML content
        with open(expected_path) as f:
            loaded = yaml.safe_load(f)
        assert loaded["title"] == "GB 7258-2017"
        assert loaded["document_type"] == "gb"

    def test_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        write_candidate_metadata({"title": "Test"}, "test")

        assert (tmp_path / "_candidates" / "metadata").exists()

    def test_handles_unicode_content(self, tmp_path, monkeypatch):
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        metadata = {
            "title": "GB 7258-2017 机动车运行安全技术条件",
            "publisher": "中华人民共和国工业和信息化部",
        }

        result = write_candidate_metadata(metadata, "gb-7258")

        content = Path(result).read_text()
        assert "机动车运行安全技术条件" in content
        assert "中华人民共和国工业和信息化部" in content


class TestWriteCandidateDocument:
    def test_writes_markdown_with_frontmatter(self, tmp_path, monkeypatch):
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        content = "# Main Content\n\nSome text here."

        result = write_candidate_document(
            title="Test Document",
            content=content,
            slug="test-doc",
        )

        expected_path = tmp_path / "_candidates" / "documents" / "test-doc.md"
        assert result == str(expected_path)
        assert expected_path.exists()

        written = expected_path.read_text()
        assert "---" in written
        assert "title: Test Document" in written
        assert "type: document" in written
        assert "review_status: draft" in written
        assert "# Main Content" in written

    def test_includes_metadata_in_frontmatter(self, tmp_path, monkeypatch):
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        metadata = {
            "document_id": "gb-7258-2017",
            "standard_id": "GB7258-2017",
            "confidence": "medium",
        }

        result = write_candidate_document(
            title="GB 7258",
            content="Content here.",
            slug="gb-7258",
            metadata=metadata,
        )

        written = Path(result).read_text()
        assert "document_id: gb-7258-2017" in written
        assert "standard_id: GB7258-2017" in written
        # confidence is a default field, not overridden by metadata
        assert "confidence: low" in written

    def test_skips_none_metadata_values(self, tmp_path, monkeypatch):
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        metadata = {
            "document_id": "test",
            "release_date": None,  # Should be skipped
        }

        result = write_candidate_document(
            title="Test",
            content="Content.",
            slug="test",
            metadata=metadata,
        )

        written = Path(result).read_text()
        assert "document_id: test" in written
        assert "release_date" not in written

    def test_creates_directory_if_not_exists(self, tmp_path, monkeypatch):
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        write_candidate_document("Title", "Content", "test")

        assert (tmp_path / "_candidates" / "documents").exists()

    def test_includes_timestamps(self, tmp_path, monkeypatch):
        monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")

        result = write_candidate_document("Title", "Content", "test")

        written = Path(result).read_text()
        assert "created:" in written
        assert "updated:" in written
        assert written.count("---") == 2  # Opening and closing frontmatter
