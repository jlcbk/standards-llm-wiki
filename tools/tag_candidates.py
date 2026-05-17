#!/usr/bin/env python3
"""CLI tool for rule-based topic and entity tagging of candidate records."""

import argparse
import json
import sys
from pathlib import Path

from standards_wiki.tagging import tag_records


def _load_jsonl(path: Path) -> list[dict]:
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Tag candidate provisions and requirements with topics and entities.",
    )
    parser.add_argument("document_id", help="Document identifier")
    parser.add_argument(
        "--candidates-dir",
        default="_candidates",
        help="Root candidates directory (default: _candidates)",
    )
    args = parser.parse_args(argv)

    base = Path(args.candidates_dir)
    prov_path = base / "provisions" / f"{args.document_id}.jsonl"
    req_path = base / "requirements" / f"{args.document_id}.jsonl"

    if not prov_path.exists():
        print(f"Error: {prov_path} not found", file=sys.stderr)
        sys.exit(1)

    provisions = _load_jsonl(prov_path)
    tagged_provisions = tag_records(provisions)

    requirements: list[dict] = []
    if req_path.exists():
        requirements = _load_jsonl(req_path)
    tagged_requirements = tag_records(requirements)

    output = {
        "document_id": args.document_id,
        "provisions": tagged_provisions,
        "requirements": tagged_requirements,
    }

    out_dir = base / "topic-tags"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.document_id}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Tagged {len(tagged_provisions)} provisions, {len(tagged_requirements)} requirements -> {out_path}")


if __name__ == "__main__":
    main()
