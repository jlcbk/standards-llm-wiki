"""Tests for candidate validation module."""

import pytest
import yaml

from standards_wiki.validate import (
    ValidationError,
    validate_metadata,
    validate_provision_jsonl,
    validate_requirement_jsonl,
    validate_candidate_chain,
)
from standards_wiki.candidates import write_jsonl


def _write_candidate_fixtures(tmp_path, doc_id, metadata=None, provisions=None, requirements=None):
    """Helper: write test fixtures under tmp_path."""
    base = tmp_path / "candidates"
    base.mkdir(parents=True, exist_ok=True)

    # Metadata
    meta = metadata or {
        "document_id": doc_id,
        "title": "Test Standard",
        "review_status": "draft",
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
    }
    meta_dir = base / "metadata"
    meta_dir.mkdir(exist_ok=True)
    (meta_dir / f"{doc_id}.yaml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8"
    )

    # Document
    doc_dir = base / "documents"
    doc_dir.mkdir(exist_ok=True)
    (doc_dir / f"{doc_id}.md").write_text("# Test\n\nBody.", encoding="utf-8")

    # Provisions
    if provisions is not None:
        prov_dir = base / "provisions"
        write_jsonl(provisions, prov_dir / f"{doc_id}.jsonl")

    # Requirements
    if requirements is not None:
        req_dir = base / "requirements"
        write_jsonl(requirements, req_dir / f"{doc_id}.jsonl")


class TestValidateMetadata:
    def test_valid_metadata(self):
        meta = {
            "document_id": "test",
            "title": "Test",
            "review_status": "draft",
            "source_text": "sources/test.md",
            "raw_path": "raw/test.pdf",
        }
        errors = validate_metadata(meta)
        assert len(errors) == 0

    def test_missing_required_field(self):
        meta = {"title": "Test"}  # missing document_id and review_status
        errors = validate_metadata(meta)
        error_fields = [e.category for e in errors]
        assert any("document_id" in str(e.message) for e in errors)

    def test_missing_provenance_field(self):
        meta = {
            "document_id": "test",
            "title": "Test",
            "review_status": "draft",
        }
        errors = validate_metadata(meta)
        warnings = [e for e in errors if e.level == "warning"]
        assert len(warnings) >= 1

    def test_empty_required_field(self):
        meta = {
            "document_id": "test",
            "title": "",
            "review_status": "draft",
        }
        errors = validate_metadata(meta)
        assert any("title" in e.message for e in errors)


class TestValidateProvisionJsonl:
    def test_valid_provisions(self):
        records = [
            {
                "provision_id": "test-4-1",
                "locator": {"label": "4.1"},
                "evidence": {"quote": "text"},
            },
        ]
        errors = validate_provision_jsonl(records)
        assert len(errors) == 0

    def test_duplicate_provision_id(self):
        records = [
            {"provision_id": "test-4-1", "locator": {"label": "4.1"}, "evidence": {"quote": "a"}},
            {"provision_id": "test-4-1", "locator": {"label": "4.1"}, "evidence": {"quote": "b"}},
        ]
        errors = validate_provision_jsonl(records)
        assert any("Duplicate" in e.message for e in errors)

    def test_missing_provision_id(self):
        records = [{"locator": {}, "evidence": {"quote": "text"}}]
        errors = validate_provision_jsonl(records)
        assert any("missing provision_id" in e.message for e in errors)

    def test_missing_evidence_quote(self):
        records = [
            {"provision_id": "test-4-1", "locator": {"label": "4.1"}, "evidence": {}},
        ]
        errors = validate_provision_jsonl(records)
        assert any("missing evidence quote" in e.message for e in errors)

    def test_missing_locator_warns(self):
        records = [
            {"provision_id": "test-4-1", "evidence": {"quote": "text"}},
        ]
        errors = validate_provision_jsonl(records)
        assert any("missing locator" in e.message for e in errors)


class TestValidateRequirementJsonl:
    def test_valid_requirements(self):
        records = [{
            "requirement_id": "test-4-1-r1",
            "modality": "must",
            "document_id": "test",
            "provision_id": "test-4-1",
            "evidence": {"quote": "text"},
        }]
        errors = validate_requirement_jsonl(records)
        assert len(errors) == 0

    def test_missing_modality(self):
        records = [{
            "requirement_id": "test-4-1-r1",
            "document_id": "test",
            "provision_id": "test-4-1",
            "evidence": {"quote": "text"},
        }]
        errors = validate_requirement_jsonl(records)
        assert any("modality" in e.message for e in errors)

    def test_missing_evidence(self):
        records = [{
            "requirement_id": "test-4-1-r1",
            "modality": "must",
            "document_id": "test",
            "provision_id": "test-4-1",
            "evidence": {},
        }]
        errors = validate_requirement_jsonl(records)
        assert any("missing evidence quote" in e.message for e in errors)


class TestValidateCandidateChain:
    def test_full_valid_chain(self, tmp_path):
        provisions = [
            {
                "provision_id": "test-4-1",
                "locator": {"label": "4.1"},
                "evidence": {"quote": "应安装"},
                "document_id": "test",
            },
        ]
        requirements = [{
            "requirement_id": "test-4-1-r1",
            "modality": "must",
            "document_id": "test",
            "provision_id": "test-4-1",
            "evidence": {"quote": "应安装"},
        }]
        _write_candidate_fixtures(
            tmp_path, "test",
            provisions=provisions,
            requirements=requirements,
        )

        errors = validate_candidate_chain("test", candidates_dir=tmp_path / "candidates")
        assert len(errors) == 0

    def test_chain_accepts_legacy_metadata_without_document_id(self, tmp_path):
        provisions = [
            {
                "provision_id": "test-4-1",
                "locator": {"label": "4.1"},
                "evidence": {"quote": "应安装"},
                "document_id": "test",
            },
        ]
        metadata = {
            "title": "Test Standard",
            "review_status": "draft",
            "source_text": "sources/test.md",
            "raw_path": "raw/test.pdf",
        }
        _write_candidate_fixtures(
            tmp_path, "test",
            metadata=metadata,
            provisions=provisions,
            requirements=[],
        )

        errors = validate_candidate_chain("test", candidates_dir=tmp_path / "candidates")
        assert len(errors) == 0

    def test_missing_metadata(self, tmp_path):
        # No metadata file
        errors = validate_candidate_chain("nonexistent", candidates_dir=tmp_path / "candidates")
        assert any("Metadata file not found" in e.message for e in errors)

    def test_missing_document(self, tmp_path):
        meta = {
            "document_id": "test",
            "title": "Test",
            "review_status": "draft",
        }
        meta_dir = tmp_path / "candidates" / "metadata"
        meta_dir.mkdir(parents=True)
        (meta_dir / "test.yaml").write_text(
            yaml.dump(meta, allow_unicode=True), encoding="utf-8"
        )

        errors = validate_candidate_chain("test", candidates_dir=tmp_path / "candidates")
        assert any("Candidate document not found" in e.message for e in errors)

    def test_invalid_jsonl(self, tmp_path):
        _write_candidate_fixtures(tmp_path, "test")
        prov_dir = tmp_path / "candidates" / "provisions"
        prov_dir.mkdir(exist_ok=True)
        (prov_dir / "test.jsonl").write_text("not valid json\n", encoding="utf-8")

        errors = validate_candidate_chain("test", candidates_dir=tmp_path / "candidates")
        assert any(e.level == "error" for e in errors)
