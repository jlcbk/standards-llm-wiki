"""Tests for graph JSONL export."""

import json
from pathlib import Path

import pytest
import yaml

from standards_wiki.graph_export import export_graph


def _write_yaml(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _make_candidates(
    tmp: Path,
    docs: list[dict] | None = None,
    provisions: list[dict] | None = None,
    requirements: list[dict] | None = None,
    topic_tags: dict | None = None,
) -> Path:
    cdir = tmp / "candidates"
    cdir.mkdir(exist_ok=True)

    if docs:
        for doc in docs:
            doc_id = doc.get("document_id", "test-doc")
            meta = doc.get("meta", {})
            _write_yaml(cdir / "metadata" / f"{doc_id}.yaml", meta)

    if provisions:
        doc_id = provisions[0].get("document_id", "test-doc") if provisions else "test-doc"
        _write_jsonl(cdir / "provisions" / f"{doc_id}.jsonl", provisions)

    if requirements:
        doc_id = requirements[0].get("document_id", "test-doc") if requirements else "test-doc"
        _write_jsonl(cdir / "requirements" / f"{doc_id}.jsonl", requirements)

    if topic_tags:
        doc_id = topic_tags.get("document_id", "test-doc")
        _write_json(cdir / "topic-tags" / f"{doc_id}.json", topic_tags)

    return cdir


# ── Basic node/edge generation ──────────────────────────────────────────


class TestExportGraph:

    def test_produces_nodes_and_edges_files(self, tmp_path):
        cdir = _make_candidates(tmp_path)
        out = tmp_path / "graph"
        result = export_graph(cdir, out)

        assert (out / "nodes.jsonl").exists()
        assert (out / "edges.jsonl").exists()
        assert result["nodes"] == 0
        assert result["edges"] == 0

    def test_document_nodes(self, tmp_path):
        cdir = _make_candidates(tmp_path, docs=[
            {"document_id": "gb-test", "meta": {
                "title": "Test Standard",
                "document_type": "standard",
                "publisher": "SAC",
                "confidence": "high",
                "review_status": "reviewed",
            }},
        ])
        out = tmp_path / "graph"
        result = export_graph(cdir, out)

        assert result["nodes"] == 1
        nodes = _read_jsonl(out / "nodes.jsonl")
        assert nodes[0]["id"] == "gb-test"
        assert nodes[0]["type"] == "Document"
        assert nodes[0]["props"]["title"] == "Test Standard"

    def test_provision_nodes_with_has_provision_edge(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
                {"document_id": "doc1", "provision_id": "doc1-4-2", "label": "4.2", "kind": "clause"},
            ],
        )
        out = tmp_path / "graph"
        result = export_graph(cdir, out)

        assert result["provisions"] == 2
        edges = _read_jsonl(out / "edges.jsonl")
        hp_edges = [e for e in edges if e["type"] == "HAS_PROVISION"]
        assert len(hp_edges) == 2
        sources = {e["source"] for e in hp_edges}
        assert sources == {"doc1"}

    def test_subsection_of_edges(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4", "label": "4", "kind": "section"},
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
                {"document_id": "doc1", "provision_id": "doc1-4-1-1", "label": "4.1.1", "kind": "item"},
            ],
        )
        out = tmp_path / "graph"
        export_graph(cdir, out)

        edges = _read_jsonl(out / "edges.jsonl")
        sub_edges = {(e["source"], e["target"]) for e in edges if e["type"] == "SUBSECTION_OF"}
        assert ("doc1-4-1", "doc1-4") in sub_edges
        assert ("doc1-4-1-1", "doc1-4-1") in sub_edges

    def test_requirement_nodes_and_edges(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
            requirements=[
                {
                    "requirement_id": "doc1-4-1-r1",
                    "document_id": "doc1",
                    "provision_id": "doc1-4-1",
                    "modality": "must",
                    "confidence": "high",
                    "review_status": "reviewed",
                },
            ],
        )
        out = tmp_path / "graph"
        result = export_graph(cdir, out)

        nodes = _read_jsonl(out / "nodes.jsonl")
        req_nodes = [n for n in nodes if n["type"] == "Requirement"]
        assert len(req_nodes) == 1
        assert req_nodes[0]["id"] == "doc1-4-1-r1"

        edges = _read_jsonl(out / "edges.jsonl")
        hr_edges = [e for e in edges if e["type"] == "HAS_REQUIREMENT"]
        assert len(hr_edges) == 1
        assert hr_edges[0]["source"] == "doc1-4-1"
        assert hr_edges[0]["target"] == "doc1-4-1-r1"

    def test_topic_and_entity_nodes(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
            topic_tags={
                "document_id": "doc1",
                "provisions": [
                    {
                        "id": "doc1-4-1",
                        "topics": ["braking", "safety"],
                        "entities": ["vehicle", "driver"],
                    },
                ],
            },
        )
        out = tmp_path / "graph"
        export_graph(cdir, out)

        nodes = _read_jsonl(out / "nodes.jsonl")
        topic_nodes = [n for n in nodes if n["type"] == "Topic"]
        entity_nodes = [n for n in nodes if n["type"] == "Entity"]
        assert len(topic_nodes) == 2
        assert len(entity_nodes) == 2

        edges = _read_jsonl(out / "edges.jsonl")
        about_edges = [e for e in edges if e["type"] == "ABOUT"]
        mentions_edges = [e for e in edges if e["type"] == "MENTIONS"]
        assert len(about_edges) == 2
        assert len(mentions_edges) == 2

    def test_replaces_edges_when_metadata_present(self, tmp_path):
        cdir = _make_candidates(tmp_path, docs=[
            {"document_id": "doc-v1", "meta": {"title": "V1", "replaces": "doc-v0"}},
            {"document_id": "doc-v2", "meta": {"title": "V2", "replaced": "doc-v3"}},
        ])
        out = tmp_path / "graph"
        export_graph(cdir, out)

        edges = _read_jsonl(out / "edges.jsonl")
        replaces = [e for e in edges if e["type"] == "REPLACES"]
        replaced_by = [e for e in edges if e["type"] == "REPLACED_BY"]
        assert len(replaces) == 1
        assert replaces[0]["source"] == "doc-v1"
        assert replaces[0]["target"] == "doc-v0"
        assert len(replaced_by) == 1
        assert replaced_by[0]["source"] == "doc-v2"

    def test_no_replaces_edges_when_metadata_absent(self, tmp_path):
        cdir = _make_candidates(tmp_path, docs=[
            {"document_id": "doc1", "meta": {"title": "Doc"}},
        ])
        out = tmp_path / "graph"
        export_graph(cdir, out)

        edges = _read_jsonl(out / "edges.jsonl")
        replaces = [e for e in edges if e["type"] in ("REPLACES", "REPLACED_BY")]
        assert len(replaces) == 0


