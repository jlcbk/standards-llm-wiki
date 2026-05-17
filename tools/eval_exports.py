#!/usr/bin/env python3
"""CLI tool for evaluating exported SQLite and Graph JSONL against deterministic checks."""

import argparse
import json
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from standards_wiki.eval import load_checks, run_checks
from standards_wiki.sqlite_export import export_sqlite
from standards_wiki.graph_export import export_graph


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate exported SQLite/Graph against deterministic checks.",
    )
    parser.add_argument("checks_jsonl", nargs="+",
                        help="Path(s) to checks JSONL file")
    parser.add_argument("--candidates-dir", default="_candidates",
                        help="Root candidates directory (default: _candidates)")
    parser.add_argument("--sqlite-db", default=None,
                        help="SQLite output path (default: <tmp>/standards.db)")
    parser.add_argument("--graph-dir", default=None,
                        help="Graph output directory (default: <tmp>/graph/)")
    parser.add_argument("--skip-export", action="store_true",
                        help="Skip export, use existing db_path/graph_dir from checks")
    args = parser.parse_args(argv)

    candidates_dir = Path(args.candidates_dir)

    sqlite_db_path = args.sqlite_db
    graph_dir = args.graph_dir

    if not args.skip_export:
        import tempfile
        tmp = tempfile.mkdtemp(prefix="eval_exports_")

        if sqlite_db_path is None:
            sqlite_db_path = str(Path(tmp) / "standards.db")
        if graph_dir is None:
            graph_dir = str(Path(tmp) / "graph")

        export_sqlite(candidates_dir, sqlite_db_path)
        export_graph(candidates_dir, graph_dir)

    checks = []
    for checks_path in args.checks_jsonl:
        checks.extend(load_checks(checks_path))

    context = {
        "documents": [],
        "provisions": [],
        "requirements": [],
        "topic_tags": {},
        "sqlite_db_path": sqlite_db_path,
        "graph_dir": graph_dir,
    }

    result = run_checks(checks, context)

    print(f"total: {result['total']}  passed: {result['passed']}  failed: {result['failed']}")
    if result["failures"]:
        for f in result["failures"]:
            print(f"  FAIL [{f['id']}] {f['type']}: {f['reason']}")

    if result["failed"] > 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
