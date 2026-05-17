"""Tests for candidate IO module."""

import json
from pathlib import Path

import pytest
import yaml

from standards_wiki.candidates import (
    load_metadata,
    load_candidate_document,
    split_frontmatter,
    write_jsonl,
    read_jsonl,
)


class TestLoadMetadata:
    def test_loads_yaml_success(self, tmp_path):
        meta = {"title": "GB 7258-2017", "document_type": "gb", "confidence": "low"}
        f = tmp_path / "gb-7258-2017.yaml"
        f.write_text(yaml.dump(meta, allow_unicode=True), encoding="utf-8")

        result = load_metadata(f)

        assert result["title"] == "GB 7258-2017"
        assert result["document_type"] == "gb"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Metadata file not found"):
            load_metadata(tmp_path / "nonexistent.yaml")

    def test_handles_unicode(self, tmp_path):
        meta = {"title": "机动车运行安全技术条件", "publisher": "工业和信息化部"}
        f = tmp_path / "test.yaml"
        f.write_text(yaml.dump(meta, allow_unicode=True), encoding="utf-8")

        result = load_metadata(f)

        assert result["title"] == "机动车运行安全技术条件"

    def test_empty_yaml_returns_empty_dict(self, tmp_path):
        f = tmp_path / "empty.yaml"
        f.write_text("", encoding="utf-8")

        result = load_metadata(f)

        assert result == {}

    def test_accepts_string_path(self, tmp_path):
        meta = {"title": "Test"}
        f = tmp_path / "test.yaml"
        f.write_text(yaml.dump(meta, allow_unicode=True), encoding="utf-8")

        result = load_metadata(str(f))

        assert result["title"] == "Test"


class TestLoadCandidateDocument:
    def test_loads_document_with_frontmatter(self, tmp_path):
        content = "---\ntitle: Test\ndocument_id: gb-7258\n---\n\nBody content here."
        f = tmp_path / "test.md"
        f.write_text(content, encoding="utf-8")

        fm, body = load_candidate_document(f)

        assert fm["title"] == "Test"
        assert fm["document_id"] == "gb-7258"
        assert "Body content here." in body

    def test_loads_document_without_frontmatter(self, tmp_path):
        content = "# Just a heading\n\nSome text."
        f = tmp_path / "test.md"
        f.write_text(content, encoding="utf-8")

        fm, body = load_candidate_document(f)

        assert fm == {}
        assert body == content

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Candidate document not found"):
            load_candidate_document(tmp_path / "nonexistent.md")


class TestSplitFrontmatter:
    def test_splits_valid_frontmatter(self):
        text = "---\ntitle: Hello\nreview_status: draft\n---\n\nBody text."
        fm, body = split_frontmatter(text)

        assert fm["title"] == "Hello"
        assert fm["review_status"] == "draft"
        assert body == "Body text."

    def test_no_frontmatter_returns_empty(self):
        text = "# Heading\n\nParagraph."
        fm, body = split_frontmatter(text)

        assert fm == {}
        assert body == text

    def test_unclosed_frontmatter_returns_empty(self):
        text = "---\ntitle: Broken\n\nNo closing marker."
        fm, body = split_frontmatter(text)

        assert fm == {}
        assert body == text

    def test_empty_frontmatter(self):
        text = "---\n---\n\nBody."
        fm, body = split_frontmatter(text)

        assert fm == {}
        assert body == "Body."

    def test_preserves_multiline_body(self):
        text = "---\ntitle: T\n---\n\nLine 1\n\nLine 2\n\nLine 3"
        fm, body = split_frontmatter(text)

        assert "Line 1" in body
        assert "Line 3" in body


class TestWriteJsonl:
    def test_writes_jsonl_file(self, tmp_path):
        records = [
            {"id": 1, "name": "first"},
            {"id": 2, "name": "second"},
        ]
        out = tmp_path / "output.jsonl"

        result = write_jsonl(records, out)

        assert out.exists()
        assert result == str(out)
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["name"] == "first"

    def test_creates_parent_directories(self, tmp_path):
        out = tmp_path / "sub" / "dir" / "output.jsonl"

        write_jsonl([], out)

        assert out.exists()

    def test_unicode_preserved(self, tmp_path):
        records = [{"text": "机动车运行安全技术条件"}]
        out = tmp_path / "test.jsonl"

        write_jsonl(records, out)

        content = out.read_text(encoding="utf-8")
        assert "机动车运行安全技术条件" in content
        # Should NOT be escaped to \uXXXX
        assert "\\u" not in content

    def test_accepts_string_path(self, tmp_path):
        out = tmp_path / "test.jsonl"

        write_jsonl([{"a": 1}], str(out))

        assert out.exists()


class TestReadJsonl:
    def test_reads_jsonl_file(self, tmp_path):
        out = tmp_path / "test.jsonl"
        out.write_text(
            '{"id": 1, "name": "a"}\n{"id": 2, "name": "b"}\n',
            encoding="utf-8",
        )

        result = read_jsonl(out)

        assert len(result) == 2
        assert result[0]["name"] == "a"

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="JSONL file not found"):
            read_jsonl(tmp_path / "nonexistent.jsonl")

    def test_skips_blank_lines(self, tmp_path):
        out = tmp_path / "test.jsonl"
        out.write_text('{"a": 1}\n\n{"b": 2}\n\n', encoding="utf-8")

        result = read_jsonl(out)

        assert len(result) == 2


class TestJsonlRoundTrip:
    def test_round_trip_preserves_data(self, tmp_path):
        records = [
            {"id": "gb-7258-2017-11-6", "modality": "must", "text": "应安装"},
            {"id": "gb-7258-2017-11-7", "modality": "must_not", "text": "不得改装"},
        ]
        out = tmp_path / "roundtrip.jsonl"

        write_jsonl(records, out)
        loaded = read_jsonl(out)

        assert loaded == records
        assert loaded[0]["text"] == "应安装"
        assert loaded[1]["text"] == "不得改装"
