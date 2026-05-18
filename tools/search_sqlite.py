"""Search the exported SQLite FTS5 database.

Usage:
    .venv/bin/python tools/search_sqlite.py <query> --db <path> --mode provisions --limit 5
"""

import argparse
import json
import sys

from standards_wiki.sqlite_search import search_sqlite


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Search SQLite FTS5 database"
    )
    parser.add_argument("query", help="Search query")
    parser.add_argument(
        "--db",
        default="db/kb.sqlite",
        help="Database path (default: db/kb.sqlite)",
    )
    parser.add_argument(
        "--mode",
        default="provisions",
        choices=["provisions", "documents", "requirements", "all"],
        help="Search mode (default: provisions)",
    )
    parser.add_argument(
        "--document-id", default=None, help="Filter by document ID"
    )
    parser.add_argument(
        "--limit", type=int, default=20, help="Max results (default: 20)"
    )
    parser.add_argument(
        "--review-status", default=None, help="Filter by review status"
    )
    parser.add_argument(
        "--topic", default=None, help="Filter by topic tag"
    )
    parser.add_argument(
        "--entity", default=None, help="Filter by entity tag"
    )

    args = parser.parse_args(argv)

    try:
        results = search_sqlite(
            args.db,
            args.query,
            mode=args.mode,
            document_id=args.document_id,
            limit=args.limit,
            review_status=args.review_status,
            topic=args.topic,
            entity=args.entity,
        )
    except FileNotFoundError as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
