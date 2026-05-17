#!/usr/bin/env python3
"""CLI tool for running the Phase 2 pipeline on a single document."""

import argparse
import json
import sys

from standards_wiki.real_run import run_phase2


def main():
    parser = argparse.ArgumentParser(
        description="Run Phase 2 pipeline for a document.",
    )
    parser.add_argument("document_id", help="Document identifier")
    parser.add_argument("--candidates-dir", default="_candidates")
    parser.add_argument("--draft-dir", default="documents/drafts")
    parser.add_argument("--provision-pages-dir", default="_candidates/provision-pages")
    parser.add_argument("--review-dir", default="_reviews/phase2-runs")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    report = run_phase2(
        document_id=args.document_id,
        candidates_dir=args.candidates_dir,
        draft_dir=args.draft_dir,
        provision_pages_dir=args.provision_pages_dir,
        review_dir=args.review_dir,
        overwrite=args.overwrite,
    )

    print(f"Document ID: {report['document_id']}")
    print(f"Status: {report['status']}")
    for key, path in report["outputs"].items():
        print(f"  {key}: {path}")
    counts = report["counts"]
    print(f"Provisions: {counts['provisions']}")
    print(f"Requirements: {counts['requirements']}")
    print(f"Validation errors: {counts['validation_errors']}")
    print(f"Validation warnings: {counts['validation_warnings']}")

    if report["warnings"]:
        print("\nWarnings:")
        for w in report["warnings"]:
            print(f"  {w}")
    if report["errors"]:
        print("\nErrors:")
        for e in report["errors"]:
            print(f"  {e}")

    sys.exit(1 if report["status"] == "failed" else 0)


if __name__ == "__main__":
    main()
