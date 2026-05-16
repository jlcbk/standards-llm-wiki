"""Job tracking for ingestion pipeline state."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from .utils import ensure_parent

JobStatus = Literal["pending", "running", "completed", "failed"]

_JOBS_DIR = Path("_jobs")


def _job_dir(status: JobStatus) -> Path:
    """Return the directory path for a given job status."""
    return _JOBS_DIR / status


def create_job(job_id: str, input_type: str, input_path: str) -> dict:
    """Create a new pending job record.

    Returns the job dict and writes it to _jobs/pending/.
    """
    job = {
        "job_id": job_id,
        "input_type": input_type,
        "input": input_path,
        "status": "pending",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "error": None,
    }
    _write_job(job)
    return job


def update_job(job_id: str, status: JobStatus, error: str | None = None) -> dict:
    """Update an existing job's status.

    Moves the job file from its current status directory to the new one.
    """
    job_path = _find_job(job_id)
    if job_path is None:
        raise FileNotFoundError(f"Job not found: {job_id}")

    with open(job_path) as f:
        job = json.load(f)

    job["status"] = status
    job["updated_at"] = _now_iso()
    if error is not None:
        job["error"] = error

    # Remove from old location, write to new location
    job_path.unlink()
    _write_job(job)
    return job


def get_job(job_id: str) -> dict | None:
    """Retrieve a job by ID from any status directory."""
    job_path = _find_job(job_id)
    if job_path is None:
        return None
    with open(job_path) as f:
        return json.load(f)


def list_jobs(status: JobStatus | None = None) -> list[dict]:
    """List all jobs, optionally filtered by status."""
    jobs = []
    if status is not None:
        dirs = [_job_dir(status)]
    else:
        dirs = [_job_dir(s) for s in ["pending", "running", "completed", "failed"]]

    for d in dirs:
        if not d.exists():
            continue
        for f in d.glob("*.json"):
            with open(f) as fp:
                jobs.append(json.load(fp))
    return jobs


def _find_job(job_id: str) -> Path | None:
    """Find a job file by ID across all status directories."""
    for status in ["pending", "running", "completed", "failed"]:
        candidate = _job_dir(status) / f"{job_id}.json"
        if candidate.exists():
            return candidate
    return None


def _write_job(job: dict) -> None:
    """Write a job to the appropriate status directory."""
    status_dir = _job_dir(job["status"])
    status_dir.mkdir(parents=True, exist_ok=True)
    path = status_dir / f"{job['job_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job, f, indent=2, ensure_ascii=False)


def _now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
