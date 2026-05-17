"""Tests for review and promotion CLI tools."""

import json

import pytest

from standards_wiki.candidates import write_jsonl
from standards_wiki.review import (
    create_review_manifest,
    mark_reviewed,
    save_review_manifest,
)

from tools.review_candidates import main as review_main
from tools.promote_candidates import main as promote_main


def _make_provision(provision_id, document_id="doc"):
    return {
        "document_id": document_id,
        "provision_id": provision_id,
        "label": provision_id.split("-")[-1],
        "kind": "clause",
        "title": "test",
        "text": "content",
        "locator": {"label": "4.1", "occurrence": 1, "source_offset": 0},
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
        "confidence": "medium",
        "review_status": "machine_extracted",
        "evidence": {"quote": "test quote"},
    }


def _write_provision_candidates(tmp_path, doc_id, provisions):
    prov_dir = tmp_path / "_candidates" / "provisions"
    prov_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(provisions, prov_dir / f"{doc_id}.jsonl")


class TestReviewCliManifest:
    def test_creates_manifest(self, tmp_path, capsys):
        _write_provision_candidates(
            tmp_path, "doc", [_make_provision("doc-4-1"), _make_provision("doc-4-2")]
        )

        review_main(["manifest", "doc", "--candidates-dir", str(tmp_path / "_candidates")])

        out = capsys.readouterr().out
        assert "Total provisions: 2" in out

    def test_manifest_command_writes_file(self, tmp_path):
        _write_provision_candidates(tmp_path, "doc", [_make_provision("doc-4-1")])

        review_main(["manifest", "doc", "--candidates-dir", str(tmp_path / "_candidates")])

        manifest_path = tmp_path / "_candidates" / "review-manifests" / "doc-manifest.json"
        assert manifest_path.exists()


class TestReviewCliMark:
    def test_marks_provisions_reviewed(self, tmp_path, capsys):
        manifest = {
            "document_id": "doc",
            "provisions": [
                {"provision_id": "doc-4-1", "review_status": "pending"},
                {"provision_id": "doc-4-2", "review_status": "pending"},
            ],
        }
        manifest_path = tmp_path / "doc-manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        review_main(["mark", str(manifest_path), "doc-4-1"])

        out = capsys.readouterr().out
        assert "Marked 1" in out

        updated = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert updated["provisions"][0]["review_status"] == "reviewed"
        assert updated["provisions"][1]["review_status"] == "pending"


class TestPromoteCli:
    def test_promotes_reviewed(self, tmp_path, capsys):
        provisions = [_make_provision("doc-4-1"), _make_provision("doc-4-2")]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                    {"provision_id": "doc-4-2", "review_status": "pending"},
                ],
            },
            {"doc-4-1"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        manifest_path = manifest_dir / "doc-manifest.json"
        save_review_manifest(manifest, manifest_path)

        promote_main([
            "doc",
            "--candidates-dir", str(tmp_path / "_candidates"),
            "--manifest-path", str(manifest_path),
            "--output-dir", str(tmp_path / "provisions"),
        ])

        out = capsys.readouterr().out
        assert "Promoted 1" in out
        assert (tmp_path / "provisions" / "doc" / "doc-4-1.md").exists()
        assert not (tmp_path / "provisions" / "doc" / "doc-4-2.md").exists()

    def test_missing_reviewed_id_exits_with_warning(self, tmp_path, capsys):
        provisions = [_make_provision("doc-4-1")]
        _write_provision_candidates(tmp_path, "doc", provisions)

        manifest = mark_reviewed(
            {
                "document_id": "doc",
                "provisions": [
                    {"provision_id": "doc-4-1", "review_status": "pending"},
                    {"provision_id": "doc-4-missing", "review_status": "pending"},
                ],
            },
            {"doc-4-1", "doc-4-missing"},
        )
        manifest_dir = tmp_path / "manifests"
        manifest_dir.mkdir()
        manifest_path = manifest_dir / "doc-manifest.json"
        save_review_manifest(manifest, manifest_path)

        with pytest.raises(SystemExit) as exc_info:
            promote_main([
                "doc",
                "--candidates-dir", str(tmp_path / "_candidates"),
                "--manifest-path", str(manifest_path),
                "--output-dir", str(tmp_path / "provisions"),
            ])
        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "doc-4-missing" in captured.err

        assert (tmp_path / "provisions" / "doc" / "doc-4-1.md").exists()

    def test_no_reviewed_shows_message(self, tmp_path, capsys):
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
        manifest_path = manifest_dir / "doc-manifest.json"
        save_review_manifest(manifest, manifest_path)

        promote_main([
            "doc",
            "--candidates-dir", str(tmp_path / "_candidates"),
            "--manifest-path", str(manifest_path),
            "--output-dir", str(tmp_path / "provisions"),
        ])

        out = capsys.readouterr().out
        assert "No reviewed provisions" in out
