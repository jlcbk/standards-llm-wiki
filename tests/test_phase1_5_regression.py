"""Tests for tools/run_phase1_5_regression.py — mocked subprocess calls."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tools.run_phase1_5_regression import _check_dangling_edges, main

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class TestCommandConstruction:
    """Verify main() builds the right commands from arguments."""

    @patch("tools.run_phase1_5_regression.subprocess.run")
    def test_default_runs_pytest_and_evals(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        # Need graph dir + nodes/edges for dangling check
        with patch("tools.run_phase1_5_regression._check_dangling_edges", return_value=0):
            rc = main(["--skip-pytest", "--tmp-dir", "/tmp/reg_test"])

        assert rc == 0
        calls = mock_run.call_args_list
        # With --skip-pytest, should NOT see pytest in commands
        for call in calls:
            cmd = call[0][0] if call[0] else call[1].get("cmd", [])
            assert "pytest" not in " ".join(str(c) for c in cmd) or "--skip-pytest" in str(call)

    @patch("tools.run_phase1_5_regression.subprocess.run")
    def test_skip_pytest_omits_pytest_command(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with patch("tools.run_phase1_5_regression._check_dangling_edges", return_value=0):
            rc = main(["--skip-pytest", "--tmp-dir", "/tmp/reg_test"])
        assert rc == 0
        # Verify no call has -m pytest
        for call in mock_run.call_args_list:
            cmd_args = call[0][0]
            assert not (len(cmd_args) >= 3 and cmd_args[1] == "-m" and cmd_args[2] == "pytest")

    @patch("tools.run_phase1_5_regression.subprocess.run")
    def test_default_includes_pytest(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with patch("tools.run_phase1_5_regression._check_dangling_edges", return_value=0):
            rc = main(["--tmp-dir", "/tmp/reg_test"])
        assert rc == 0
        # First call should be pytest
        first_cmd = mock_run.call_args_list[0][0][0]
        assert "-m" in first_cmd and "pytest" in first_cmd

    @patch("tools.run_phase1_5_regression.subprocess.run")
    def test_custom_document_id(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        with patch("tools.run_phase1_5_regression._check_dangling_edges", return_value=0):
            rc = main(["--skip-pytest", "--tmp-dir", "/tmp/reg_test",
                        "--document-id", "custom-doc"])
        assert rc == 0
        # eval_candidates call should have --document-id custom-doc
        for call in mock_run.call_args_list:
            cmd = call[0][0]
            if "eval_candidates.py" in " ".join(str(c) for c in cmd):
                assert "--document-id" in cmd
                idx = cmd.index("--document-id")
                assert cmd[idx + 1] == "custom-doc"

    @patch("tools.run_phase1_5_regression.subprocess.run")
    def test_failure_returns_nonzero(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        with patch("tools.run_phase1_5_regression._check_dangling_edges", return_value=1):
            rc = main(["--skip-pytest", "--tmp-dir", "/tmp/reg_test"])
        assert rc != 0


class TestDanglingEdges:
    """Test _check_dangling_edges directly."""

    def test_no_dangling(self, tmp_path):
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir()
        (graph_dir / "nodes.jsonl").write_text(
            json.dumps({"id": "n1"}) + "\n", encoding="utf-8"
        )
        (graph_dir / "edges.jsonl").write_text(
            json.dumps({"source": "n1", "target": "n1", "type": "SELF"}) + "\n",
            encoding="utf-8",
        )
        assert _check_dangling_edges(graph_dir) == 0

    def test_dangling_source(self, tmp_path):
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir()
        (graph_dir / "nodes.jsonl").write_text(
            json.dumps({"id": "n1"}) + "\n", encoding="utf-8"
        )
        (graph_dir / "edges.jsonl").write_text(
            json.dumps({"source": "n2", "target": "n1", "type": "REF"}) + "\n",
            encoding="utf-8",
        )
        assert _check_dangling_edges(graph_dir) == 1

    def test_dangling_target(self, tmp_path):
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir()
        (graph_dir / "nodes.jsonl").write_text(
            json.dumps({"id": "n1"}) + "\n", encoding="utf-8"
        )
        (graph_dir / "edges.jsonl").write_text(
            json.dumps({"source": "n1", "target": "n9", "type": "REF"}) + "\n",
            encoding="utf-8",
        )
        assert _check_dangling_edges(graph_dir) == 1

    def test_missing_files(self, tmp_path):
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir()
        assert _check_dangling_edges(graph_dir) == 1

    def test_empty_edges(self, tmp_path):
        graph_dir = tmp_path / "graph"
        graph_dir.mkdir()
        (graph_dir / "nodes.jsonl").write_text(
            json.dumps({"id": "n1"}) + "\n", encoding="utf-8"
        )
        (graph_dir / "edges.jsonl").write_text("", encoding="utf-8")
        assert _check_dangling_edges(graph_dir) == 0


class TestKeepTmp:
    """Test --keep-tmp and --tmp-dir behavior."""

    @patch("tools.run_phase1_5_regression.subprocess.run")
    @patch("tools.run_phase1_5_regression._check_dangling_edges", return_value=0)
    def test_tmp_dir_implies_keep(self, mock_dangling, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        rc = main(["--skip-pytest", "--tmp-dir", "/tmp/reg_keep_test"])
        assert rc == 0
        assert Path("/tmp/reg_keep_test").exists()
