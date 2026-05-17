"""Tests for tools/tag_candidates.py CLI."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_TAG_MOD_PATH = _PROJECT_ROOT / "tools" / "tag_candidates.py"

_spec = importlib.util.spec_from_file_location("tag_candidates", _TAG_MOD_PATH)
_tag_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tag_mod)
tag_main = _tag_mod.main


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _run_cli(document_id: str, candidates_dir: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [
            sys.executable,
            "tools/tag_candidates.py",
            document_id,
            "--candidates-dir",
            candidates_dir,
        ],
        capture_output=True,
        text=True,
    )


class TestTagCandidates:
    def test_provisions_and_requirements(self, tmp_path: Path):
        prov_dir = tmp_path / "provisions"
        req_dir = tmp_path / "requirements"
        prov_dir.mkdir()
        req_dir.mkdir()

        _write_jsonl(prov_dir / "test-doc.jsonl", [
            {"document_id": "test-doc", "provision_id": "test-doc-1", "text": "座椅强度"},
        ])
        _write_jsonl(req_dir / "test-doc.jsonl", [
            {"document_id": "test-doc", "requirement_id": "test-doc-r1", "text": "制动"},
        ])

        result = _run_cli("test-doc", str(tmp_path))
        assert result.returncode == 0

        out = json.loads((tmp_path / "topic-tags" / "test-doc.json").read_text())
        assert out["document_id"] == "test-doc"
        assert len(out["provisions"]) == 1
        assert len(out["requirements"]) == 1
        assert out["provisions"][0]["id"] == "test-doc-1"
        assert "seats" in out["provisions"][0]["topics"]
        assert out["requirements"][0]["id"] == "test-doc-r1"
        assert "braking-system" in out["requirements"][0]["topics"]

    def test_no_requirements_file(self, tmp_path: Path):
        prov_dir = tmp_path / "provisions"
        prov_dir.mkdir()

        _write_jsonl(prov_dir / "solo.jsonl", [
            {"document_id": "solo", "provision_id": "solo-1", "text": "灯光"},
        ])

        result = _run_cli("solo", str(tmp_path))
        assert result.returncode == 0

        out = json.loads((tmp_path / "topic-tags" / "solo.json").read_text())
        assert out["document_id"] == "solo"
        assert len(out["provisions"]) == 1
        assert out["requirements"] == []

    def test_output_structure_fields(self, tmp_path: Path):
        prov_dir = tmp_path / "provisions"
        prov_dir.mkdir()

        _write_jsonl(prov_dir / "struct.jsonl", [
            {"document_id": "struct", "provision_id": "struct-1", "text": "校车座椅"},
        ])

        _run_cli("struct", str(tmp_path))
        out = json.loads((tmp_path / "topic-tags" / "struct.json").read_text())

        prov = out["provisions"][0]
        assert "document_id" in prov
        assert "id" in prov
        assert "topics" in prov
        assert "entities" in prov

    def test_missing_provisions_exits_nonzero(self, tmp_path: Path):
        (tmp_path / "provisions").mkdir()

        result = _run_cli("nonexistent", str(tmp_path))
        assert result.returncode != 0
        assert "not found" in result.stderr

    def test_matched_keywords_in_output(self, tmp_path: Path):
        prov_dir = tmp_path / "provisions"
        prov_dir.mkdir()

        _write_jsonl(prov_dir / "mk.jsonl", [
            {"document_id": "mk", "provision_id": "mk-1", "text": "座椅头枕靠背"},
        ])

        _run_cli("mk", str(tmp_path))
        out = json.loads((tmp_path / "topic-tags" / "mk.json").read_text())

        prov = out["provisions"][0]
        assert "matched_keywords" in prov
        mk = prov["matched_keywords"]
        assert mk["topics"]["seats"] == ["头枕", "座椅", "靠背"]

    def test_main_with_argv(self, tmp_path: Path):
        prov_dir = tmp_path / "provisions"
        prov_dir.mkdir()

        _write_jsonl(prov_dir / "argv.jsonl", [
            {"document_id": "argv", "provision_id": "argv-1", "text": "制动"},
        ])

        tag_main(argv=["argv", "--candidates-dir", str(tmp_path)])

        out = json.loads((tmp_path / "topic-tags" / "argv.json").read_text())
        assert out["document_id"] == "argv"
        prov = out["provisions"][0]
        assert "braking-system" in prov["topics"]
        assert "matched_keywords" in prov
        assert "制动" in prov["matched_keywords"]["topics"]["braking-system"]
