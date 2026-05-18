"""Deterministic search over collected records.

Usage:
    .venv/bin/python tools/search.py <query> [--limit N] [--candidates-dir DIR] [--drafts-dir DIR] [--db-path PATH]
"""

import argparse
import sys

from standards_wiki.search import search, format_results


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Search documents, provisions, requirements")
    parser.add_argument("query", help="Search query string")
    parser.add_argument("--limit", type=int, default=20, help="Maximum results (default: 20)")
    parser.add_argument(
        "--candidates-dir", default="_candidates",
        help="Root candidates directory (default: _candidates)",
    )
    parser.add_argument(
        "--drafts-dir", default="documents/drafts",
        help="Draft documents directory (default: documents/drafts)",
    )
    parser.add_argument(
        "--db-path", default=None,
        help="Path to SQLite database; uses FTS5 backend instead of in-memory search",
    )
    args = parser.parse_args(argv)

    hits = search(
        query=args.query,
        candidates_dir=args.candidates_dir,
        drafts_dir=args.drafts_dir,
        limit=args.limit,
        db_path=args.db_path,
    )
    print(format_results(hits))


if __name__ == "__main__":
    main()
