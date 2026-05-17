#!/usr/bin/env python3
"""CLI tool for evaluating candidates against deterministic checks."""

import argparse
import json
import sys
from pathlib import Path

import yaml

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from standards_wiki.eval import load_checks, run_checks


def _load_jsonl(path: Path) -> list[dict]:
    """Load records from a JSONL file, return empty list if missing."""
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def _load_json(path: Path) -> dict | list | None:
    """Load a JSON file, return None if missing."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_metadata(path: Path) -> dict | None:
    """Load metadata from a YAML file, return None if missing."""
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _metadata_to_document(meta: dict) -> dict:
    """Extract document fields from metadata dict."""
    return dict(meta)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Evaluate candidates against deterministic checks.",
    )
    parser.add_argument("checks_jsonl", nargs="+", help="Path(s) to checks JSONL file")
    parser.add_argument("--candidates-dir", default="_candidates",
                        help="Root candidates directory (default: _candidates)")
    parser.add_argument("--document-id", required=True,
                        help="Document identifier to evaluate")
    parser.add_argument("--run-id", default=None,
                        help="Run identifier for failure report filename")
    args = parser.parse_args(argv)

    candidates_dir = Path(args.candidates_dir)
    doc_id = args.document_id

    provisions_path = candidates_dir / "provisions" / f"{doc_id}.jsonl"
    requirements_path = candidates_dir / "requirements" / f"{doc_id}.jsonl"

    provisions = _load_jsonl(provisions_path)
    requirements = _load_jsonl(requirements_path)

    # Build documents list from real metadata file
    metadata_path = candidates_dir / "metadata" / f"{doc_id}.yaml"
    meta = _load_metadata(metadata_path)
    if meta:
        doc = _metadata_to_document(meta)
        # CLI --document-id is the canonical identifier; inject it so that
        # metadata_field_equals (and other checks) can match even when the
        # YAML only contains standard_id / title and no document_id.
        doc["document_id"] = doc_id
        documents = [doc]
    else:
        documents = []

    # Load topic-tags
    topic_tags_path = candidates_dir / "topic-tags" / f"{doc_id}.json"
    topic_tags = _load_json(topic_tags_path) or {}

    context = {
        "documents": documents,
        "provisions": provisions,
        "requirements": requirements,
        "topic_tags": topic_tags,
    }

    checks = []
    for checks_path in args.checks_jsonl:
        checks.extend(load_checks(checks_path))
    result = run_checks(checks, context)

    print(f"total: {result['total']}  passed: {result['passed']}  failed: {result['failed']}")
    if result["failures"]:
        for f in result["failures"]:
            print(f"  FAIL [{f['id']}] {f['type']}: {f['reason']}")

    if result["failed"] > 0:
        review_dir = Path("_reviews") / "eval-failures"
        review_dir.mkdir(parents=True, exist_ok=True)
        run_id = args.run_id or "unnamed"
        report_path = review_dir / f"{run_id}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"Failure report written to {report_path}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
