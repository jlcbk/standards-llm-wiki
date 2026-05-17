"""Export candidate data to graph JSONL (nodes + edges).

Usage:
    .venv/bin/python tools/export_graph.py [--candidates-dir DIR] [--out DIR]
"""

import argparse
import sys

from standards_wiki.graph_export import export_graph


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export graph JSONL from candidate data")
    parser.add_argument(
        "--candidates-dir", default="_candidates",
        help="Root candidates directory (default: _candidates)",
    )
    parser.add_argument(
        "--out", default="db/graph",
        help="Output directory (default: db/graph)",
    )
    args = parser.parse_args(argv)

    result = export_graph(args.candidates_dir, args.out)

    print(f"Nodes: {result['nodes']}")
    print(f"Edges: {result['edges']}")
    print(f"  Documents: {result['documents']}")
    print(f"  Provisions: {result['provisions']}")
    print(f"  Requirements: {result['requirements']}")


if __name__ == "__main__":
    main()
