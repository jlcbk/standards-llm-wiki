"""Tests for deterministic candidate evaluation."""

import json

import pytest

from standards_wiki.eval import load_checks, run_checks


def _write_jsonl(records, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


class TestLoadChecks:
    def test_loads_valid_jsonl(self, tmp_path):
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "gb-7258"},
            {"id": "c2", "type": "provision_label_exists", "expected": {"document_id": "gb-7258", "label": "4.1"}},
        ]
        path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, path)

        result = load_checks(path)
        assert len(result) == 2
        assert result[0]["id"] == "c1"
        assert result[1]["type"] == "provision_label_exists"

    def test_skips_blank_lines(self, tmp_path):
        path = tmp_path / "checks.jsonl"
        path.write_text('{"id":"c1","type":"document_id_exists","expected":"x"}\n\n{"id":"c2","type":"document_id_exists","expected":"y"}\n', encoding="utf-8")

        result = load_checks(path)
        assert len(result) == 2

    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_checks(tmp_path / "nope.jsonl")


class TestDocumentIdExists:
    def test_pass_when_found_in_documents(self):
        checks = [{"id": "c1", "type": "document_id_exists", "expected": "gb-7258"}]
        ctx = {"documents": [{"document_id": "gb-7258", "title": "运行安全"}]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1
        assert result["failed"] == 0

    def test_pass_when_found_in_provisions(self):
        checks = [{"id": "c1", "type": "document_id_exists", "expected": "gb-7258"}]
        ctx = {"provisions": [{"document_id": "gb-7258", "label": "4.1"}]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1

    def test_fail_when_not_found(self):
        checks = [{"id": "c1", "type": "document_id_exists", "expected": "gb-missing"}]
        ctx = {"documents": [{"document_id": "gb-7258"}]}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1
        assert result["failures"][0]["id"] == "c1"
        assert "not found" in result["failures"][0]["reason"]


class TestProvisionLabelExists:
    def test_pass_when_label_matches(self):
        checks = [{"id": "c1", "type": "provision_label_exists", "expected": {"document_id": "gb-7258", "label": "4.1"}}]
        ctx = {"provisions": [
            {"document_id": "gb-7258", "label": "4.1", "text": "应安装制动装置"},
        ]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1

    def test_fail_when_label_missing(self):
        checks = [{"id": "c1", "type": "provision_label_exists", "expected": {"document_id": "gb-7258", "label": "9.9"}}]
        ctx = {"provisions": [
            {"document_id": "gb-7258", "label": "4.1", "text": "..."},
        ]}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1
        assert "9.9" in result["failures"][0]["reason"]


class TestKeywordSearch:
    def test_count_keyword_in_text(self):
        checks = [{"id": "c1", "type": "keyword_search", "expected": {"keyword": "制动", "min_count": 2}}]
        ctx = {"provisions": [
            {"text": "应安装制动装置", "title": "制动系统"},
            {"text": "制动性能应满足要求"},
        ]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1

    def test_fail_when_below_min_count(self):
        checks = [{"id": "c1", "type": "keyword_search", "expected": {"keyword": "制动", "min_count": 5}}]
        ctx = {"provisions": [{"text": "制动装置"}]}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1
        assert "need >= 5" in result["failures"][0]["reason"]

    def test_searches_evidence_quote(self):
        checks = [{"id": "c1", "type": "keyword_search", "expected": {"keyword": "制动", "min_count": 1}}]
        ctx = {"requirements": [
            {"evidence": {"quote": "应安装制动装置"}},
        ]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1

    def test_searches_title(self):
        checks = [{"id": "c1", "type": "keyword_search", "expected": {"keyword": "安全", "min_count": 1}}]
        ctx = {"provisions": [{"title": "安全要求", "text": ""}]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1

    def test_evidence_list_keyword_hits(self):
        checks = [{"id": "c1", "type": "keyword_search", "expected": {"keyword": "制动", "min_count": 2}}]
        ctx = {"requirements": [
            {"evidence": [
                {"quote": "应安装制动装置"},
                {"quote": "制动性能应满足要求"},
            ]},
        ]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1


class TestRunChecksMixed:
    def test_mixed_pass_and_fail(self):
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "gb-7258"},
            {"id": "c2", "type": "document_id_exists", "expected": "missing-doc"},
            {"id": "c3", "type": "provision_label_exists", "expected": {"document_id": "gb-7258", "label": "4.1"}},
        ]
        ctx = {
            "documents": [{"document_id": "gb-7258"}],
            "provisions": [{"document_id": "gb-7258", "label": "4.1", "text": "..."}],
        }
        result = run_checks(checks, ctx)
        assert result["total"] == 3
        assert result["passed"] == 2
        assert result["failed"] == 1
        assert result["failures"][0]["id"] == "c2"

    def test_empty_checks(self):
        result = run_checks([], {"documents": []})
        assert result["total"] == 0
        assert result["passed"] == 0
