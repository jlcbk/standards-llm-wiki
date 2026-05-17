"""Candidate IO — load metadata, candidate documents, and JSONL records."""

import json
from pathlib import Path

import yaml


def load_metadata(path: str | Path) -> dict:
    """Load candidate metadata from a YAML file.

    Args:
        path: Path to the YAML metadata file.

    Returns:
        Parsed metadata dict.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Metadata file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data if isinstance(data, dict) else {}


def load_candidate_document(path: str | Path) -> tuple[dict, str]:
    """Load a candidate Markdown document and split frontmatter from body.

    Args:
        path: Path to the candidate Markdown file.

    Returns:
        Tuple of (frontmatter_dict, body_text).
        If no frontmatter is present, returns ({}, full_text).

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Candidate document not found: {path}")

    text = path.read_text(encoding="utf-8")
    return split_frontmatter(text)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Split Markdown text into YAML frontmatter and body.

    Args:
        text: Full Markdown text, optionally starting with --- frontmatter.

    Returns:
        Tuple of (frontmatter_dict, body_text).
    """
    if not text.startswith("---"):
        return {}, text

    # Find the closing ---
    close_idx = text.find("\n---", 3)
    if close_idx == -1:
        return {}, text

    fm_text = text[3:close_idx].strip()
    body = text[close_idx + 4:].lstrip("\n")

    if not fm_text:
        return {}, body

    parsed = yaml.safe_load(fm_text)
    return parsed if isinstance(parsed, dict) else {}, body


def write_jsonl(records: list[dict], path: str | Path) -> str:
    """Write records to a JSONL file (one JSON object per line, UTF-8).

    Creates parent directories if they don't exist.

    Args:
        records: List of dicts to serialize.
        path: Output file path.

    Returns:
        String representation of the output path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    return str(path)


def read_jsonl(path: str | Path) -> list[dict]:
    """Read records from a JSONL file.

    Args:
        path: Path to the JSONL file.

    Returns:
        List of parsed dicts.

    Raises:
        FileNotFoundError: If the file does not exist.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"JSONL file not found: {path}")

    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records
