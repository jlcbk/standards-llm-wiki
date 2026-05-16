"""Tests for jobs module."""

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from standards_wiki.jobs import (
    create_job,
    update_job,
    get_job,
    list_jobs,
    _JOBS_DIR,
    _now_iso,
)


@pytest.fixture(autouse=True)
def clean_jobs_dir(monkeypatch, tmp_path):
    """Use a temporary _jobs directory for each test."""
    jobs_tmp = tmp_path / "_jobs"
    monkeypatch.setattr("standards_wiki.jobs._JOBS_DIR", jobs_tmp)
    return jobs_tmp


class TestCreateJob:
    def test_creates_pending_job(self, clean_jobs_dir):
        job = create_job("test-001", "pdf", "/path/to/file.pdf")

        assert job["job_id"] == "test-001"
        assert job["input_type"] == "pdf"
        assert job["input"] == "/path/to/file.pdf"
        assert job["status"] == "pending"
        assert job["error"] is None
        assert job["created_at"].endswith("Z")
        assert job["updated_at"].endswith("Z")

    def test_writes_to_pending_dir(self, clean_jobs_dir):
        create_job("test-002", "url", "https://example.com/doc.html")

        pending_file = clean_jobs_dir / "pending" / "test-002.json"
        assert pending_file.exists()

    def test_job_file_is_valid_json(self, clean_jobs_dir):
        create_job("test-003", "pdf", "/tmp/test.pdf")

        pending_file = clean_jobs_dir / "pending" / "test-003.json"
        with open(pending_file) as f:
            data = json.load(f)
        assert data["job_id"] == "test-003"


class TestUpdateJob:
    def test_updates_to_running(self, clean_jobs_dir):
        create_job("test-004", "pdf", "/tmp/test.pdf")
        job = update_job("test-004", "running")

        assert job["status"] == "running"
        assert job["updated_at"].endswith("Z")

    def test_updates_to_completed(self, clean_jobs_dir):
        create_job("test-005", "pdf", "/tmp/test.pdf")
        job = update_job("test-005", "completed")

        assert job["status"] == "completed"

    def test_updates_to_failed_with_error(self, clean_jobs_dir):
        create_job("test-006", "pdf", "/tmp/test.pdf")
        job = update_job("test-006", "failed", error="OCR required: scanned PDF")

        assert job["status"] == "failed"
        assert job["error"] == "OCR required: scanned PDF"

    def test_moves_between_dirs(self, clean_jobs_dir):
        create_job("test-007", "pdf", "/tmp/test.pdf")

        # Should be in pending
        assert (clean_jobs_dir / "pending" / "test-007.json").exists()

        update_job("test-007", "running")
        assert (clean_jobs_dir / "running" / "test-007.json").exists()
        assert not (clean_jobs_dir / "pending" / "test-007.json").exists()

    def test_raises_on_missing_job(self, clean_jobs_dir):
        with pytest.raises(FileNotFoundError, match="Job not found"):
            update_job("nonexistent", "running")


class TestGetJob:
    def test_retrieves_existing_job(self, clean_jobs_dir):
        create_job("test-008", "pdf", "/tmp/test.pdf")
        job = get_job("test-008")

        assert job is not None
        assert job["job_id"] == "test-008"

    def test_returns_none_for_missing_job(self, clean_jobs_dir):
        assert get_job("nonexistent") is None


class TestListJobs:
    def test_lists_all_jobs(self, clean_jobs_dir):
        create_job("test-009", "pdf", "/tmp/a.pdf")
        create_job("test-010", "url", "https://example.com")
        update_job("test-009", "completed")

        all_jobs = list_jobs()
        assert len(all_jobs) == 2

    def test_filters_by_status(self, clean_jobs_dir):
        create_job("test-011", "pdf", "/tmp/a.pdf")
        create_job("test-012", "pdf", "/tmp/b.pdf")
        update_job("test-011", "completed")

        pending = list_jobs(status="pending")
        completed = list_jobs(status="completed")

        assert len(pending) == 1
        assert len(completed) == 1

    def test_returns_empty_when_no_jobs(self, clean_jobs_dir):
        assert list_jobs() == []


class TestNowIso:
    def test_returns_iso_format(self):
        result = _now_iso()
        assert result.endswith("Z")
        assert len(result) == 20
