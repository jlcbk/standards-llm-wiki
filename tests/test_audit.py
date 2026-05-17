"""Tests for candidate quality audit."""

import json

import pytest

from standards_wiki.audit import audit_candidates, format_summary
from standards_wiki.candidates import write_jsonl


def _write_provisions_and_requirements(
    tmp_path, doc_id, provisions=None, requirements=None,
):
    cdir = tmp_path / "_candidates"
    if provisions is not None:
        prov_dir = cdir / "provisions"
        write_jsonl(provisions, prov_dir / f"{doc_id}.jsonl")
    if requirements is not None:
        req_dir = cdir / "requirements"
        write_jsonl(requirements, req_dir / f"{doc_id}.jsonl")
    return cdir


def _make_provision(pid, label=None, text="应安装制动装置", **extra):
    if label is None:
        parts = pid.rsplit("-", 2)
        label = ".".join(parts[-2:]) if len(parts) >= 3 and all(p.isdigit() for p in parts[-2:]) else "unknown"
    return {
        "provision_id": pid,
        "document_id": "test-doc",
        "label": label,
        "text": text,
        **extra,
    }


def _make_requirement(rid, modality="must", provision_id="test-doc-4-1",
                      evidence_quote="应安装"):
    return {
        "requirement_id": rid,
        "document_id": "test-doc",
        "provision_id": provision_id,
        "modality": modality,
        "evidence": {"quote": evidence_quote},
    }


