"""Review and promotion workflow for candidate provisions."""

import json
from pathlib import Path

import yaml

from .candidates import read_jsonl

_DEFAULT_CANDIDATES_DIR = Path("_candidates")

_MAX_SHORT_QUOTE_LEN = 120


def _extract_short_quote(provision: dict, max_len: int = _MAX_SHORT_QUOTE_LEN) -> str:
    quote = provision.get("evidence", {}).get("quote") or provision.get("text", "")
    if len(quote) > max_len:
        return quote[:max_len] + "..."
    return quote


def create_review_manifest(
    document_id: str,
    candidates_dir: str | Path = _DEFAULT_CANDIDATES_DIR,
    output_dir: str | Path | None = None,
) -> dict:
    """Create a review manifest from candidate provisions.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory containing provisions JSONL.
        output_dir: Directory to write the manifest JSON. Defaults to
            candidates_dir / "review-manifests".

    Returns:
        Manifest dict with provisions list. Each entry includes provision_id,
        review_status, label, title, locator, confidence, and short_quote.
    """
    candidates_dir = Path(candidates_dir)
    prov_path = candidates_dir / "provisions" / f"{document_id}.jsonl"

    provisions = read_jsonl(prov_path) if prov_path.exists() else []

    manifest = {
        "document_id": document_id,
        "provisions": [
            {
                "provision_id": p["provision_id"],
                "review_status": "pending",
                "label": p.get("label", ""),
                "title": p.get("title", ""),
                "locator": p.get("locator", {}),
                "confidence": p.get("confidence", "medium"),
                "short_quote": _extract_short_quote(p),
            }
            for p in provisions
        ],
    }

    if output_dir is None:
        output_dir = candidates_dir / "review-manifests"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / f"{document_id}-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return manifest


def load_review_manifest(path: str | Path) -> dict:
    """Load a review manifest from disk.

    Args:
        path: Path to the manifest JSON file.

    Returns:
        Manifest dict.
    """
    path = Path(path)
    return json.loads(path.read_text(encoding="utf-8"))


def mark_reviewed(manifest: dict, provision_ids: set[str]) -> dict:
    """Mark selected provision IDs as reviewed in a manifest.

    Args:
        manifest: Manifest dict with "provisions" list.
        provision_ids: Set of provision IDs to mark as reviewed.

    Returns:
        Updated manifest dict (new object, input not mutated).
    """
    updated_provisions = []
    for entry in manifest["provisions"]:
        new_entry = dict(entry)
        new_entry["review_status"] = (
            "reviewed" if entry["provision_id"] in provision_ids
            else entry["review_status"]
        )
        updated_provisions.append(new_entry)

    return {
        "document_id": manifest["document_id"],
        "provisions": updated_provisions,
    }


def save_review_manifest(manifest: dict, path: str | Path) -> Path:
    """Write a review manifest to disk.

    Args:
        manifest: Manifest dict.
        path: Output file path.

    Returns:
        Path to the written file.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def build_provision_page(provision: dict) -> str:
    """Build a Markdown page for a promoted provision.

    Args:
        provision: Provision record dict.

    Returns:
        Markdown string with YAML frontmatter and body.
    """
    frontmatter = {
        "provision_id": provision["provision_id"],
        "document_id": provision["document_id"],
        "label": provision["label"],
        "kind": provision["kind"],
        "review_status": "reviewed",
        "confidence": provision.get("confidence", "medium"),
        "source_text": provision.get("source_text", "unknown"),
        "raw_path": provision.get("raw_path", "unknown"),
        "locator": provision.get("locator", {}),
    }

    fm_str = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False).strip()
    title = provision.get("title", "unknown")
    label = provision["label"]
    quote = provision.get("evidence", {}).get("quote", provision.get("text", ""))

    body = f"## {label} {title}\n\n### 原文\n\n> {quote}\n"

    return f"---\n{fm_str}\n---\n\n{body}"


def promote_reviewed(
    document_id: str,
    candidates_dir: str | Path = _DEFAULT_CANDIDATES_DIR,
    manifest_path: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> dict:
    """Promote reviewed provisions to individual Markdown pages.

    Only provisions whose manifest entry has review_status "reviewed" are
    promoted. Unreviewed candidates are always skipped.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory.
        manifest_path: Path to the review manifest JSON. Defaults to
            candidates_dir / "review-manifests" / "{document_id}-manifest.json".
        output_dir: Base directory for promoted pages. Defaults to
            "provisions".

    Returns:
        Dict with "written" (list of file paths) and "missing_reviewed_ids"
        (list of reviewed IDs not found in candidates JSONL).
    """
    candidates_dir = Path(candidates_dir)

    if manifest_path is None:
        manifest_path = candidates_dir / "review-manifests" / f"{document_id}-manifest.json"
    manifest = load_review_manifest(manifest_path)

    reviewed_ids = {
        e["provision_id"]
        for e in manifest["provisions"]
        if e["review_status"] == "reviewed"
    }

    if not reviewed_ids:
        return {"written": [], "missing_reviewed_ids": []}

    prov_path = candidates_dir / "provisions" / f"{document_id}.jsonl"
    provisions = read_jsonl(prov_path)

    prov_by_id = {p["provision_id"]: p for p in provisions}

    missing_reviewed_ids = sorted(
        pid for pid in reviewed_ids if pid not in prov_by_id
    )

    if output_dir is None:
        output_dir = Path("provisions")
    output_dir = Path(output_dir)
    doc_dir = output_dir / document_id
    doc_dir.mkdir(parents=True, exist_ok=True)

    written = []
    for pid in sorted(reviewed_ids):
        provision = prov_by_id.get(pid)
        if provision is None:
            continue

        page = build_provision_page(provision)
        page_path = doc_dir / f"{pid}.md"
        page_path.write_text(page, encoding="utf-8")
        written.append(str(page_path))

    return {"written": written, "missing_reviewed_ids": missing_reviewed_ids}
