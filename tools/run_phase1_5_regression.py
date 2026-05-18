#!/usr/bin/env python3
"""Phase 1-5 regression runner — single entry point for full pipeline validation.

Usage:
    .venv/bin/python tools/run_phase1_5_regression.py
    .venv/bin/python tools/run_phase1_5_regression.py --skip-pytest
    .venv/bin/python tools/run_phase1_5_regression.py --keep-tmp --tmp-dir /tmp/regression
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _header(title: str) -> None:
    width = 60
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)


def _run(cmd: list[str], *, label: str, cwd: Path | None = None) -> int:
    print(f"\n[{label}] $ {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(cwd or _PROJECT_ROOT))
    if result.returncode != 0:
        print(f"FAILED [{label}] (exit {result.returncode})")
    else:
        print(f"PASSED [{label}]")
    return result.returncode


def _check_dangling_edges(graph_dir: Path) -> int:
    nodes_path = graph_dir / "nodes.jsonl"
    edges_path = graph_dir / "edges.jsonl"

    if not nodes_path.exists() or not edges_path.exists():
        print("FAILED [Graph integrity] missing nodes.jsonl or edges.jsonl")
        return 1

    node_ids: set[str] = set()
    with open(nodes_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                node_ids.add(json.loads(line)["id"])

    dangling = []
    with open(edges_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            edge = json.loads(line)
            if edge["source"] not in node_ids:
                dangling.append(f"source={edge['source']}")
            if edge["target"] not in node_ids:
                dangling.append(f"target={edge['target']}")

    if dangling:
        print(f"FAILED [Graph integrity] {len(dangling)} dangling edges:")
        for d in dangling[:10]:
            print(f"  {d}")
        return 1

    print(f"PASSED [Graph integrity] 0 dangling edges ({len(node_ids)} nodes)")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Phase 1-5 regression runner",
    )
    parser.add_argument("--skip-pytest", action="store_true",
                        help="Skip full pytest suite")
    parser.add_argument("--keep-tmp", action="store_true",
                        help="Keep temp directory and print its path")
    parser.add_argument("--tmp-dir", default=None,
                        help="Explicit temp directory (implies --keep-tmp)")
    parser.add_argument("--document-id", default="gb-7258-2017",
                        help="Document ID for eval (default: gb-7258-2017)")
    parser.add_argument("--candidates-dir", default="_candidates",
                        help="Candidates directory (default: _candidates)")
    args = parser.parse_args(argv)

    candidates_dir = _PROJECT_ROOT / args.candidates_dir
    venv_python = _PROJECT_ROOT / ".venv" / "bin" / "python"

    # ── Temp dir ──────────────────────────────────────────────────────────
    if args.tmp_dir:
        tmp_dir = Path(args.tmp_dir)
        tmp_dir.mkdir(parents=True, exist_ok=True)
        cleanup = False
    else:
        tmp_dir = Path(tempfile.mkdtemp(prefix="phase1_5_regression_"))
        cleanup = not args.keep_tmp

    sqlite_db = tmp_dir / "kb.sqlite"
    graph_dir = tmp_dir / "graph"

    failures: list[str] = []

    # ── Step 1: pytest ────────────────────────────────────────────────────
    if not args.skip_pytest:
        _header("Phase 1-5 pytest")
        rc = _run(
            [str(venv_python), "-m", "pytest", "-q"],
            label="pytest",
        )
        if rc != 0:
            failures.append("pytest")
    else:
        _header("Phase 1-5 pytest (SKIPPED)")

    # ── Step 2: Phase 3.5/4 candidate eval ────────────────────────────────
    _header("Phase 3.5/4 candidate eval")
    eval_checks = [
        "eval/qa/phase3_5_smoke.jsonl",
        "eval/qa/phase4_smoke.jsonl",
        f"eval/qa/{args.document_id}_factq.jsonl",
        f"eval/qa/{args.document_id}_dateq.jsonl",
        f"eval/qa/{args.document_id}_citationq.jsonl",
    ]
    # Only include files that exist
    eval_args: list[str] = []
    for p in eval_checks:
        full = _PROJECT_ROOT / p
        if full.exists():
            eval_args.append(p)
        else:
            print(f"  SKIP missing: {p}")

    if eval_args:
        rc = _run(
            [
                str(venv_python), "tools/eval_candidates.py",
                *eval_args,
                "--document-id", args.document_id,
                "--candidates-dir", str(candidates_dir),
            ],
            label="eval_candidates",
        )
        if rc != 0:
            failures.append("eval_candidates")
    else:
        print("  No eval check files found — skipping")

    # ── Step 3: Phase 5 export eval ───────────────────────────────────────
    _header("Phase 5 export eval")
    phase5_checks = _PROJECT_ROOT / "eval/qa/phase5_smoke.jsonl"
    if phase5_checks.exists():
        rc = _run(
            [
                str(venv_python), "tools/eval_exports.py",
                "eval/qa/phase5_smoke.jsonl",
                "--candidates-dir", str(candidates_dir),
                "--sqlite-db", str(sqlite_db),
                "--graph-dir", str(graph_dir),
            ],
            label="eval_exports",
        )
        if rc != 0:
            failures.append("eval_exports")
    else:
        print(f"  SKIP missing: eval/qa/phase5_smoke.jsonl")

    # ── Step 4: Graph dangling edges ──────────────────────────────────────
    _header("Graph integrity")
    if graph_dir.exists():
        rc = _check_dangling_edges(graph_dir)
        if rc != 0:
            failures.append("graph_integrity")
    else:
        print("  SKIP graph dir not produced (eval_exports may have been skipped)")

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    if failures:
        print(f"REGRESSION FAILED — {len(failures)} step(s): {', '.join(failures)}")
        code = 1
    else:
        print("ALL PASSED")
        code = 0

    if args.keep_tmp or args.tmp_dir:
        print(f"Temp directory: {tmp_dir}")
    elif cleanup:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return code


if __name__ == "__main__":
    sys.exit(main())
