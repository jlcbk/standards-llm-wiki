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


# ------------------------------------------------------------------
# P4-02: requirement_modality_exists
# ------------------------------------------------------------------
class TestRequirementModalityExists:
    def test_pass_when_modality_matches(self):
        checks = [{"id": "c1", "type": "requirement_modality_exists",
                    "expected": {"document_id": "gb-7258", "modality": "shall"}}]
        ctx = {"requirements": [
            {"document_id": "gb-7258", "modality": "shall", "text": "应安装"},
        ]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1
        assert result["failed"] == 0

    def test_fail_when_no_matching_modality(self):
        checks = [{"id": "c1", "type": "requirement_modality_exists",
                    "expected": {"document_id": "gb-7258", "modality": "may"}}]
        ctx = {"requirements": [
            {"document_id": "gb-7258", "modality": "shall", "text": "应安装"},
        ]}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1
        assert "modality='may'" in result["failures"][0]["reason"]

    def test_fail_when_no_requirements(self):
        checks = [{"id": "c1", "type": "requirement_modality_exists",
                    "expected": {"document_id": "gb-7258", "modality": "shall"}}]
        ctx = {"requirements": []}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1

    def test_fail_when_missing_document_id_in_expected(self):
        checks = [{"id": "c1", "type": "requirement_modality_exists",
                    "expected": {"modality": "shall"}}]
        result = run_checks(checks, {"requirements": []})
        assert result["failed"] == 1
        assert "Missing document_id" in result["failures"][0]["reason"]


# ------------------------------------------------------------------
# P4-02: evidence_quote_exists
# ------------------------------------------------------------------
class TestEvidenceQuoteExists:
    def _ctx(self):
        return {
            "provisions": [
                {
                    "document_id": "gb-7258",
                    "label": "4.1",
                    "provision_id": "gb-7258-4.1",
                    "text": "机动车应安装制动装置",
                    "title": "制动系统",
                    "evidence": {"quote": "应安装制动装置以确保安全"},
                },
            ],
            "requirements": [
                {
                    "document_id": "gb-7258",
                    "requirement_id": "gb-7258-r1",
                    "id": "r1",
                    "text": "制动性能应满足要求",
                    "title": "制动要求",
                    "evidence": [
                        {"quote": "制动力不低于规定值"},
                        {"quote": "制动距离应符合标准"},
                    ],
                },
            ],
        }

    # --- pass cases ---
    def test_pass_via_provision_label(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258", "label": "4.1",
                                 "quote_substring": "制动装置"}}]
        result = run_checks(checks, self._ctx())
        assert result["passed"] == 1

    def test_pass_via_requirement_id(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258", "id": "gb-7258-r1",
                                 "quote_substring": "制动距离"}}]
        result = run_checks(checks, self._ctx())
        assert result["passed"] == 1

    def test_pass_via_evidence_list(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258", "id": "r1",
                                 "quote_substring": "制动力不低于规定值"}}]
        result = run_checks(checks, self._ctx())
        assert result["passed"] == 1

    def test_pass_via_text_field(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258",
                                 "quote_substring": "机动车应安装"}}]
        result = run_checks(checks, self._ctx())
        assert result["passed"] == 1

    def test_pass_via_title_field(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258",
                                 "quote_substring": "制动系统"}}]
        result = run_checks(checks, self._ctx())
        assert result["passed"] == 1

    # --- fail cases ---
    def test_fail_when_quote_not_found(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258",
                                 "quote_substring": "不存在的引用"}}]
        result = run_checks(checks, self._ctx())
        assert result["failed"] == 1
        assert "不存在的引用" in result["failures"][0]["reason"]

    def test_fail_when_label_filter_mismatches(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258", "label": "9.9",
                                 "quote_substring": "制动装置"}}]
        result = run_checks(checks, self._ctx())
        assert result["failed"] == 1

    def test_fail_when_id_filter_mismatches(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "gb-7258", "id": "nonexistent-id",
                                 "quote_substring": "制动"}}]
        result = run_checks(checks, self._ctx())
        assert result["failed"] == 1


