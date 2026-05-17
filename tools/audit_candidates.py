#!/usr/bin/env python3
"""CLI tool for auditing candidate quality."""

import argparse
import sys

from standards_wiki.audit import audit_candidates, format_summary


def main():
    parser = argparse.ArgumentParser(
        description="Audit candidate quality for a document.",
    )
    parser.add_argument("document_id", help="Document identifier")
    parser.add_argument("--candidates-dir", default="_candidates")
    parser.add_argument("--review-dir", default="_reviews/phase2-runs")
    args = parser.parse_args()

    report = audit_candidates(
        document_id=args.document_id,
        candidates_dir=args.candidates_dir,
        review_dir=args.review_dir,
    )

    print(format_summary(report))

    total = report.get("summary", {}).get("total_issues", 0)
    sys.exit(1 if total > 0 else 0)


if __name__ == "__main__":
    main()
