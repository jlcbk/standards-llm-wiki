"""Tests for eval_candidates CLI tool."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tools.eval_candidates import _load_jsonl, main

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CLI_SCRIPT = PROJECT_ROOT / "tools" / "eval_candidates.py"


def _write_jsonl(records, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _run_cli(cwd, *extra_args):
    cmd = [sys.executable, str(CLI_SCRIPT), *extra_args]
    return subprocess.run(cmd, capture_output=True, text=True, cwd=str(cwd))


class TestLoadJsonl:
    def test_loads_existing_file(self, tmp_path):
        path = tmp_path / "test.jsonl"
        _write_jsonl([{"a": 1}, {"b": 2}], path)
        result = _load_jsonl(path)
        assert len(result) == 2

    def test_returns_empty_for_missing(self, tmp_path):
        result = _load_jsonl(tmp_path / "nope.jsonl")
        assert result == []


class TestCliPass:
    def test_all_checks_pass(self, tmp_path):
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "doc-1"},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        prov_dir = tmp_path / "candidates" / "provisions"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1", "text": "制动装置"}],
            prov_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            PROJECT_ROOT,
            str(checks_path),
            "--candidates-dir", str(tmp_path / "candidates"),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout
        assert "failed: 0" in result.stdout

    def test_multiple_check_files_pass(self, tmp_path):
        checks_path_1 = tmp_path / "checks-1.jsonl"
        checks_path_2 = tmp_path / "checks-2.jsonl"
        _write_jsonl(
            [{"id": "c1", "type": "document_id_exists", "expected": "doc-1"}],
            checks_path_1,
        )
        _write_jsonl(
            [{"id": "c2", "type": "keyword_search", "expected": {"keyword": "制动", "min_count": 1}}],
            checks_path_2,
        )

        prov_dir = tmp_path / "candidates" / "provisions"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1", "text": "制动装置"}],
            prov_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            PROJECT_ROOT,
            str(checks_path_1),
            str(checks_path_2),
            "--candidates-dir", str(tmp_path / "candidates"),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "total: 2" in result.stdout
        assert "passed: 2" in result.stdout
        assert "failed: 0" in result.stdout


class TestCliFailWritesReport:
    def test_writes_failure_report(self, tmp_path):
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "missing-doc"},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        prov_dir = tmp_path / "candidates" / "provisions"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1"}],
            prov_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(tmp_path / "candidates"),
            "--document-id", "doc-1",
            "--run-id", "test-run-001",
        )
        assert result.returncode == 1
        assert "failed: 1" in result.stdout

        report_path = tmp_path / "_reviews" / "eval-failures" / "test-run-001.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["failed"] == 1
        assert report["failures"][0]["id"] == "c1"


class TestCliRequirementsOptional:
    def test_works_without_requirements_file(self, tmp_path):
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "doc-1"},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        prov_dir = tmp_path / "candidates" / "provisions"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1"}],
            prov_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            PROJECT_ROOT,
            str(checks_path),
            "--candidates-dir", str(tmp_path / "candidates"),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0

    def test_keyword_search_uses_requirements(self, tmp_path):
        checks = [
            {"id": "c1", "type": "keyword_search", "expected": {"keyword": "制动", "min_count": 1}},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        prov_dir = cand_dir / "provisions"
        req_dir = cand_dir / "requirements"
        _write_jsonl([], prov_dir / "doc-1.jsonl")
        _write_jsonl(
            [{"document_id": "doc-1", "evidence": {"quote": "应安装制动装置"}}],
            req_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            PROJECT_ROOT,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout


class TestCliDocumentIdSources:
    """Tests that document_id_exists uses real data, not artificial injection."""

    def test_fails_without_metadata_or_matching_records(self, tmp_path):
        """No metadata file and no provisions/requirements with target document_id → fail + report."""
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "missing-doc"},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        prov_dir = cand_dir / "provisions"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1"}],
            prov_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
            "--run-id", "no-meta-fail",
        )
        assert result.returncode == 1
        assert "failed: 1" in result.stdout

        # Verify failure report was written
        report_path = tmp_path / "_reviews" / "eval-failures" / "no-meta-fail.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report["failed"] == 1
        assert report["failures"][0]["id"] == "c1"

    def test_passes_from_provisions(self, tmp_path):
        """No metadata but provisions have target document_id → pass."""
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "doc-1"},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        prov_dir = cand_dir / "provisions"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1"}],
            prov_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout

    def test_passes_from_metadata(self, tmp_path):
        """Metadata file exists with matching document_id → pass."""
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "doc-1"},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        meta_dir = cand_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "doc-1.yaml").write_text(
            "document_id: doc-1\ntitle: Test Document\n",
            encoding="utf-8",
        )

        # Empty provisions — document_id comes from metadata
        prov_dir = cand_dir / "provisions"
        _write_jsonl([], prov_dir / "doc-1.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout


class TestCliEvidenceListKeyword:
    """Tests that keyword_search handles evidence as a list of dicts."""

    def test_keyword_hits_in_evidence_list(self, tmp_path):
        checks = [
            {"id": "c1", "type": "keyword_search", "expected": {"keyword": "制动", "min_count": 2}},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        prov_dir = cand_dir / "provisions"
        req_dir = cand_dir / "requirements"
        _write_jsonl([], prov_dir / "doc-1.jsonl")
        _write_jsonl(
            [{"document_id": "doc-1", "evidence": [
                {"quote": "应安装制动装置"},
                {"quote": "制动性能应满足要求"},
            ]}],
            req_dir / "doc-1.jsonl",
        )

        result = _run_cli(
            PROJECT_ROOT,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout


class TestCliTopicTags:
    """Tests that CLI reads candidates/topic-tags/<doc>.json for topic_tag_exists checks."""

    def test_topic_tag_exists_pass(self, tmp_path):
        checks = [
            {
                "id": "tt1",
                "type": "topic_tag_exists",
                "expected": {"document_id": "doc-1", "topic": "braking-system"},
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        tt_dir = cand_dir / "topic-tags"
        tt_dir.mkdir(parents=True, exist_ok=True)
        (tt_dir / "doc-1.json").write_text(
            json.dumps({
                "document_id": "doc-1",
                "provisions": [
                    {
                        "document_id": "doc-1",
                        "id": "doc-1-1",
                        "topics": ["braking-system", "lighting"],
                    },
                ],
                "requirements": [],
            }),
            encoding="utf-8",
        )

        # Provisions file still needed for CLI
        _write_jsonl([], cand_dir / "provisions" / "doc-1.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout
        assert "failed: 0" in result.stdout

    def test_topic_tag_exists_from_requirements(self, tmp_path):
        """topic_tag_exists should also find tags in requirements list."""
        checks = [
            {
                "id": "tt2",
                "type": "topic_tag_exists",
                "expected": {"document_id": "doc-1", "topic": "emissions"},
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        tt_dir = cand_dir / "topic-tags"
        tt_dir.mkdir(parents=True, exist_ok=True)
        (tt_dir / "doc-1.json").write_text(
            json.dumps({
                "document_id": "doc-1",
                "provisions": [],
                "requirements": [
                    {
                        "document_id": "doc-1",
                        "id": "doc-1-r1",
                        "topics": ["emissions"],
                    },
                ],
            }),
            encoding="utf-8",
        )

        _write_jsonl([], cand_dir / "provisions" / "doc-1.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout


class TestCliMetadataField:
    """Tests that CLI reads candidates/metadata/<doc>.yaml for metadata_field_equals checks."""

    def test_metadata_field_equals_pass(self, tmp_path):
        checks = [
            {
                "id": "mf1",
                "type": "metadata_field_equals",
                "expected": {
                    "document_id": "doc-1",
                    "field": "title",
                    "value": "Test Standard",
                },
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        meta_dir = cand_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "doc-1.yaml").write_text(
            "document_id: doc-1\ntitle: Test Standard\n",
            encoding="utf-8",
        )

        _write_jsonl([], cand_dir / "provisions" / "doc-1.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout
        assert "failed: 0" in result.stdout

    def test_metadata_field_equals_no_document_id_in_yaml(self, tmp_path):
        """metadata YAML has only standard_id/title, no document_id.
        CLI --document-id is injected as canonical document_id,
        so metadata_field_equals still matches."""
        checks = [
            {
                "id": "mf-no-did",
                "type": "metadata_field_equals",
                "expected": {
                    "document_id": "gb-7258-2017",
                    "field": "standard_id",
                    "value": "GB-7258-2017",
                },
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        meta_dir = cand_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        # Real-world style YAML: no document_id, only standard_id + title
        (meta_dir / "gb-7258-2017.yaml").write_text(
            "title: 中华人民共和国国家标准\n"
            "standard_id: GB-7258-2017\n",
            encoding="utf-8",
        )

        _write_jsonl([], cand_dir / "provisions" / "gb-7258-2017.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "gb-7258-2017",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout
        assert "failed: 0" in result.stdout

    def test_metadata_field_equals_standard_id(self, tmp_path):
        """metadata_field_equals should work with standard_id field too."""
        checks = [
            {
                "id": "mf2",
                "type": "metadata_field_equals",
                "expected": {
                    "document_id": "doc-1",
                    "field": "standard_id",
                    "value": "GB-7258-2017",
                },
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        meta_dir = cand_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "doc-1.yaml").write_text(
            "document_id: doc-1\nstandard_id: GB-7258-2017\n",
            encoding="utf-8",
        )

        _write_jsonl([], cand_dir / "provisions" / "doc-1.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
        )
        assert result.returncode == 0
        assert "passed: 1" in result.stdout


class TestCliFailureReportFields:
    """Tests that failure report JSON contains category and severity."""

    def test_failure_report_has_category_and_severity(self, tmp_path):
        checks = [
            {
                "id": "f1",
                "type": "document_id_exists",
                "category": "missed_document",
                "severity": "error",
                "expected": "missing-doc",
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1"}],
            cand_dir / "provisions" / "doc-1.jsonl",
        )

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
            "--run-id", "cat-sev-test",
        )
        assert result.returncode == 1

        report_path = tmp_path / "_reviews" / "eval-failures" / "cat-sev-test.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        failure = report["failures"][0]
        assert "category" in failure
        assert failure["category"] == "missed_document"
        assert "severity" in failure
        assert failure["severity"] == "error"

    def test_failure_report_inferred_category(self, tmp_path):
        """When check lacks category/severity, report should still have them (inferred)."""
        checks = [
            {
                "id": "f2",
                "type": "topic_tag_exists",
                "expected": {"document_id": "doc-1", "topic": "missing-topic"},
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        tt_dir = cand_dir / "topic-tags"
        tt_dir.mkdir(parents=True, exist_ok=True)
        (tt_dir / "doc-1.json").write_text(
            json.dumps({
                "document_id": "doc-1",
                "provisions": [],
                "requirements": [],
            }),
            encoding="utf-8",
        )

        _write_jsonl([], cand_dir / "provisions" / "doc-1.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
            "--run-id", "inferred-cat",
        )
        assert result.returncode == 1

        report_path = tmp_path / "_reviews" / "eval-failures" / "inferred-cat.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        failure = report["failures"][0]
        assert "category" in failure
        assert failure["category"] == "topic_mismatch"
        assert "severity" in failure
        assert failure["severity"] == "error"

    def test_failure_report_with_warn_severity(self, tmp_path):
        """Checks can specify warn severity, which should be preserved."""
        checks = [
            {
                "id": "f3",
                "type": "metadata_field_equals",
                "category": "metadata_mismatch",
                "severity": "warn",
                "expected": {
                    "document_id": "doc-1",
                    "field": "title",
                    "value": "Expected Title",
                },
            },
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        meta_dir = cand_dir / "metadata"
        meta_dir.mkdir(parents=True, exist_ok=True)
        (meta_dir / "doc-1.yaml").write_text(
            "document_id: doc-1\ntitle: Actual Title\n",
            encoding="utf-8",
        )

        _write_jsonl([], cand_dir / "provisions" / "doc-1.jsonl")

        result = _run_cli(
            tmp_path,
            str(checks_path),
            "--candidates-dir", str(cand_dir),
            "--document-id", "doc-1",
            "--run-id", "warn-sev",
        )
        assert result.returncode == 1

        report_path = tmp_path / "_reviews" / "eval-failures" / "warn-sev.json"
        assert report_path.exists()
        report = json.loads(report_path.read_text(encoding="utf-8"))
        failure = report["failures"][0]
        assert failure["category"] == "metadata_mismatch"
        assert failure["severity"] == "warn"


class TestCliMainArgv:
    """Tests that main() accepts argv parameter for programmatic use."""

    def test_main_with_argv(self, tmp_path):
        checks = [
            {"id": "c1", "type": "document_id_exists", "expected": "doc-1"},
        ]
        checks_path = tmp_path / "checks.jsonl"
        _write_jsonl(checks, checks_path)

        cand_dir = tmp_path / "candidates"
        prov_dir = cand_dir / "provisions"
        _write_jsonl(
            [{"document_id": "doc-1", "label": "1"}],
            prov_dir / "doc-1.jsonl",
        )

        with pytest.raises(SystemExit) as exc_info:
            main([
                str(checks_path),
                "--candidates-dir", str(cand_dir),
                "--document-id", "doc-1",
            ])
        assert exc_info.value.code == 0