# ------------------------------------------------------------------
# P4-02: metadata_field_equals
# ------------------------------------------------------------------
class TestMetadataFieldEquals:
    def test_pass_when_field_matches(self):
        checks = [{"id": "c1", "type": "metadata_field_equals",
                    "expected": {"document_id": "gb-7258", "field": "status",
                                 "value": "现行"}}]
        ctx = {"documents": [
            {"document_id": "gb-7258", "status": "现行", "title": "运行安全"},
        ]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1

    def test_pass_matching_via_standard_id(self):
        checks = [{"id": "c1", "type": "metadata_field_equals",
                    "expected": {"document_id": "gb-7258", "field": "year",
                                 "value": 2017}}]
        ctx = {"documents": [{"standard_id": "gb-7258", "year": 2017}]}
        result = run_checks(checks, ctx)
        assert result["passed"] == 1

    def test_fail_when_value_mismatches(self):
        checks = [{"id": "c1", "type": "metadata_field_equals",
                    "expected": {"document_id": "gb-7258", "field": "status",
                                 "value": "废止"}}]
        ctx = {"documents": [
            {"document_id": "gb-7258", "status": "现行"},
        ]}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1
        assert "现行" in result["failures"][0]["reason"]
        assert "废止" in result["failures"][0]["reason"]

    def test_fail_when_document_not_found(self):
        checks = [{"id": "c1", "type": "metadata_field_equals",
                    "expected": {"document_id": "missing", "field": "status",
                                 "value": "现行"}}]
        ctx = {"documents": [{"document_id": "gb-7258", "status": "现行"}]}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1
        assert "not found" in result["failures"][0]["reason"]


# ------------------------------------------------------------------
# P4-02: topic_tag_exists
# ------------------------------------------------------------------
class TestTopicTagExists:
    def _topic_ctx(self):
        return {
            "topic_tags": {
                "document_id": "gb-7258",
                "provisions": [
                    {"label": "4.1", "topics": ["制动系统", "安全装置"]},
                    {"label": "4.2", "topics": ["照明"]},
                ],
                "requirements": [
                    {"id": "r1", "topics": ["制动性能", "安全"]},
                ],
            },
        }

    def test_pass_topic_in_provisions(self):
        checks = [{"id": "c1", "type": "topic_tag_exists",
                    "expected": {"document_id": "gb-7258", "topic": "制动系统"}}]
        result = run_checks(checks, self._topic_ctx())
        assert result["passed"] == 1

    def test_pass_topic_in_requirements(self):
        checks = [{"id": "c1", "type": "topic_tag_exists",
                    "expected": {"document_id": "gb-7258", "topic": "制动性能"}}]
        result = run_checks(checks, self._topic_ctx())
        assert result["passed"] == 1

    def test_fail_when_topic_not_found(self):
        checks = [{"id": "c1", "type": "topic_tag_exists",
                    "expected": {"document_id": "gb-7258", "topic": "排放"}}]
        result = run_checks(checks, self._topic_ctx())
        assert result["failed"] == 1
        assert "排放" in result["failures"][0]["reason"]

    def test_fail_when_document_id_mismatches(self):
        checks = [{"id": "c1", "type": "topic_tag_exists",
                    "expected": {"document_id": "other-doc", "topic": "制动系统"}}]
        result = run_checks(checks, self._topic_ctx())
        assert result["failed"] == 1
        assert "not found" in result["failures"][0]["reason"]


# ------------------------------------------------------------------
# P4-02: failure preserves explicit category / severity
# ------------------------------------------------------------------
class TestFailureCategorySeverity:
    def test_explicit_category_and_severity_preserved(self):
        checks = [{"id": "c1", "type": "document_id_exists",
                    "category": "custom_cat", "severity": "warn",
                    "expected": "missing-doc"}]
        ctx = {"documents": [{"document_id": "gb-7258"}]}
        result = run_checks(checks, ctx)
        assert result["failed"] == 1
        f = result["failures"][0]
        assert f["category"] == "custom_cat"
        assert f["severity"] == "warn"

    def test_explicit_severity_info(self):
        checks = [{"id": "c1", "type": "provision_label_exists",
                    "category": "my_cat", "severity": "info",
                    "expected": {"document_id": "x", "label": "missing"}}]
        result = run_checks(checks, {"provisions": []})
        assert result["failed"] == 1
        assert result["failures"][0]["severity"] == "info"

    def test_invalid_severity_falls_back_to_error(self):
        checks = [{"id": "c1", "type": "document_id_exists",
                    "category": "cat", "severity": "critical",
                    "expected": "missing"}]
        result = run_checks(checks, {"documents": []})
        assert result["failed"] == 1
        assert result["failures"][0]["severity"] == "error"


# ------------------------------------------------------------------
# P4-02: legacy check — infer category, severity defaults to error
# ------------------------------------------------------------------
class TestLegacyInference:
    def test_infer_category_from_type(self):
        checks = [{"id": "c1", "type": "requirement_modality_exists",
                    "expected": {"document_id": "x", "modality": "shall"}}]
        result = run_checks(checks, {"requirements": []})
        assert result["failed"] == 1
        f = result["failures"][0]
        assert f["category"] == "missed_requirement"
        assert f["severity"] == "error"

    def test_infer_category_evidence(self):
        checks = [{"id": "c1", "type": "evidence_quote_exists",
                    "expected": {"document_id": "x", "quote_substring": "q"}}]
        result = run_checks(checks, {"provisions": [], "requirements": []})
        assert result["failed"] == 1
        assert result["failures"][0]["category"] == "citation_missing"
        assert result["failures"][0]["severity"] == "error"

    def test_infer_category_metadata(self):
        checks = [{"id": "c1", "type": "metadata_field_equals",
                    "expected": {"document_id": "x", "field": "s", "value": "v"}}]
        result = run_checks(checks, {"documents": []})
        assert result["failed"] == 1
        assert result["failures"][0]["category"] == "metadata_mismatch"

    def test_infer_category_topic(self):
        checks = [{"id": "c1", "type": "topic_tag_exists",
                    "expected": {"document_id": "x", "topic": "t"}}]
        result = run_checks(checks, {"topic_tags": {"document_id": "other"}})
        assert result["failed"] == 1
        assert result["failures"][0]["category"] == "topic_mismatch"


# ------------------------------------------------------------------
# P4-02: lightweight validation — missing id/type/expected, unknown type
# ------------------------------------------------------------------
class TestLightweightValidation:
    def test_missing_id_produces_failure(self):
        checks = [{"type": "document_id_exists", "expected": "gb-7258"}]
        result = run_checks(checks, {"documents": [{"document_id": "gb-7258"}]})
        assert result["failed"] == 1
        f = result["failures"][0]
        assert f["id"] == ""
        assert "Missing id" in f["reason"]

    def test_missing_type_produces_failure(self):
        checks = [{"id": "c1", "expected": "gb-7258"}]
        result = run_checks(checks, {"documents": []})
        assert result["failed"] == 1
        f = result["failures"][0]
        assert f["id"] == "c1"
        assert "Missing type" in f["reason"]

    def test_missing_expected_produces_failure(self):
        checks = [{"id": "c1", "type": "document_id_exists"}]
        result = run_checks(checks, {"documents": []})
        assert result["failed"] == 1
        f = result["failures"][0]
        assert f["id"] == "c1"
        assert "Missing expected" in f["reason"]

    def test_unknown_type_produces_failure(self):
        checks = [{"id": "c1", "type": "nonexistent_check_type",
                    "expected": "whatever"}]
        result = run_checks(checks, {})
        assert result["failed"] == 1
        f = result["failures"][0]
        assert f["id"] == "c1"
        assert "Unknown check type" in f["reason"]

    def test_all_three_missing_counts_as_total(self):
        """Even degenerate checks count toward total."""
        checks = [
            {"type": "document_id_exists", "expected": "x"},  # no id
            {"id": "c2"},  # no type, no expected
        ]
        result = run_checks(checks, {})
        assert result["total"] == 2
        assert result["failed"] == 2
