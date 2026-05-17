"""Tests for index data collector."""

import json
from pathlib import Path

import yaml

from standards_wiki.candidates import write_jsonl
from standards_wiki.indexer import (
    IndexResult,
    collect_records,
    export_json,
    generate_documents_index,
    generate_provisions_index,
    generate_requirements_index,
    generate_effective_dates_index,
    generate_markdown_indexes,
)


def _write_fixtures(tmp_path, doc_id="gb-test-2024"):
    """Create a complete set of candidate fixtures under tmp_path."""
    cand = tmp_path / "_candidates"
    drafts = tmp_path / "documents" / "drafts"

    # Metadata
    meta_dir = cand / "metadata"
    meta_dir.mkdir(parents=True)
    meta = {
        "title": "测试标准",
        "document_type": "standard",
        "standard_id": "GB-TEST-2024",
        "publisher": "测试机构",
        "release_date": "2024-01-01",
        "effective_date": "2024-07-01",
        "raw_path": "raw/test.pdf",
        "source_text": "sources/test.md",
        "confidence": "low",
        "review_status": "draft",
    }
    (meta_dir / f"{doc_id}.yaml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8"
    )

    # Draft page
    drafts.mkdir(parents=True)
    fm = {
        "document_id": doc_id,
        "title": "测试标准",
        "standard_id": "GB-TEST-2024",
        "review_status": "draft",
        "confidence": "low",
    }
    body = "测试正文内容"
    fm_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
    (drafts / f"{doc_id}.md").write_text(
        f"---\n{fm_yaml}---\n\n{body}", encoding="utf-8"
    )

    # Provisions
    prov_dir = cand / "provisions"
    prov_dir.mkdir(parents=True)
    provisions = [
        {
            "document_id": doc_id,
            "provision_id": f"{doc_id}-3-1",
            "label": "3.1",
            "kind": "clause",
            "title": "术语",
            "text": "应符合要求",
            "locator": {"label": "3.1"},
            "source_text": "sources/test.md",
            "raw_path": "raw/test.pdf",
            "confidence": "low",
            "review_status": "machine_extracted",
            "evidence": {"quote": "应符合要求"},
        }
    ]
    write_jsonl(provisions, prov_dir / f"{doc_id}.jsonl")

    # Requirements
    req_dir = cand / "requirements"
    req_dir.mkdir(parents=True)
    requirements = [
        {
            "requirement_id": f"{doc_id}-3-1-r1",
            "document_id": doc_id,
            "provision_id": f"{doc_id}-3-1",
            "modality": "must",
            "subject": "unknown",
            "action": "unknown",
            "object": "unknown",
            "condition": "unknown",
            "exception": "unknown",
            "evidence": {
                "quote": "应符合要求",
                "source_text": "sources/test.md",
                "raw_path": "raw/test.pdf",
                "locator": {"label": "3.1"},
            },
            "confidence": "low",
            "review_status": "machine_extracted",
        }
    ]
    write_jsonl(requirements, req_dir / f"{doc_id}.jsonl")

    return cand, drafts


