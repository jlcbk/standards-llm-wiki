"""Candidate validation — verify candidate chain integrity before promotion."""

import json
import sys
from pathlib import Path

import yaml

from .candidates import load_metadata, read_jsonl, load_candidate_document

_CANDIDATES_DIR = Path("_candidates")


class ValidationError:
    """A single validation finding."""

    def __init__(self, level: str, category: str, message: str, path: str = ""):
        self.level = level  # error, warning
        self.category = category
        self.message = message
        self.path = path

    def __str__(self):
        prefix = f"[{self.level.upper()}]"
        if self.path:
            return f"{prefix} {self.category}: {self.message} ({self.path})"
        return f"{prefix} {self.category}: {self.message}"


def validate_metadata(metadata: dict, path: str = "") -> list[ValidationError]:
    """Validate candidate metadata has required fields.

    Args:
        metadata: Metadata dict to validate.
        path: File path for error reporting.

    Returns:
        List of ValidationError instances.
    """
    errors = []
    required_fields = ["document_id", "title", "review_status"]

    for field in required_fields:
        if field not in metadata or metadata[field] in (None, "", "unknown"):
            errors.append(ValidationError(
                "error", "metadata",
                f"Missing or empty required field: {field}", path,
            ))

    # Provenance fields should exist (may be "unknown")
    provenance_fields = ["source_text", "raw_path"]
    for field in provenance_fields:
        if field not in metadata:
            errors.append(ValidationError(
                "warning", "metadata",
                f"Missing provenance field: {field}", path,
            ))

    return errors


def validate_provision_jsonl(
    records: list[dict],
    path: str = "",
) -> list[ValidationError]:
    """Validate provision JSONL records.

    Args:
        records: List of provision dicts.
        path: File path for error reporting.

    Returns:
        List of ValidationError instances.
    """
    errors = []

    # Check unique provision IDs
    seen_ids = set()
    for i, record in enumerate(records):
        pid = record.get("provision_id", "")
        if not pid:
            errors.append(ValidationError(
                "error", "provision",
                f"Record {i} missing provision_id", path,
            ))
        elif pid in seen_ids:
            errors.append(ValidationError(
                "error", "provision",
                f"Duplicate provision_id: {pid}", path,
            ))
        else:
            seen_ids.add(pid)

        # Check locator
        if "locator" not in record or not record.get("locator"):
            errors.append(ValidationError(
                "warning", "provision",
                f"Record {i} ({pid}) missing locator", path,
            ))

        # Check evidence quote
        evidence = record.get("evidence", {})
        if not evidence or not evidence.get("quote"):
            errors.append(ValidationError(
                "error", "provision",
                f"Record {i} ({pid}) missing evidence quote", path,
            ))

    return errors


def validate_requirement_jsonl(
    records: list[dict],
    path: str = "",
) -> list[ValidationError]:
    """Validate requirement JSONL records.

    Args:
        records: List of requirement dicts.
        path: File path for error reporting.

    Returns:
        List of ValidationError instances.
    """
    errors = []

    for i, record in enumerate(records):
        rid = record.get("requirement_id", "")
        if not rid:
            errors.append(ValidationError(
                "error", "requirement",
                f"Record {i} missing requirement_id", path,
            ))

        # Check required fields
        for field in ["modality", "document_id", "provision_id"]:
            if not record.get(field):
                errors.append(ValidationError(
                    "error", "requirement",
                    f"Record {i} ({rid}) missing {field}", path,
                ))

        # Check evidence quote
        evidence = record.get("evidence", {})
        if not evidence or not evidence.get("quote"):
            errors.append(ValidationError(
                "error", "requirement",
                f"Record {i} ({rid}) missing evidence quote", path,
            ))

    return errors


def validate_candidate_chain(
    document_id: str,
    candidates_dir: str | Path = _CANDIDATES_DIR,
) -> list[ValidationError]:
    """Validate the full candidate chain for a document.

    Checks metadata, candidate document existence, provision JSONL,
    and requirement JSONL.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory.

    Returns:
        List of ValidationError instances.
    """
    candidates_dir = Path(candidates_dir)
    errors = []

    # 1. Validate metadata
    meta_path = candidates_dir / "metadata" / f"{document_id}.yaml"
    if not meta_path.exists():
        errors.append(ValidationError(
            "error", "metadata",
            f"Metadata file not found", str(meta_path),
        ))
        return errors

    try:
        metadata = load_metadata(meta_path)
        errors.extend(validate_metadata(metadata, str(meta_path)))
    except Exception as e:
        errors.append(ValidationError(
            "error", "metadata", f"Failed to load: {e}", str(meta_path),
        ))
        return errors

    # 2. Validate candidate document exists
    doc_path = candidates_dir / "documents" / f"{document_id}.md"
    if not doc_path.exists():
        errors.append(ValidationError(
            "error", "document",
            "Candidate document not found", str(doc_path),
        ))

    # 3. Validate provision JSONL if exists
    prov_path = candidates_dir / "provisions" / f"{document_id}.jsonl"
    if prov_path.exists():
        try:
            provisions = read_jsonl(prov_path)
            errors.extend(validate_provision_jsonl(provisions, str(prov_path)))
        except Exception as e:
            errors.append(ValidationError(
                "error", "provision", f"Failed to load: {e}", str(prov_path),
            ))

    # 4. Validate requirement JSONL if exists
    req_path = candidates_dir / "requirements" / f"{document_id}.jsonl"
    if req_path.exists():
        try:
            requirements = read_jsonl(req_path)
            errors.extend(validate_requirement_jsonl(requirements, str(req_path)))
        except Exception as e:
            errors.append(ValidationError(
                "error", "requirement", f"Failed to load: {e}", str(req_path),
            ))

    return errors


def main():
    """CLI entry point for validation."""
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python tools/validate.py --document-id <document_id>")
        sys.exit(1)

    document_id = None
    for arg in sys.argv[1:]:
        if arg.startswith("--document-id="):
            document_id = arg.split("=", 1)[1]
        elif arg == "--document-id":
            continue
        elif not arg.startswith("-"):
            document_id = arg

    if not document_id:
        print("Error: --document-id is required")
        sys.exit(1)

    errors = validate_candidate_chain(document_id)

    for e in errors:
        print(str(e))

    error_count = sum(1 for e in errors if e.level == "error")
    warning_count = sum(1 for e in errors if e.level == "warning")

    print(f"\nSummary: {error_count} errors, {warning_count} warnings")

    if error_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
