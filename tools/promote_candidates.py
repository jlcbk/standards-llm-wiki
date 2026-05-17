#!/usr/bin/env python3
"""CLI tool for promoting reviewed provisions to final pages."""

import argparse
import sys

from standards_wiki.review import promote_reviewed


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Promote reviewed provisions to Markdown pages"
    )
    parser.add_argument("document_id")
    parser.add_argument("--candidates-dir", default="_candidates")
    parser.add_argument("--manifest-path", default=None)
    parser.add_argument("--output-dir", default="provisions")

    args = parser.parse_args(argv)

    result = promote_reviewed(
        args.document_id,
        candidates_dir=args.candidates_dir,
        manifest_path=args.manifest_path,
        output_dir=args.output_dir,
    )

    written = result["written"]
    missing = result["missing_reviewed_ids"]

    if written:
        print(f"Promoted {len(written)} provision(s) for {args.document_id}")
    else:
        print(f"No reviewed provisions to promote for {args.document_id}")

    if missing:
        print(
            f"WARNING: {len(missing)} reviewed ID(s) missing from candidates: "
            + ", ".join(missing),
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
