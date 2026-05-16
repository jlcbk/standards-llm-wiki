"""Smoke tests for ingestion CLI scripts."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

# Get the project root directory (parent of tests/)
PROJECT_ROOT = Path(__file__).parent.parent


@pytest.fixture(autouse=True)
def clean_output_dirs(tmp_path, monkeypatch):
    """Clean output directories before each test."""
    # Monkeypatch the base directories to use tmp_path
    monkeypatch.setattr("standards_wiki.archive._RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr("standards_wiki.extractors.pdf._DEFAULT_SOURCES_DIR", tmp_path / "sources")
    monkeypatch.setattr("standards_wiki.extractors.html._DEFAULT_SOURCES_DIR", tmp_path / "sources")
    monkeypatch.setattr("standards_wiki.writers.candidate_writer._CANDIDATES_DIR", tmp_path / "_candidates")
    monkeypatch.setattr("standards_wiki.jobs._JOBS_DIR", tmp_path / "_jobs")
    return tmp_path


class TestIngestPdfSmoke:
    def test_ingest_pdf_cli(self, tmp_path):
        # Create a simple test PDF
        doc = __import__("pymupdf").open()
        page = doc.new_page()
        page.insert_text((72, 72), "# GB 7258-2017 机动车运行安全技术条件\n\nThis is a test PDF with enough content for extraction.")
        for i in range(5):
            page.insert_text((72, 100 + i * 18), f"Additional content line {i + 1} with meaningful text for testing purposes.")
        pdf_path = tmp_path / "test.pdf"
        doc.save(pdf_path)
        doc.close()

        # Run the CLI using absolute path
        tools_dir = PROJECT_ROOT / "tools"
        result = subprocess.run(
            [sys.executable, str(tools_dir / "ingest_pdf.py"), str(pdf_path)],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
        )

        # Should succeed
        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        assert "Job ID:" in result.stdout
        assert "raw/standards" in result.stdout
        assert "sources/standards" in result.stdout
        assert "_candidates" in result.stdout

    def test_ingest_pdf_cli_missing_file(self, tmp_path):
        tools_dir = PROJECT_ROOT / "tools"
        result = subprocess.run(
            [sys.executable, str(tools_dir / "ingest_pdf.py"), str(tmp_path / "nonexistent.pdf")],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
        )

        assert result.returncode == 1
        assert "not found" in result.stdout.lower() or "Error" in result.stdout


class TestIngestUrlSmoke:
    def test_ingest_url_function(self, tmp_path, monkeypatch):
        """Test ingest_url function directly (subprocess can't mock network)."""
        from unittest.mock import Mock, patch

        html = """<!DOCTYPE html>
<html>
<head><title>Test Notice</title></head>
<body>
<h1>Test Notice Title</h1>
<p>This is test content from a webpage.</p>
<a href="/docs/guide.pdf">Guide PDF</a>
</body>
</html>"""

        with patch("standards_wiki.extractors.html.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.text = html
            mock_response.url = "https://example.com/notice.html"
            mock_response.raise_for_status = lambda: None
            mock_get.return_value = mock_response

            from standards_wiki.ingest import ingest_url

            result = ingest_url("https://example.com/notice.html")

            assert result["status"] == "completed"
            assert result["job_id"].startswith("url-")
            assert result["source_text"] is not None

    def test_ingest_url_cli_missing_arg(self, tmp_path):
        tools_dir = PROJECT_ROOT / "tools"
        result = subprocess.run(
            [sys.executable, str(tools_dir / "ingest_url.py")],
            capture_output=True,
            text=True,
            cwd=tmp_path,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
        )

        assert result.returncode == 1
        assert "Usage" in result.stdout
