#!/usr/bin/env python3
"""CLI tool for creating review manifests and marking provisions as reviewed."""

import argparse
import sys

from standards_wiki.review import (
    create_review_manifest,
    load_review_manifest,
    mark_reviewed,
    save_review_manifest,
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Review candidate provisions"
    )
    sub = parser.add_subparsers(dest="command")

    manifest_p = sub.add_parser("manifest", help="Create review manifest")
    manifest_p.add_argument("document_id")
    manifest_p.add_argument("--candidates-dir", default="_candidates")

    mark_p = sub.add_parser("mark", help="Mark provisions as reviewed")
    mark_p.add_argument("manifest_path")
    mark_p.add_argument("provision_ids", nargs="+")

    args = parser.parse_args(argv)

    if args.command == "manifest":
        manifest = create_review_manifest(
            args.document_id, candidates_dir=args.candidates_dir
        )
        reviewed = sum(
            1 for e in manifest["provisions"] if e["review_status"] == "reviewed"
        )
        print(f"Document: {args.document_id}")
        print(f"Total provisions: {len(manifest['provisions'])}")
        print(f"Reviewed: {reviewed}")

    elif args.command == "mark":
        manifest = load_review_manifest(args.manifest_path)
        updated = mark_reviewed(manifest, set(args.provision_ids))
        save_review_manifest(updated, args.manifest_path)
        reviewed = sum(
            1 for e in updated["provisions"] if e["review_status"] == "reviewed"
        )
        print(f"Marked {len(args.provision_ids)} provision(s) as reviewed")
        print(f"Total reviewed: {reviewed}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