class TestCollectRecords:
    def test_collects_all_record_types(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)

        assert len(result.documents) == 1
        assert len(result.provisions) == 1
        assert len(result.requirements) == 1

    def test_document_fields(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)

        doc = result.documents[0]
        assert doc["document_id"] == "gb-test-2024"
        assert doc["title"] == "测试标准"
        assert doc["standard_id"] == "GB-TEST-2024"
        assert doc["review_status"] == "draft"

    def test_provision_fields(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)

        prov = result.provisions[0]
        assert prov["provision_id"] == "gb-test-2024-3-1"
        assert prov["label"] == "3.1"
        assert prov["review_status"] == "machine_extracted"

    def test_requirement_fields(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)

        req = result.requirements[0]
        assert req["requirement_id"] == "gb-test-2024-3-1-r1"
        assert req["modality"] == "must"

    def test_deterministic_sorting(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        # Add a second document with earlier ID
        meta_dir = cand / "metadata"
        meta2 = {"title": "A 标准前", "review_status": "draft"}
        (meta_dir / "aa-first.yaml").write_text(
            yaml.dump(meta2, allow_unicode=True), encoding="utf-8"
        )
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        assert result.documents[0]["document_id"] == "aa-first"

    def test_tolerates_missing_dirs(self, tmp_path):
        result = collect_records(
            candidates_dir=tmp_path / "no-candidates",
            drafts_dir=tmp_path / "no-drafts",
        )
        assert result.documents == []
        assert result.provisions == []
        assert result.requirements == []

    def test_detects_duplicate_provision_ids(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        prov_dir = cand / "provisions"
        # Write duplicate provision ID
        dup = [
            {"provision_id": "dup-1", "document_id": "x"},
            {"provision_id": "dup-1", "document_id": "x"},
        ]
        write_jsonl(dup, prov_dir / "dup.jsonl")
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        assert any("Duplicate provision_id: dup-1" in e for e in result.errors)

    def test_detects_duplicate_requirement_ids(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        req_dir = cand / "requirements"
        dup = [
            {"requirement_id": "req-dup-1", "document_id": "x", "provision_id": "y", "modality": "must"},
            {"requirement_id": "req-dup-1", "document_id": "x", "provision_id": "y", "modality": "must"},
        ]
        write_jsonl(dup, req_dir / "dup.jsonl")
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        assert any("Duplicate requirement_id: req-dup-1" in e for e in result.errors)

    def test_draft_without_metadata(self, tmp_path):
        drafts = tmp_path / "documents" / "drafts"
        drafts.mkdir(parents=True)
        fm = {"document_id": "orphan-doc", "title": "孤立文档", "review_status": "draft"}
        fm_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True)
        (drafts / "orphan-doc.md").write_text(
            f"---\n{fm_yaml}---\n\n正文", encoding="utf-8"
        )
        result = collect_records(
            candidates_dir=tmp_path / "_candidates",
            drafts_dir=drafts,
        )
        assert len(result.documents) == 1
        assert result.documents[0]["document_id"] == "orphan-doc"

    def test_merges_draft_into_metadata(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        doc = result.documents[0]
        assert "draft_path" in doc


class TestGenerateMarkdownIndexes:
    def test_generates_documents_index(self, tmp_path):
        documents = [
            {"document_id": "gb-1", "title": "标准一", "document_type": "standard",
             "standard_id": "GB-1", "confidence": "low", "review_status": "draft",
             "source": "meta/gb-1.yaml"},
        ]
        md = generate_documents_index(documents)
        assert "gb-1" in md
        assert "标准一" in md

    def test_generates_provisions_index(self, tmp_path):
        provisions = [
            {"provision_id": "gb-1-3-1", "document_id": "gb-1", "label": "3.1",
             "kind": "clause", "confidence": "low", "review_status": "machine_extracted",
             "source": "prov/gb-1.jsonl"},
        ]
        md = generate_provisions_index(provisions)
        assert "gb-1-3-1" in md

    def test_generates_requirements_index(self, tmp_path):
        requirements = [
            {"requirement_id": "gb-1-3-1-r1", "document_id": "gb-1",
             "provision_id": "gb-1-3-1", "modality": "must", "confidence": "low",
             "review_status": "machine_extracted", "source": "req/gb-1.jsonl"},
        ]
        md = generate_requirements_index(requirements)
        assert "gb-1-3-1-r1" in md

    def test_generates_effective_dates_index(self, tmp_path):
        documents = [
            {"document_id": "gb-1", "standard_id": "GB-1",
             "release_date": "2024-01-01", "effective_date": "2024-07-01",
             "review_status": "draft", "source": "meta/gb-1.yaml"},
        ]
        md = generate_effective_dates_index(documents)
        assert "2024-01-01" in md
        assert "2024-07-01" in md

    def test_generate_markdown_indexes_writes_files(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        out = tmp_path / "indexes"
        outputs = generate_markdown_indexes(result, out)

        assert "documents-index.md" in outputs
        assert "provisions-index.md" in outputs
        assert "requirements-index.md" in outputs
        assert "effective-dates-index.md" in outputs

        for path in outputs.values():
            assert Path(path).exists()

    def test_empty_indexes(self, tmp_path):
        out = tmp_path / "indexes"
        result = IndexResult()
        outputs = generate_markdown_indexes(result, out)
        for path in outputs.values():
            content = Path(path).read_text(encoding="utf-8")
            assert "| " not in content.split("\n")[3:][0] if len(content.split("\n")) > 3 else True


class TestExportJson:
    def test_exports_all_files(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        out = tmp_path / "db" / "json"
        outputs = export_json(result, out)

        assert set(outputs.keys()) == {
            "documents.json", "provisions.json", "requirements.json", "manifest.json"
        }

    def test_json_utf8_chinese(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        out = tmp_path / "db" / "json"
        export_json(result, out)

        docs_path = out / "documents.json"
        content = docs_path.read_text(encoding="utf-8")
        assert "测试标准" in content

    def test_manifest_counts(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        out = tmp_path / "db" / "json"
        export_json(result, out)

        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert manifest["documents"] == 1
        assert manifest["provisions"] == 1
        assert manifest["requirements"] == 1

    def test_manifest_includes_warnings_and_errors(self, tmp_path):
        result = IndexResult(
            warnings=["test warning"],
            errors=["test error"],
        )
        out = tmp_path / "db" / "json"
        export_json(result, out)

        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        assert "test warning" in manifest["warnings"]
        assert "test error" in manifest["errors"]
