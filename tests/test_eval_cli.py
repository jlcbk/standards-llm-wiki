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
