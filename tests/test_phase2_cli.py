"""Smoke tests for Phase 2 CLI scripts."""

import os
import subprocess
import sys
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).parent.parent


def _env():
    return {**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")}


def _run_tool(tmp_path, script, *args):
    return subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "tools" / script), *args],
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_env(),
    )


def _write_candidate(tmp_path, document_id="test-doc"):
    base = tmp_path / "_candidates"
    (base / "metadata").mkdir(parents=True)
    (base / "documents").mkdir(parents=True)
    metadata = {
        "document_id": document_id,
        "title": "Test Standard",
        "document_type": "standard",
        "standard_id": "TEST 1-2026",
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
        "confidence": "medium",
        "review_status": "draft",
    }
    (base / "metadata" / f"{document_id}.yaml").write_text(
        yaml.dump(metadata, allow_unicode=True),
        encoding="utf-8",
    )
    (base / "documents" / f"{document_id}.md").write_text(
        "---\ntitle: Test Standard\n---\n\n4.1 要求\n\n车辆应安装装置。\n\n4.2 禁止\n\n不得改装。",
        encoding="utf-8",
    )
    return document_id


def test_compile_document_cli(tmp_path):
    document_id = _write_candidate(tmp_path)

    result = _run_tool(tmp_path, "compile_document.py", document_id)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Document ID: test-doc" in result.stdout
    assert (tmp_path / "documents" / "drafts" / "test-doc.md").exists()


def test_split_extract_validate_and_generate_cli_chain(tmp_path):
    document_id = _write_candidate(tmp_path)

    split_result = _run_tool(tmp_path, "split_provisions.py", document_id)
    assert split_result.returncode == 0, split_result.stdout + split_result.stderr
    assert (tmp_path / "_candidates" / "provisions" / "test-doc.jsonl").exists()

    extract_result = _run_tool(tmp_path, "extract_requirements.py", document_id)
    assert extract_result.returncode == 0, extract_result.stdout + extract_result.stderr
    assert (tmp_path / "_candidates" / "requirements" / "test-doc.jsonl").exists()

    validate_result = _run_tool(tmp_path, "validate.py", "--document-id", document_id)
    assert validate_result.returncode == 0, validate_result.stdout + validate_result.stderr
    assert "0 errors" in validate_result.stdout

    page_result = _run_tool(tmp_path, "generate_provision_pages.py", document_id)
    assert page_result.returncode == 0, page_result.stdout + page_result.stderr
    assert (tmp_path / "_candidates" / "provision-pages" / "test-doc").exists()


def test_validate_cli_fails_for_missing_chain(tmp_path):
    result = _run_tool(tmp_path, "validate.py", "--document-id", "missing")

    assert result.returncode == 1
    assert "Metadata file not found" in result.stdout


def test_generate_provision_pages_cli_missing_file(tmp_path):
    result = _run_tool(tmp_path, "generate_provision_pages.py", "missing")

    assert result.returncode == 1
    assert "Provisions file not found" in result.stdout
