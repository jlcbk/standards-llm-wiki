"""Export candidate data to SQLite with FTS5 full-text search.

Usage:
    .venv/bin/python tools/export_sqlite.py [--candidates-dir DIR] [--drafts-dir DIR] [--out PATH]
"""

import argparse
import sys
from pathlib import Path

from standards_wiki.indexer import collect_records
from standards_wiki.sqlite_export import export_sqlite


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Export to SQLite with FTS5")
    parser.add_argument(
        "--candidates-dir", default="_candidates",
        help="Root candidates directory (default: _candidates)",
    )
    parser.add_argument(
        "--drafts-dir", default="documents/drafts",
        help="Draft documents directory (default: documents/drafts)",
    )
    parser.add_argument(
        "--out", default="db/kb.sqlite",
        help="Output SQLite path (default: db/kb.sqlite)",
    )
    args = parser.parse_args(argv)

    result = collect_records(
        candidates_dir=args.candidates_dir,
        drafts_dir=args.drafts_dir,
    )

    stats = export_sqlite(result, args.out)

    print(f"Documents: {stats['documents']}")
    print(f"Provisions: {stats['provisions']}")
    print(f"Requirements: {stats['requirements']}")
    print(f"Topic tags: {stats['topic_tags']}")
    print(f"Output: {stats['path']}")

    if result.warnings:
        print(f"\nWarnings ({len(result.warnings)}):")
        for w in result.warnings:
            print(f"  {w}")

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for e in result.errors:
            print(f"  {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
