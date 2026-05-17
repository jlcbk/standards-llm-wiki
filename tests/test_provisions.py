"""Tests for provision splitter module."""

import json

import pytest

from standards_wiki.provisions import (
    split_provisions,
    split_provisions_from_candidates,
    _make_provision_id,
    _classify_kind,
)
from standards_wiki.candidates import write_jsonl, read_jsonl

import yaml


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


class TestMakeProvisionId:
    def test_numeric_label(self):
        assert _make_provision_id("gb-7258-2017", "11.6") == "gb-7258-2017-11-6"

    def test_article_label(self):
        assert _make_provision_id("cn-law-2024", "第一条") == "cn-law-2024-第一条"

    def test_annex_label(self):
        assert _make_provision_id("iso-26262", "Annex A") == "iso-26262-annex-a"

    def test_path_safe(self):
        pid = _make_provision_id("test", "4.1.2")
        assert "/" not in pid
        assert " " not in pid


class TestClassifyKind:
    def test_article(self):
        assert _classify_kind("第一条") == "article"

    def test_annex(self):
        assert _classify_kind("附录 A") == "annex"
        assert _classify_kind("Annex B") == "annex"

    def test_section(self):
        assert _classify_kind("4") == "section"

    def test_clause(self):
        assert _classify_kind("4.1") == "clause"
        assert _classify_kind("11.6.1") == "clause"


class TestSplitProvisions:
    def test_numeric_labels(self):
        text = (
            "1 范围\n\n本标准规定了...\n\n"
            "4.1 一般要求\n\n机动车应...\n\n"
            "4.1.1 具体要求\n\n车辆须...\n\n"
            "11.6 座椅要求\n\n乘用车座椅...\n"
        )
        provisions = split_provisions(text, "gb-7258-2017")

        assert len(provisions) == 4
        assert provisions[0]["label"] == "1"
        assert provisions[1]["label"] == "4.1"
        assert provisions[2]["label"] == "4.1.1"
        assert provisions[3]["label"] == "11.6"

    def test_chinese_article_labels(self):
        text = (
            "第一条 目的\n\n为了规范...\n\n"
            "第二条 适用范围\n\n本条例适用于...\n\n"
            "第三条 定义\n\n下列用语含义...\n"
        )
        provisions = split_provisions(text, "cn-law-2024")

        assert len(provisions) == 3
        assert provisions[0]["label"] == "第一条"
        assert provisions[0]["kind"] == "article"
        assert provisions[1]["label"] == "第二条"
        assert provisions[2]["label"] == "第三条"

    def test_annex_labels(self):
        text = (
            "4.1 要求\n\n内容...\n\n"
            "附录 A: 测试方法\n\n测试步骤...\n\n"
            "Annex B: 规范性引用\n\n引用列表...\n"
        )
        provisions = split_provisions(text, "iso-26262")

        annexes = [p for p in provisions if p["kind"] == "annex"]
        assert len(annexes) >= 2

    def test_fallback_when_no_labels(self):
        text = "This is a plain text document with no labeled sections."
        provisions = split_provisions(text, "plain-doc")

        assert len(provisions) == 1
        assert provisions[0]["kind"] == "unknown"
        assert provisions[0]["confidence"] == "low"
        assert provisions[0]["label"] == "fallback"

    def test_provision_records_have_required_fields(self):
        text = "4.1 要求\n\n机动车应安装...\n"
        provisions = split_provisions(
            text, "gb-test",
            source_text="sources/test.md",
            raw_path="raw/test.pdf",
        )

        p = provisions[0]
        assert "document_id" in p
        assert "provision_id" in p
        assert "label" in p
        assert "kind" in p
        assert "title" in p
        assert "text" in p
        assert "locator" in p
        assert "source_text" in p
        assert "raw_path" in p
        assert "confidence" in p
        assert "review_status" in p
        assert "evidence" in p

    def test_review_status_is_machine_extracted(self):
        text = "4.1 要求\n\n内容...\n"
        provisions = split_provisions(text, "test")

        assert all(p["review_status"] == "machine_extracted" for p in provisions)

    def test_quote_preserved(self):
        text = "11.6 座椅要求\n\n乘用车应安装安全座椅，不得擅自改装。\n"
        provisions = split_provisions(text, "gb-7258-2017")

        assert "乘用车应安装安全座椅，不得擅自改装。" in provisions[0]["evidence"]["quote"]

    def test_locater_has_label(self):
        text = "4.1 要求\n\n内容\n"
        provisions = split_provisions(text, "test")

        assert provisions[0]["locator"]["label"] == "4.1"


class TestSplitProvisionsFromCandidates:
    def test_reads_candidates_and_splits(self, tmp_path):
        meta = {
            "title": "GB Test",
            "source_text": "sources/test.md",
            "raw_path": "raw/test.pdf",
            "confidence": "medium",
        }
        doc = "4.1 要求\n\n内容A\n\n4.2 其他\n\n内容B\n"
        _write_candidates(tmp_path, "test-std", meta, doc)

        provisions = split_provisions_from_candidates(
            "test-std", candidates_dir=tmp_path / "_candidates"
        )

        assert len(provisions) == 2
        assert provisions[0]["document_id"] == "test-std"
        assert provisions[0]["source_text"] == "sources/test.md"

    def test_missing_metadata_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            split_provisions_from_candidates(
                "nonexistent", candidates_dir=tmp_path / "_candidates"
            )


class TestProvisionJsonlRoundTrip:
    def test_jsonl_round_trip(self, tmp_path):
        text = "4.1 要求\n\n应安装\n\n4.2 禁止\n\n不得改装\n"
        provisions = split_provisions(text, "gb-test")

        out = tmp_path / "provisions" / "gb-test.jsonl"
        write_jsonl(provisions, out)
        loaded = read_jsonl(out)

        assert len(loaded) == 2
        assert loaded[0]["label"] == "4.1"
        assert loaded[1]["label"] == "4.2"
        assert loaded[0]["evidence"]["quote"] == "应安装"
