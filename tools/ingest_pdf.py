#!/usr/bin/env python3
"""CLI tool for ingesting PDF files into the standards wiki."""

import sys
from pathlib import Path

from standards_wiki.ingest import ingest_pdf


def main():
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python tools/ingest_pdf.py <pdf_path>")
        print("Example: .venv/bin/python tools/ingest_pdf.py ./raw/standards/gb-7258-2017.pdf")
        sys.exit(1)

    pdf_path = Path(sys.argv[1])
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)

    print(f"Ingesting PDF: {pdf_path}")
    result = ingest_pdf(pdf_path)

    if result["status"] == "completed":
        print(f"Job ID: {result['job_id']}")
        print(f"Raw path: {result['raw_path']}")
        print(f"Source text: {result['source_text']}")
        print(f"Metadata: {result['metadata_path']}")
        print(f"Document: {result['document_path']}")
        if result.get("ocr_required"):
            print("WARNING: OCR may be required for this PDF (low text density detected)")
    else:
        print(f"Job failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
