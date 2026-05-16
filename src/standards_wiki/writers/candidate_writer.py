"""Candidate writer — persist metadata YAML and candidate document Markdown."""

import yaml
from pathlib import Path

from ..utils import ensure_parent, utc_now_iso

_CANDIDATES_DIR = Path("_candidates")


def write_candidate_metadata(metadata: dict, slug: str) -> str:
    """Write candidate metadata as YAML to _candidates/metadata/{slug}.yaml.

    Args:
        metadata: Metadata dict to write.
        slug: Slug for the output filename.

    Returns:
        Path to the written YAML file.
    """
    target_dir = _CANDIDATES_DIR / "metadata"
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / f"{slug}.yaml"

    with open(output_path, "w", encoding="utf-8") as f:
        yaml.dump(metadata, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    return str(output_path)


def write_candidate_document(
    title: str,
    content: str,
    slug: str,
    metadata: dict | None = None,
) -> str:
    """Write candidate document Markdown to _candidates/documents/{slug}.md.

    Args:
        title: Document title.
        content: Document body content.
        slug: Slug for the output filename.
        metadata: Optional metadata to include in frontmatter.

    Returns:
        Path to the written Markdown file.
    """
    target_dir = _CANDIDATES_DIR / "documents"
    target_dir.mkdir(parents=True, exist_ok=True)

    output_path = target_dir / f"{slug}.md"

    with open(output_path, "w", encoding="utf-8") as f:
        # Write frontmatter
        f.write("---\n")
        f.write(f"title: {title}\n")
        f.write(f"created: {utc_now_iso()}\n")
        f.write(f"updated: {utc_now_iso()}\n")
        f.write("type: document\n")
        f.write("review_status: draft\n")
        f.write("confidence: low\n")

        if metadata:
            # Add additional metadata fields
            for key, value in metadata.items():
                if key not in ("title", "created", "updated", "type", "review_status", "confidence"):
                    if value is not None:
                        f.write(f"{key}: {value}\n")

        f.write("---\n\n")

        # Write body content
        f.write(content)

    return str(output_path)
