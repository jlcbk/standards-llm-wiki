"""Tests for export-level benchmark and smoke checks (Phase 5)."""

import json
import sqlite3
from pathlib import Path

import pytest

from standards_wiki.eval import load_checks, run_checks
from standards_wiki.graph_export import export_graph
from standards_wiki.sqlite_export import export_sqlite


# ---------------------------------------------------------------------------
# Fixtures: minimal candidates directory
# ---------------------------------------------------------------------------

_DOC_ID = "test-doc"


def _write_candidates(tmp: Path) -> Path:
    """Create a minimal candidates directory and return it."""
    c = tmp / "candidates"
    c.mkdir()

    # metadata
    meta_dir = c / "metadata"
    meta_dir.mkdir()
    (meta_dir / f"{_DOC_ID}.yaml").write_text(
        "title: Test Standard\nstandard_id: TS-001\npublisher: Test\n", encoding="utf-8"
    )

    # provisions
    prov_dir = c / "provisions"
    prov_dir.mkdir()
    prov = {
        "provision_id": f"{_DOC_ID}-4.1",
        "document_id": _DOC_ID,
        "label": "4.1",
        "kind": "section",
        "title": "制动系统 brakecheck",
        "text": "机动车制动系统应满足基本要求。brakecheck",
        "confidence": "high",
        "review_status": "approved",
    }
    (prov_dir / f"{_DOC_ID}.jsonl").write_text(
        json.dumps(prov, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # requirements
    req_dir = c / "requirements"
    req_dir.mkdir()
    req = {
        "requirement_id": f"{_DOC_ID}-4.1-r1",
        "document_id": _DOC_ID,
        "provision_id": f"{_DOC_ID}-4.1",
        "modality": "must",
        "subject": "制动系统 brakecheck",
        "action": "满足",
        "object": "基本要求",
        "evidence": {"quote": "机动车制动系统应满足基本要求 brakecheck"},
        "confidence": "high",
        "review_status": "approved",
    }
    (req_dir / f"{_DOC_ID}.jsonl").write_text(
        json.dumps(req, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    return c


@pytest.fixture()
def candidates(tmp_path):
    return _write_candidates(tmp_path)


@pytest.fixture()
def exported(candidates, tmp_path):
    """Export SQLite + Graph, return (candidates_dir, db_path, graph_dir)."""
    db_path = str(tmp_path / "test.db")
    graph_dir = str(tmp_path / "graph")
    export_sqlite(candidates, db_path)
    export_graph(candidates, graph_dir)
    return candidates, db_path, graph_dir


def _ctx(db_path=None, graph_dir=None):
    ctx = {
        "documents": [],
        "provisions": [],
        "requirements": [],
        "topic_tags": {},
    }
    if db_path:
        ctx["sqlite_db_path"] = db_path
    if graph_dir:
        ctx["graph_dir"] = graph_dir
    return ctx


# ---------------------------------------------------------------------------
# sqlite_table_row_count
# ---------------------------------------------------------------------------

class TestSqliteTableRowCount:
    def test_pass(self, exported):
        _, db_path, _ = exported
        checks = [{"id": "r1", "type": "sqlite_table_row_count",
                    "expected": {"table": "documents", "min_count": 1}}]
        result = run_checks(checks, _ctx(db_path=db_path))
        assert result["passed"] == 1
        assert result["failed"] == 0

    def test_fail_too_few(self, exported):
        _, db_path, _ = exported
        checks = [{"id": "r2", "type": "sqlite_table_row_count",
                    "expected": {"table": "provisions", "min_count": 999}}]
        result = run_checks(checks, _ctx(db_path=db_path))
        assert result["failed"] == 1
        assert "need >=" in result["failures"][0]["reason"]

    def test_fail_no_db(self, tmp_path):
        checks = [{"id": "r3", "type": "sqlite_table_row_count",
                    "expected": {"table": "documents", "min_count": 1}}]
        result = run_checks(checks, _ctx(db_path=str(tmp_path / "no.db")))
        assert result["failed"] == 1

    def test_context_fallback(self, exported):
        _, db_path, _ = exported
        checks = [{"id": "r4", "type": "sqlite_table_row_count",
                    "expected": {"table": "documents", "min_count": 1}}]
        result = run_checks(checks, _ctx(db_path=db_path))
        assert result["passed"] == 1


# ---------------------------------------------------------------------------
# sqlite_fts_result
# ---------------------------------------------------------------------------

class TestSqliteFtsResult:
    def test_pass(self, exported):
        _, db_path, _ = exported
        checks = [{"id": "f1", "type": "sqlite_fts_result",
                    "expected": {"query": "brakecheck", "mode": "provisions", "min_count": 1}}]
        result = run_checks(checks, _ctx(db_path=db_path))
        assert result["passed"] == 1

    def test_fail_too_few(self, exported):
        _, db_path, _ = exported
        checks = [{"id": "f2", "type": "sqlite_fts_result",
                    "expected": {"query": "不存在的关键词", "mode": "provisions", "min_count": 1}}]
        result = run_checks(checks, _ctx(db_path=db_path))
        assert result["failed"] == 1

    def test_with_document_id(self, exported):
        _, db_path, _ = exported
        checks = [{"id": "f3", "type": "sqlite_fts_result",
                    "expected": {"query": "brakecheck", "mode": "provisions",
                                 "document_id": _DOC_ID, "min_count": 1}}]
        result = run_checks(checks, _ctx(db_path=db_path))
        assert result["passed"] == 1


# ---------------------------------------------------------------------------
# graph_node_exists
# ---------------------------------------------------------------------------

class TestGraphNodeExists:
    def test_pass(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "n1", "type": "graph_node_exists",
                    "expected": {"id": _DOC_ID, "type": "Document"}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["passed"] == 1

    def test_pass_provision(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "n2", "type": "graph_node_exists",
                    "expected": {"id": f"{_DOC_ID}-4.1", "type": "Provision"}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["passed"] == 1

    def test_fail_wrong_type(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "n3", "type": "graph_node_exists",
                    "expected": {"id": _DOC_ID, "type": "Provision"}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["failed"] == 1
        assert "expected 'Provision'" in result["failures"][0]["reason"]

    def test_fail_not_found(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "n4", "type": "graph_node_exists",
                    "expected": {"id": "nonexistent", "type": "Document"}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["failed"] == 1


# ---------------------------------------------------------------------------
# graph_edge_exists
# ---------------------------------------------------------------------------

class TestGraphEdgeExists:
    def test_pass_has_provision(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "e1", "type": "graph_edge_exists",
                    "expected": {"source": _DOC_ID,
                                 "target": f"{_DOC_ID}-4.1",
                                 "type": "HAS_PROVISION"}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["passed"] == 1

    def test_fail_wrong_type(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "e2", "type": "graph_edge_exists",
                    "expected": {"source": _DOC_ID,
                                 "target": f"{_DOC_ID}-4.1",
                                 "type": "WRONG_TYPE"}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["failed"] == 1

    def test_fail_missing_field(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "e3", "type": "graph_edge_exists",
                    "expected": {"source": _DOC_ID, "type": "HAS_PROVISION"}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["failed"] == 1
        assert "Missing" in result["failures"][0]["reason"]


# ---------------------------------------------------------------------------
# graph_edge_integrity
# ---------------------------------------------------------------------------

class TestGraphEdgeIntegrity:
    def test_pass(self, exported):
        _, _, graph_dir = exported
        checks = [{"id": "i1", "type": "graph_edge_integrity",
                    "expected": {}}]
        result = run_checks(checks, _ctx(graph_dir=graph_dir))
        assert result["passed"] == 1

    def test_fail_broken_edge(self, tmp_path):
        gdir = tmp_path / "graph_broken"
        gdir.mkdir()
        (gdir / "nodes.jsonl").write_text(
            json.dumps({"id": "n1", "type": "Doc"}) + "\n", encoding="utf-8"
        )
        (gdir / "edges.jsonl").write_text(
            json.dumps({"source": "n1", "target": "n_missing", "type": "LINK"}) + "\n",
            encoding="utf-8"
        )
        checks = [{"id": "i2", "type": "graph_edge_integrity", "expected": {}}]
        result = run_checks(checks, _ctx(graph_dir=str(gdir)))
        assert result["failed"] == 1
        assert "missing" in result["failures"][0]["reason"]


# ---------------------------------------------------------------------------
# Backward compatibility: old checks still work
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    def test_old_check_types_unchanged(self):
        ctx = {
            "documents": [{"document_id": "d1"}],
            "provisions": [],
            "requirements": [],
            "topic_tags": {},
        }
        checks = [{"id": "old1", "type": "document_id_exists", "expected": "d1"}]
        result = run_checks(checks, ctx)
        assert result["passed"] == 1


# ---------------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------------

class TestEvalExportsCLI:
    def test_main_smoke(self, candidates, tmp_path):
        checks_path = tmp_path / "checks.jsonl"
        checks_path.write_text(
            json.dumps({"id": "c1", "type": "sqlite_table_row_count",
                        "expected": {"table": "documents", "min_count": 1}}) + "\n",
            encoding="utf-8"
        )
        from tools.eval_exports import main
        with pytest.raises(SystemExit) as exc_info:
            main([
                str(checks_path),
                "--candidates-dir", str(candidates),
            ])
        assert exc_info.value.code == 0

    def test_main_failure_exit(self, candidates, tmp_path):
        checks_path = tmp_path / "checks.jsonl"
        checks_path.write_text(
            json.dumps({"id": "c2", "type": "sqlite_table_row_count",
                        "expected": {"table": "documents", "min_count": 999}}) + "\n",
            encoding="utf-8"
        )
        from tools.eval_exports import main
        with pytest.raises(SystemExit) as exc_info:
            main([
                str(checks_path),
                "--candidates-dir", str(candidates),
            ])
        assert exc_info.value.code == 1