# ── Integrity checks ────────────────────────────────────────────────────


class TestIntegrity:

    def test_no_dangling_edges(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
            requirements=[
                {"requirement_id": "doc1-4-1-r1", "document_id": "doc1", "provision_id": "doc1-4-1"},
            ],
            topic_tags={
                "document_id": "doc1",
                "provisions": [{"id": "doc1-4-1", "topics": ["safety"], "entities": []}],
            },
        )
        out = tmp_path / "graph"
        export_graph(cdir, out)

        nodes = _read_jsonl(out / "nodes.jsonl")
        node_ids = {n["id"] for n in nodes}
        edges = _read_jsonl(out / "edges.jsonl")

        for edge in edges:
            assert edge["source"] in node_ids, f"Dangling source: {edge['source']}"
            assert edge["target"] in node_ids, f"Dangling target: {edge['target']}"

    def test_idempotent(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
        )
        out1 = tmp_path / "graph1"
        out2 = tmp_path / "graph2"
        export_graph(cdir, out1)
        export_graph(cdir, out2)

        assert (out1 / "nodes.jsonl").read_text() == (out2 / "nodes.jsonl").read_text()
        assert (out1 / "edges.jsonl").read_text() == (out2 / "edges.jsonl").read_text()

    def test_sorted_output(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-5", "label": "5", "kind": "section"},
                {"document_id": "doc1", "provision_id": "doc1-4-2", "label": "4.2", "kind": "clause"},
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
        )
        out = tmp_path / "graph"
        export_graph(cdir, out)

        nodes = _read_jsonl(out / "nodes.jsonl")
        node_ids = [n["id"] for n in nodes]
        assert node_ids == sorted(node_ids)


# ── Edge cases ───────────────────────────────────────────────────────────


class TestEdgeCases:

    def test_empty_candidates_produces_empty_files(self, tmp_path):
        cdir = tmp_path / "empty_candidates"
        cdir.mkdir()
        out = tmp_path / "graph"
        result = export_graph(cdir, out)

        assert result["nodes"] == 0
        assert result["edges"] == 0
        assert (out / "nodes.jsonl").read_text() == ""
        assert (out / "edges.jsonl").read_text() == ""

    def test_missing_optional_files(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
        )
        out = tmp_path / "graph"
        result = export_graph(cdir, out)

        assert result["nodes"] >= 1
        assert result["edges"] >= 1

    def test_deduplicated_edges(self, tmp_path):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
            topic_tags={
                "document_id": "doc1",
                "provisions": [
                    {"id": "doc1-4-1", "topics": ["safety"], "entities": []},
                ],
            },
        )
        out = tmp_path / "graph"
        export_graph(cdir, out)

        edges = _read_jsonl(out / "edges.jsonl")
        edge_keys = [(e["source"], e["target"], e["type"]) for e in edges]
        assert len(edge_keys) == len(set(edge_keys))


# ── CLI ──────────────────────────────────────────────────────────────────


class TestCLI:

    def test_cli_main(self, tmp_path, monkeypatch, capsys):
        cdir = _make_candidates(
            tmp_path,
            docs=[{"document_id": "doc1", "meta": {"title": "Doc"}}],
            provisions=[
                {"document_id": "doc1", "provision_id": "doc1-4-1", "label": "4.1", "kind": "clause"},
            ],
        )
        out = tmp_path / "graph"

        import tools.export_graph as mod
        mod.main(["--candidates-dir", str(cdir), "--out", str(out)])

        captured = capsys.readouterr()
        assert "Nodes: 2" in captured.out
        assert "Edges: 1" in captured.out


# ── Helpers ──────────────────────────────────────────────────────────────


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records
