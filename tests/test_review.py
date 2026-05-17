"""Tests for review and promotion workflow."""

import json

import pytest
import yaml

from standards_wiki.candidates import write_jsonl
from standards_wiki.review import (
    build_provision_page,
    create_review_manifest,
    load_review_manifest,
    mark_reviewed,
    promote_reviewed,
    save_review_manifest,
)


def _make_provision(provision_id, document_id="test-doc", **overrides):
    """Helper to create a minimal provision record."""
    base = {
        "document_id": document_id,
        "provision_id": provision_id,
        "label": provision_id.split("-")[-1],
        "kind": "clause",
        "title": "test title",
        "text": "test content",
        "locator": {"label": "4.1", "occurrence": 1, "source_offset": 0},
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
        "confidence": "medium",
        "review_status": "machine_extracted",
        "evidence": {"quote": "test quote text"},
    }
    base.update(overrides)
    return base


def _write_provision_candidates(tmp_path, doc_id, provisions):
    """Write provision JSONL under tmp_path/_candidates/provisions/."""
    prov_dir = tmp_path / "_candidates" / "provisions"
    prov_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(provisions, prov_dir / f"{doc_id}.jsonl")


class TestCreateReviewManifest:
    def test_creates_manifest_with_all_pending(self, tmp_path):
        provisions = [
            _make_provision("doc-4-1"),
            _make_provision("doc-4-2"),
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = create_review_manifest("doc", candidates_dir=tmp_path / "_candidates")

        assert manifest["document_id"] == "doc"
        assert len(manifest["provisions"]) == 2
        assert all(e["review_status"] == "pending" for e in manifest["provisions"])

    def test_manifest_written_to_disk(self, tmp_path):
        _write_provision_candidates(tmp_path, "doc", [_make_provision("doc-4-1")])

        create_review_manifest("doc", candidates_dir=tmp_path / "_candidates")

        manifest_path = tmp_path / "_candidates" / "review-manifests" / "doc-manifest.json"
        assert manifest_path.exists()
        loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert loaded["document_id"] == "doc"

    def test_empty_provisions(self, tmp_path):
        _write_provision_candidates(tmp_path, "doc", [])

        manifest = create_review_manifest("doc", candidates_dir=tmp_path / "_candidates")

        assert manifest["provisions"] == []

    def test_missing_provisions_file(self, tmp_path):
        candidates_dir = tmp_path / "_candidates"
        candidates_dir.mkdir()

        manifest = create_review_manifest("doc", candidates_dir=candidates_dir)
        assert manifest["provisions"] == []

    def test_entries_have_extra_fields(self, tmp_path):
        provisions = [
            _make_provision(
                "doc-4-1",
                label="4.1",
                title="General requirements",
                locator={"label": "4.1", "occurrence": 1, "source_offset": 0},
                confidence="high",
                evidence={"quote": "机动车应安装安全座椅"},
            ),
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = create_review_manifest("doc", candidates_dir=tmp_path / "_candidates")
        entry = manifest["provisions"][0]

        assert entry["label"] == "4.1"
        assert entry["title"] == "General requirements"
        assert entry["locator"] == {"label": "4.1", "occurrence": 1, "source_offset": 0}
        assert entry["confidence"] == "high"
        assert entry["short_quote"] == "机动车应安装安全座椅"

    def test_short_quote_truncates_long_text(self, tmp_path):
        long_quote = "x" * 200
        provisions = [
            _make_provision("doc-4-1", evidence={"quote": long_quote}),
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = create_review_manifest("doc", candidates_dir=tmp_path / "_candidates")
        entry = manifest["provisions"][0]

        assert len(entry["short_quote"]) == 123  # 120 + "..."
        assert entry["short_quote"].endswith("...")

    def test_short_quote_falls_back_to_text(self, tmp_path):
        provisions = [
            _make_provision("doc-4-1", text="fallback text content", evidence={}),
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = create_review_manifest("doc", candidates_dir=tmp_path / "_candidates")
        entry = manifest["provisions"][0]

        assert entry["short_quote"] == "fallback text content"

    def test_short_quote_defaults_to_empty(self, tmp_path):
        provisions = [
            {"document_id": "doc", "provision_id": "doc-4-1"},
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = create_review_manifest("doc", candidates_dir=tmp_path / "_candidates")
        entry = manifest["provisions"][0]

        assert entry["short_quote"] == ""


class TestMarkReviewed:
    def test_marks_selected_ids(self):
        manifest = {
            "document_id": "doc",
            "provisions": [
                {"provision_id": "doc-4-1", "review_status": "pending"},
                {"provision_id": "doc-4-2", "review_status": "pending"},
                {"provision_id": "doc-4-3", "review_status": "pending"},
            ],
        }

        result = mark_reviewed(manifest, {"doc-4-1", "doc-4-3"})

        assert result["provisions"][0]["review_status"] == "reviewed"
        assert result["provisions"][1]["review_status"] == "pending"
        assert result["provisions"][2]["review_status"] == "reviewed"

    def test_does_not_mutate_input(self):
        manifest = {
            "document_id": "doc",
            "provisions": [
                {"provision_id": "doc-4-1", "review_status": "pending"},
            ],
        }

        result = mark_reviewed(manifest, {"doc-4-1"})

        assert manifest["provisions"][0]["review_status"] == "pending"
        assert result["provisions"][0]["review_status"] == "reviewed"

    def test_marks_none(self):
        manifest = {
            "document_id": "doc",
            "provisions": [
                {"provision_id": "doc-4-1", "review_status": "pending"},
            ],
        }

        result = mark_reviewed(manifest, set())

        assert result["provisions"][0]["review_status"] == "pending"

    def test_preserves_document_id(self):
        manifest = {
            "document_id": "gb-7258-2017",
            "provisions": [],
        }

        result = mark_reviewed(manifest, set())

        assert result["document_id"] == "gb-7258-2017"

    def test_preserves_extra_fields(self):
        manifest = {
            "document_id": "doc",
            "provisions": [
                {
                    "provision_id": "doc-4-1",
                    "review_status": "pending",
                    "label": "4.1",
                    "title": "General requirements",
                    "locator": {"label": "4.1", "occurrence": 1, "source_offset": 0},
                    "confidence": "high",
                    "short_quote": "机动车应安装安全座椅",
                },
                {
                    "provision_id": "doc-4-2",
                    "review_status": "pending",
                    "label": "4.2",
                    "title": "Braking system",
                    "locator": {"label": "4.2", "occurrence": 1, "source_offset": 100},
                    "confidence": "medium",
                    "short_quote": "brake test",
                },
            ],
        }

        result = mark_reviewed(manifest, {"doc-4-1"})

        reviewed_entry = result["provisions"][0]
        assert reviewed_entry["review_status"] == "reviewed"
        assert reviewed_entry["label"] == "4.1"
        assert reviewed_entry["title"] == "General requirements"
        assert reviewed_entry["locator"]["label"] == "4.1"
        assert reviewed_entry["confidence"] == "high"
        assert reviewed_entry["short_quote"] == "机动车应安装安全座椅"

        unreviewed_entry = result["provisions"][1]
        assert unreviewed_entry["review_status"] == "pending"
        assert unreviewed_entry["label"] == "4.2"
        assert unreviewed_entry["title"] == "Braking system"


class TestPromoteReviewed:
    def test_promotes_only_reviewed(self, tmp_path):
        provisions = [
            _make_provision("doc-4-1"),
            _make_provision("doc-4-2"),
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                    {"provision_id": "doc-4-2", "review_status": "pending"},
                ],
            },
            {"doc-4-2"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        result = promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        assert len(result["written"]) == 1
        assert "doc-4-2" in result["written"][0]
        assert result["missing_reviewed_ids"] == []

        # Unreviewed should not be promoted
        assert not (tmp_path / "provisions" / "doc" / "doc-4-1.md").exists()
        assert (tmp_path / "provisions" / "doc" / "doc-4-2.md").exists()

    def test_unreviewed_candidates_skipped(self, tmp_path):
        provisions = [_make_provision("doc-4-1")]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = {
            "document_id": "doc",
            "provisions": [
                {"provision_id": "doc-4-1", "review_status": "pending"},
            ],
        }
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        result = promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        assert result["written"] == []
        assert result["missing_reviewed_ids"] == []
        assert not (tmp_path / "provisions" / "doc").exists()

    def test_promoted_page_has_review_status(self, tmp_path):
        provisions = [_make_provision("doc-4-1")]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                ],
            },
            {"doc-4-1"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        page_path = tmp_path / "provisions" / "doc" / "doc-4-1.md"
        content = page_path.read_text(encoding="utf-8")
        fm, _ = _split_frontmatter(content)

        assert fm["review_status"] == "reviewed"

    def test_promoted_page_preserves_source_locator(self, tmp_path):
        provisions = [
            _make_provision(
                "doc-4-1",
                locator={"label": "4.1", "occurrence": 2, "source_offset": 150},
            )
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                ],
            },
            {"doc-4-1"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        page_path = tmp_path / "provisions" / "doc" / "doc-4-1.md"
        fm, _ = _split_frontmatter(page_path.read_text(encoding="utf-8"))

        assert fm["locator"]["label"] == "4.1"
        assert fm["locator"]["occurrence"] == 2
        assert fm["locator"]["source_offset"] == 150

    def test_promoted_page_preserves_evidence_quote(self, tmp_path):
        provisions = [
            _make_provision(
                "doc-4-1",
                evidence={"quote": "机动车应安装安全座椅"},
            )
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                ],
            },
            {"doc-4-1"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        page_path = tmp_path / "provisions" / "doc" / "doc-4-1.md"
        content = page_path.read_text(encoding="utf-8")

        assert "机动车应安装安全座椅" in content

    def test_promote_multiple_reviewed(self, tmp_path):
        provisions = [
            _make_provision("doc-4-1"),
            _make_provision("doc-4-2"),
            _make_provision("doc-4-3"),
        ]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": p["provision_id"], "review_status": "pending"}
                    for p in provisions
                ],
            },
            {"doc-4-1", "doc-4-3"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        result = promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        assert len(result["written"]) == 2
        assert result["missing_reviewed_ids"] == []
        assert not (tmp_path / "provisions" / "doc" / "doc-4-2.md").exists()

    def test_nothing_promoted_when_nothing_reviewed(self, tmp_path):
        provisions = [_make_provision("doc-4-1")]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = {
            "document_id": "doc",
            "provisions": [
                {"provision_id": "doc-4-1", "review_status": "pending"},
            ],
        }
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        result = promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        assert result["written"] == []

    def test_missing_reviewed_ids_reported(self, tmp_path):
        provisions = [_make_provision("doc-4-1")]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                    {"provision_id": "doc-4-2", "review_status": "pending"},
                    {"provision_id": "doc-4-3", "review_status": "pending"},
                ],
            },
            {"doc-4-1", "doc-4-2", "doc-4-3"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        result = promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        assert len(result["written"]) == 1
        assert "doc-4-1" in result["written"][0]
        assert result["missing_reviewed_ids"] == ["doc-4-2", "doc-4-3"]

    def test_all_reviewed_missing(self, tmp_path):
        _write_provision_candidates(tmp_path, "doc", [])

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                ],
            },
            {"doc-4-1"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        save_review_manifest(manifest, manifest_dir / "doc-manifest.json")

        result = promote_reviewed(
            "doc",
            candidates_dir=tmp_path / "_candidates",
            manifest_path=manifest_dir / "doc-manifest.json",
            output_dir=tmp_path / "provisions",
        )

        assert result["written"] == []
        assert result["missing_reviewed_ids"] == ["doc-4-1"]


class TestBuildProvisionPage:
    def test_page_has_frontmatter_and_body(self):
        provision = _make_provision("doc-4-1")
        page = build_provision_page(provision)

        assert page.startswith("---\n")
        fm, body = _split_frontmatter(page)
        assert fm["provision_id"] == "doc-4-1"
        assert fm["review_status"] == "reviewed"
        assert "原文" in body

    def test_page_preserves_evidence_quote(self):
        provision = _make_provision(
            "doc-4-1", evidence={"quote": "specific quote content"}
        )
        page = build_provision_page(provision)

        assert "specific quote content" in page


class TestSaveLoadManifest:
    def test_round_trip(self, tmp_path):
        manifest = {
            "document_id": "doc",
            "provisions": [
                {"provision_id": "doc-4-1", "review_status": "pending"},
            ],
        }

        path = save_review_manifest(manifest, tmp_path / "test-manifest.json")
        loaded = load_review_manifest(path)

        assert loaded == manifest


def _split_frontmatter(text):
    """Split frontmatter from Markdown text."""
    if not text.startswith("---"):
        return {}, text
    close = text.find("\n---", 3)
    if close == -1:
        return {}, text
    fm = yaml.safe_load(text[3:close])
    body = text[close + 4:]
    return fm if isinstance(fm, dict) else {}, body
