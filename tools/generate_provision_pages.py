#!/usr/bin/env python3
"""CLI tool for generating review-safe draft provision pages."""

import sys

from standards_wiki.compiler import generate_provision_pages


def main():
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python tools/generate_provision_pages.py <document_id> [--overwrite]")
        sys.exit(1)

    document_id = sys.argv[1]
    overwrite = "--overwrite" in sys.argv

    try:
        results = generate_provision_pages(document_id, overwrite=overwrite)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    generated = sum(1 for r in results if r["status"] == "generated")
    skipped = sum(1 for r in results if r["status"] == "skipped_exists")

    print(f"Document ID: {document_id}")
    print(f"Generated: {generated}")
    if skipped:
        print(f"Skipped (exist): {skipped}")
    for r in results:
        if r["status"] == "generated":
            print(f"  {r['provision_id']}: {r['output_path']}")


if __name__ == "__main__":
    main()
