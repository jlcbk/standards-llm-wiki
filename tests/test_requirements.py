"""Tests for requirement extractor module."""

import json

import pytest
import yaml

from standards_wiki.requirements import (
    detect_modality,
    extract_requirements_from_provision,
    extract_requirements_from_provisions,
    extract_requirements_from_jsonl,
)
from standards_wiki.candidates import write_jsonl, read_jsonl


def _make_provision(label="4.1", text="", **overrides):
    """Helper: create a minimal provision dict."""
    base = {
        "document_id": "test-doc",
        "provision_id": f"test-doc-{label}",
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
    base.update(overrides)
    return base


class TestDetectModality:
    # Chinese must signals
    @pytest.mark.parametrize("text", [
        "车辆必须安装安全带",
        "机动车应当符合要求",
        "驾驶员须持有驾照",
        "乘用车应配备ABS",
    ])
    def test_cn_must(self, text):
        assert detect_modality(text) == "must"

    # Chinese must_not signals
    @pytest.mark.parametrize("text", [
        "不得擅自改装车辆",
        "禁止使用超标电池",
        "不应超过限速",
    ])
    def test_cn_must_not(self, text):
        assert detect_modality(text) == "must_not"

    # Chinese should signals
    @pytest.mark.parametrize("text", [
        "建议定期检查",
        "宜采用节能方案",
    ])
    def test_cn_should(self, text):
        assert detect_modality(text) == "should"

    # Chinese may signals
    @pytest.mark.parametrize("text", [
        "可以使用替代方案",
        "可委托第三方检测",
    ])
    def test_cn_may(self, text):
        assert detect_modality(text) == "may"

    # Chinese define signals
    @pytest.mark.parametrize("text", [
        "机动车是指由动力装置驱动的车辆",
        "安全带定义为约束乘员的装置",
    ])
    def test_cn_define(self, text):
        assert detect_modality(text) == "define"

    # English must signals
    @pytest.mark.parametrize("text", [
        "The vehicle shall be equipped with ABS",
        "Manufacturers must submit test reports",
        "The system is required to function at -40C",
    ])
    def test_en_must(self, text):
        assert detect_modality(text) == "must"

    # English must_not signals
    @pytest.mark.parametrize("text", [
        "The vehicle shall not exceed weight limits",
        "It must not be used on public roads",
        "Prohibited in residential areas",
    ])
    def test_en_must_not(self, text):
        assert detect_modality(text) == "must_not"

    # English should signals
    @pytest.mark.parametrize("text", [
        "It is recommended to check monthly",
        "Manufacturers should provide documentation",
    ])
    def test_en_should(self, text):
        assert detect_modality(text) == "should"

    # English may signals
    @pytest.mark.parametrize("text", [
        "Alternative methods may be used",
        "Testing is permitted at accredited labs",
    ])
    def test_en_may(self, text):
        assert detect_modality(text) == "may"

    # English define signals
    @pytest.mark.parametrize("text", [
        "Vehicle means any motorized transport",
        "The term refers to the braking system",
        "Safety is defined as the absence of risk",
    ])
    def test_en_define(self, text):
        assert detect_modality(text) == "define"

    def test_unknown_when_no_signal(self):
        assert detect_modality("本标准规定了技术条件") == "unknown"

    def test_prohibitions_not_misclassified_as_must(self):
        """Must_not must take priority over must for negative patterns."""
        assert detect_modality("不得改装，应保持原状") == "must_not"
        assert detect_modality("shall not exceed the limit") == "must_not"


class TestExtractRequirementsFromProvision:
    def test_extracts_requirement_with_modality(self):
        p = _make_provision(text="机动车应安装安全座椅")
        reqs = extract_requirements_from_provision(p, req_counter=1)

        assert len(reqs) == 1
        r = reqs[0]
        assert r["modality"] == "must"
        assert r["document_id"] == "test-doc"
        assert r["provision_id"] == "test-doc-4.1"
        assert r["requirement_id"] == "test-doc-4.1-r1"
        assert r["subject"] == "unknown"
        assert r["action"] == "unknown"
        assert r["object"] == "unknown"
        assert r["condition"] == "unknown"
        assert r["exception"] == "unknown"
        assert r["review_status"] == "machine_extracted"

    def test_skips_unknown_modality(self):
        p = _make_provision(text="本标准规定了技术条件")
        reqs = extract_requirements_from_provision(p)
        assert len(reqs) == 0

    def test_preserves_evidence_quote(self):
        p = _make_provision(text="应安装ABS系统")
        reqs = extract_requirements_from_provision(p)
        assert "应安装ABS系统" in reqs[0]["evidence"]["quote"]

    def test_evidence_has_locator(self):
        p = _make_provision(label="11.6", text="应安装座椅")
        reqs = extract_requirements_from_provision(p)
        assert reqs[0]["evidence"]["locator"]["label"] == "11.6"

    def test_counter_increments(self):
        p = _make_provision(text="应安装")
        reqs = extract_requirements_from_provision(p, req_counter=5)
        assert reqs[0]["requirement_id"] == "test-doc-4.1-r5"


class TestExtractRequirementsFromProvisions:
    def test_extracts_from_multiple_provisions(self):
        provisions = [
            _make_provision(label="4.1", text="机动车应安装安全带"),
            _make_provision(label="4.2", text="不得擅自改装车辆"),
            _make_provision(label="4.3", text="本标准规定了技术条件"),
        ]
        reqs = extract_requirements_from_provisions(provisions)

        assert len(reqs) == 2
        assert reqs[0]["modality"] == "must"
        assert reqs[1]["modality"] == "must_not"

    def test_requirement_ids_are_stable_and_ordered(self):
        provisions = [
            _make_provision(label="4.1", text="应安装A"),
            _make_provision(label="4.2", text="应安装B"),
            _make_provision(label="4.3", text="应安装C"),
        ]
        reqs = extract_requirements_from_provisions(provisions)

        assert reqs[0]["requirement_id"] == "test-doc-4.1-r1"
        assert reqs[1]["requirement_id"] == "test-doc-4.2-r2"
        assert reqs[2]["requirement_id"] == "test-doc-4.3-r3"


class TestExtractRequirementsFromJsonl:
    def test_reads_provisions_and_writes_requirements(self, tmp_path):
        provisions = [
            _make_provision(label="4.1", text="机动车应安装安全带"),
            _make_provision(label="4.2", text="不得改装"),
        ]
        prov_path = tmp_path / "provisions" / "test.jsonl"
        write_jsonl(provisions, prov_path)

        reqs = extract_requirements_from_jsonl("test", candidates_dir=tmp_path)

        assert len(reqs) == 2

    def test_missing_provisions_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            extract_requirements_from_jsonl("nonexistent", candidates_dir=tmp_path)

    def test_modality_count_deterministic(self, tmp_path):
        provisions = [
            _make_provision(label="4.1", text="应安装"),
            _make_provision(label="4.2", text="应安装"),
            _make_provision(label="4.3", text="不得改装"),
            _make_provision(label="4.4", text="可以使用"),
        ]
        prov_path = tmp_path / "provisions" / "test.jsonl"
        write_jsonl(provisions, prov_path)

        reqs = extract_requirements_from_jsonl("test", candidates_dir=tmp_path)

        modalities = [r["modality"] for r in reqs]
        assert modalities.count("must") == 2
        assert modalities.count("must_not") == 1
        assert modalities.count("may") == 1
