"""Document compiler — assemble draft wiki pages from candidate metadata and documents."""

import sys
from pathlib import Path

import yaml

from .candidates import load_metadata, load_candidate_document, read_jsonl

_CANDIDATES_DIR = Path("_candidates")
_DRAFTS_DIR = Path("documents/drafts")
_PROVISION_PAGES_DIR = Path("_candidates") / "provision-pages"


def compile_document(
    document_id: str,
    candidates_dir: str | Path = _CANDIDATES_DIR,
    output_dir: str | Path = _DRAFTS_DIR,
    overwrite: bool = False,
) -> dict:
    """Compile a draft wiki document page from candidate metadata and markdown.

    Args:
        document_id: Document identifier (e.g. gb-7258-2017).
        candidates_dir: Root candidates directory.
        output_dir: Output directory for compiled pages.
        overwrite: Whether to overwrite an existing page.

    Returns:
        dict with output_path, document_id, and metadata fields.

    Raises:
        FileNotFoundError: If candidate metadata or document is missing.
        FileExistsError: If output page exists and overwrite is False.
    """
    candidates_dir = Path(candidates_dir)
    output_dir = Path(output_dir)

    meta_path = candidates_dir / "metadata" / f"{document_id}.yaml"
    doc_path = candidates_dir / "documents" / f"{document_id}.md"

    metadata = load_metadata(meta_path)
    _frontmatter, body = load_candidate_document(doc_path)

    out_path = output_dir / f"{document_id}.md"

    if out_path.exists() and not overwrite:
        raise FileExistsError(
            f"Compiled page already exists: {out_path}. Use overwrite=True to replace."
        )

    page_fm = _build_frontmatter(document_id, metadata)
    page_content = _render_page(page_fm, body)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page_content, encoding="utf-8")

    return {
        "output_path": str(out_path),
        "document_id": document_id,
        "title": metadata.get("title", "unknown"),
        "review_status": "draft",
        "generated_from": "candidate",
    }


def _build_frontmatter(document_id: str, metadata: dict) -> dict:
    """Build normalized frontmatter for compiled page."""
    return {
        "document_id": document_id,
        "title": metadata.get("title", "unknown"),
        "document_type": metadata.get("document_type", "unknown"),
        "standard_id": metadata.get("standard_id", "unknown"),
        "source_text": metadata.get("source_text", "unknown"),
        "raw_path": metadata.get("raw_path", "unknown"),
        "review_status": "draft",
        "confidence": metadata.get("confidence", "low"),
        "generated_from": "candidate",
    }


def _render_page(frontmatter: dict, body: str) -> str:
    """Render frontmatter and body into a single Markdown string."""
    fm_yaml = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
    return f"---\n{fm_yaml}---\n\n{body}"


def main():
    """CLI entry point for compile_document."""
    if len(sys.argv) < 2:
        print("Usage: .venv/bin/python tools/compile_document.py <document_id> [--overwrite]")
        sys.exit(1)

    document_id = sys.argv[1]
    overwrite = "--overwrite" in sys.argv

    try:
        result = compile_document(document_id, overwrite=overwrite)
        print(f"Document ID: {result['document_id']}")
        print(f"Title: {result['title']}")
        print(f"Output: {result['output_path']}")
        print(f"Review status: {result['review_status']}")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except FileExistsError as e:
        print(f"Error: {e}")
        sys.exit(1)


def generate_provision_pages(
    document_id: str,
    candidates_dir: str | Path = _CANDIDATES_DIR,
    output_dir: str | Path = _PROVISION_PAGES_DIR,
    overwrite: bool = False,
) -> list[dict]:
    """Generate review-safe draft provision pages.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory.
        output_dir: Output directory for provision pages.
        overwrite: Whether to overwrite existing pages.

    Returns:
        List of dicts with output_path for each generated page.

    Raises:
        FileNotFoundError: If provisions JSONL is missing.
    """
    candidates_dir = Path(candidates_dir)
    output_dir = Path(output_dir)

    prov_path = candidates_dir / "provisions" / f"{document_id}.jsonl"
    if not prov_path.exists():
        raise FileNotFoundError(f"Provisions file not found: {prov_path}")

    provisions = read_jsonl(prov_path)

    # Try to load requirements
    req_path = candidates_dir / "requirements" / f"{document_id}.jsonl"
    requirements_by_provision = {}
    if req_path.exists():
        for req in read_jsonl(req_path):
            pid = req.get("provision_id", "")
            requirements_by_provision.setdefault(pid, []).append(req)

    results = []
    doc_output_dir = output_dir / document_id

    for provision in provisions:
        provision_id = provision.get("provision_id", "unknown")
        out_path = doc_output_dir / f"{provision_id}.md"

        if out_path.exists() and not overwrite:
            results.append({
                "output_path": str(out_path),
                "provision_id": provision_id,
                "status": "skipped_exists",
            })
            continue

        page = _render_provision_page(
            provision,
            requirements_by_provision.get(provision_id, []),
        )

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(page, encoding="utf-8")

        results.append({
            "output_path": str(out_path),
            "provision_id": provision_id,
            "status": "generated",
        })

    return results


def _render_provision_page(provision: dict, requirements: list[dict]) -> str:
    """Render a single provision page with optional requirements."""
    fm = {
        "provision_id": provision.get("provision_id", "unknown"),
        "document_id": provision.get("document_id", "unknown"),
        "label": provision.get("label", "unknown"),
        "kind": provision.get("kind", "unknown"),
        "review_status": "machine_extracted",
        "confidence": provision.get("confidence", "low"),
        "source_text": provision.get("source_text", "unknown"),
        "raw_path": provision.get("raw_path", "unknown"),
        "locator": provision.get("locator", {}),
    }

    lines = []
    lines.append("<!-- WARNING: Machine-extracted candidate — not reviewed -->")
    fm_yaml = yaml.dump(fm, default_flow_style=False, allow_unicode=True, sort_keys=False)
    lines.append(f"---\n{fm_yaml}---\n")

    title = provision.get("title", "unknown")
    label = provision.get("label", "")
    lines.append(f"## {label} {title}\n")

    # Source text
    text = provision.get("text", "")
    lines.append("### 原文\n")
    lines.append(f"> {provision.get('evidence', {}).get('quote', text)}\n")

    # Requirements section
    if requirements:
        lines.append("### 结构化要求\n")
        for req in requirements:
            req_yaml = yaml.dump(
                {
                    "requirement_id": req.get("requirement_id", "unknown"),
                    "modality": req.get("modality", "unknown"),
                    "subject": req.get("subject", "unknown"),
                    "action": req.get("action", "unknown"),
                    "object": req.get("object", "unknown"),
                    "condition": req.get("condition", "unknown"),
                    "exception": req.get("exception", "unknown"),
                    "evidence": req.get("evidence", {}),
                },
                default_flow_style=False,
                allow_unicode=True,
                sort_keys=False,
            )
            lines.append(f"```yaml\n{req_yaml}```\n")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
