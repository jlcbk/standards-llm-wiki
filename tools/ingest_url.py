#!/usr/bin/env python3
"""CLI tool for ingesting webpages into the standards wiki."""

import sys
from pathlib import Path

from standards_wiki.ingest import ingest_url


def main():
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python tools/ingest_url.py <url>")
        print("Example: .venv/bin/python tools/ingest_url.py \"https://example.gov.cn/notice.html\"")
        sys.exit(1)

    url = sys.argv[1]

    print(f"Ingesting URL: {url}")
    result = ingest_url(url)

    if result["status"] == "completed":
        print(f"Job ID: {result['job_id']}")
        print(f"Raw path: {result['raw_path']}")
        print(f"Source text: {result['source_text']}")
        print(f"Metadata: {result['metadata_path']}")
        print(f"Document: {result['document_path']}")
        if result.get("attachments"):
            print(f"Attachments found: {len(result['attachments'])}")
            for att in result["attachments"]:
                print(f"  - {att}")
    else:
        print(f"Job failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
