"""Export candidate data to a SQLite database with FTS5.

Usage:
    .venv/bin/python tools/export_sqlite.py [--candidates-dir DIR] [--out PATH]
"""

import argparse
import sys

from standards_wiki.sqlite_export import export_sqlite


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export SQLite database with FTS5")
    parser.add_argument(
        "--candidates-dir", default="_candidates",
        help="Root candidates directory (default: _candidates)",
    )
    parser.add_argument(
        "--out", default="db/kb.sqlite",
        help="Output SQLite file path (default: db/kb.sqlite)",
    )
    args = parser.parse_args(argv)

    result = export_sqlite(args.candidates_dir, args.out)

    print(f"Documents: {result['documents']}")
    print(f"Provisions: {result['provisions']}")
    print(f"Requirements: {result['requirements']}")


if __name__ == "__main__":
    main()
