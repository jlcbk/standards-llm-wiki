"""Build Markdown indexes from candidate data.

Usage:
    .venv/bin/python tools/build_indexes.py [--candidates-dir DIR] [--drafts-dir DIR] [--output-dir DIR]
"""

import argparse
import sys
from pathlib import Path

from standards_wiki.indexer import collect_records, generate_markdown_indexes


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Build Markdown indexes")
    parser.add_argument(
        "--candidates-dir", default="_candidates",
        help="Root candidates directory (default: _candidates)",
    )
    parser.add_argument(
        "--drafts-dir", default="documents/drafts",
        help="Draft documents directory (default: documents/drafts)",
    )
    parser.add_argument(
        "--output-dir", default="indexes",
        help="Output directory for index files (default: indexes)",
    )
    args = parser.parse_args(argv)

    result = collect_records(
        candidates_dir=args.candidates_dir,
        drafts_dir=args.drafts_dir,
    )

    outputs = generate_markdown_indexes(result, args.output_dir)

    print(f"Documents: {len(result.documents)}")
    print(f"Provisions: {len(result.provisions)}")
    print(f"Requirements: {len(result.requirements)}")
    for name, path in sorted(outputs.items()):
        print(f"  {name}: {path}")

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