class TestAuditCandidates:
    def test_clean_report(self, tmp_path):
        provisions = [
            _make_provision("test-doc-4-1", text="应安装制动装置。"),
            _make_provision("test-doc-4-2", text="不得改装车辆结构。"),
        ]
        requirements = [
            _make_requirement("test-doc-4-1-r1"),
            _make_requirement("test-doc-4-2-r1", modality="must_not"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions, requirements,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        assert report["document_id"] == "test-doc"
        assert report["summary"]["total_provisions"] == 2
        assert report["summary"]["total_requirements"] == 2
        assert report["checks"]["short_provisions"] == []
        assert report["checks"]["fallback_only_split"] is False
        assert report["checks"]["duplicate_labels"] == {}
        assert report["checks"]["toc_noise"] == []
        assert report["checks"]["weak_evidence"] == []

    def test_detects_short_provisions(self, tmp_path):
        provisions = [
            _make_provision("test-doc-4-1", text="应安装制动装置。"),
            _make_provision("test-doc-4-2", text="短"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=provisions,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        short = report["checks"]["short_provisions"]
        assert len(short) == 1
        assert short[0]["provision_id"] == "test-doc-4-2"

    def test_detects_fallback_only(self, tmp_path):
        provisions = [
            _make_provision("test-doc-fallback", label="fallback", text="整个文档"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=provisions,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        assert report["checks"]["fallback_only_split"] is True

    def test_fallback_with_real_labels_not_flagged(self, tmp_path):
        provisions = [
            _make_provision("test-doc-fallback", label="fallback", text="text"),
            _make_provision("test-doc-4-1", text="应安装制动装置。"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=provisions,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        assert report["checks"]["fallback_only_split"] is False

    def test_detects_duplicate_labels(self, tmp_path):
        provisions = [
            _make_provision("test-doc-4-1-a", label="4.1", text="first"),
            _make_provision("test-doc-4-1-b", label="4.1", text="second"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=provisions,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        dups = report["checks"]["duplicate_labels"]
        assert "4.1" in dups
        assert dups["4.1"]["count"] == 2
        assert len(dups["4.1"]["examples"]) == 2
        assert dups["4.1"]["examples"][0]["provision_id"] == "test-doc-4-1-a"

    def test_duplicate_labels_caps_at_five_examples(self, tmp_path):
        provisions = [
            _make_provision(f"test-doc-4-1-{i}", label="4.1", text=f"text {i}")
            for i in range(8)
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=provisions,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        dups = report["checks"]["duplicate_labels"]
        assert dups["4.1"]["count"] == 8
        assert len(dups["4.1"]["examples"]) == 5

    def test_detects_toc_label_noise(self, tmp_path):
        provisions = [
            _make_provision("test-doc-toc", label="目录", text="table of contents"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=provisions,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        toc = report["checks"]["toc_noise"]
        assert len(toc) >= 1
        assert toc[0]["reason"] == "toc_label"

    def test_detects_toc_text_noise(self, tmp_path):
        provisions = [
            _make_provision(
                "test-doc-4-1",
                text="4.1 General Requirements..........12",
            ),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=provisions,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        toc = report["checks"]["toc_noise"]
        assert len(toc) >= 1

    def test_high_requirement_density(self, tmp_path):
        provisions = [_make_provision("test-doc-4-1", text="应安装制动装置。")]
        requirements = [
            _make_requirement(f"test-doc-4-1-r{i}")
            for i in range(1, 5)
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions, requirements,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        assert report["checks"]["high_density_flag"] is True
        assert report["checks"]["requirement_density"] == 4.0

    def test_modality_distribution(self, tmp_path):
        provisions = [_make_provision("test-doc-4-1")]
        requirements = [
            _make_requirement("test-doc-4-1-r1", modality="must"),
            _make_requirement("test-doc-4-1-r2", modality="must"),
            _make_requirement("test-doc-4-1-r3", modality="must_not"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions, requirements,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        dist = report["checks"]["modality_distribution"]
        assert dist["must"] == 2
        assert dist["must_not"] == 1

    def test_weak_evidence_missing(self, tmp_path):
        provisions = [_make_provision("test-doc-4-1")]
        requirements = [
            _make_requirement("test-doc-4-1-r1", evidence_quote=""),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions, requirements,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        weak = report["checks"]["weak_evidence"]
        assert len(weak) == 1
        assert weak[0]["issue"] == "missing"

    def test_weak_evidence_very_short(self, tmp_path):
        provisions = [_make_provision("test-doc-4-1")]
        requirements = [
            _make_requirement("test-doc-4-1-r1", evidence_quote="ab"),
        ]
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions, requirements,
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        weak = report["checks"]["weak_evidence"]
        assert len(weak) == 1
        assert weak[0]["issue"] == "very_short"

    def test_writes_audit_report(self, tmp_path):
        cdir = _write_provisions_and_requirements(tmp_path, "test-doc")
        review_dir = tmp_path / "reviews"

        audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=review_dir,
        )

        report_path = review_dir / "test-doc-audit.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["document_id"] == "test-doc"

    def test_empty_files(self, tmp_path):
        cdir = _write_provisions_and_requirements(
            tmp_path, "test-doc", provisions=[], requirements=[],
        )

        report = audit_candidates(
            "test-doc",
            candidates_dir=cdir,
            review_dir=tmp_path / "reviews",
        )

        assert report["summary"]["total_provisions"] == 0
        assert report["summary"]["total_requirements"] == 0
        assert report["checks"]["requirement_density"] == 0.0
        assert report["checks"]["fallback_only_split"] is False


class TestFormatSummary:
    def test_clean_report(self):
        report = {
            "document_id": "test-doc",
            "checks": {
                "short_provisions": [],
                "fallback_only_split": False,
                "duplicate_labels": {},
                "toc_noise": [],
                "requirement_density": 1.0,
                "high_density_flag": False,
                "modality_distribution": {"must": 1},
                "weak_evidence": [],
            },
            "summary": {
                "total_provisions": 1,
                "total_requirements": 1,
                "total_issues": 0,
            },
        }
        text = format_summary(report)
        assert "clean" in text
        assert "test-doc" in text

    def test_issues_reported(self):
        report = {
            "document_id": "test-doc",
            "checks": {
                "short_provisions": [
                    {"provision_id": "p1", "label": "4.1", "text_length": 3},
                ],
                "fallback_only_split": True,
                "duplicate_labels": {
                    "4.1": {
                        "count": 2,
                        "examples": [
                            {"provision_id": "p1", "locator": "第4.1条"},
                            {"provision_id": "p2", "locator": "第4.1条"},
                        ],
                    },
                },
                "toc_noise": [],
                "requirement_density": 3.0,
                "high_density_flag": True,
                "modality_distribution": {},
                "weak_evidence": [
                    {"requirement_id": "r1", "issue": "missing"},
                ],
            },
            "summary": {
                "total_provisions": 2,
                "total_requirements": 6,
                "total_issues": 5,
            },
        }
        text = format_summary(report)
        assert "[ISSUE]" in text
        assert "Fallback-only" in text
        assert "short provisions" in text
        assert "duplicate labels" in text
        assert "High requirement density" in text
        assert "weak evidence" in text
