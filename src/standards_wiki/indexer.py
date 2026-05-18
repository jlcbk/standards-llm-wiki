"""Index data collector — gather deterministic records from candidates and drafts."""

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .candidates import read_jsonl

_CANDIDATES_DIR = Path("_candidates")
_DRAFTS_DIR = Path("documents/drafts")


@dataclass
class IndexResult:
    """Collection result with records and diagnostic warnings."""

    documents: list[dict] = field(default_factory=list)
    provisions: list[dict] = field(default_factory=list)
    requirements: list[dict] = field(default_factory=list)
    topic_tags: dict[tuple[str, str], dict] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _load_yaml(path: Path) -> dict:
    """Load YAML file, return empty dict on failure."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _parse_draft_frontmatter(path: Path) -> dict:
    """Extract frontmatter dict from a draft Markdown file."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    close = text.find("\n---", 3)
    if close == -1:
        return {}
    fm_text = text[3:close].strip()
    if not fm_text:
        return {}
    parsed = yaml.safe_load(fm_text)
    return parsed if isinstance(parsed, dict) else {}


def collect_records(
    candidates_dir: str | Path = _CANDIDATES_DIR,
    drafts_dir: str | Path = _DRAFTS_DIR,
) -> IndexResult:
    """Collect all document, provision, and requirement records.

    Scans:
      - documents/drafts/*.md for compiled document pages
      - _candidates/metadata/*.yaml for metadata
      - _candidates/provisions/*.jsonl for provision candidates
      - _candidates/requirements/*.jsonl for requirement candidates

    Args:
        candidates_dir: Root candidates directory.
        drafts_dir: Draft documents directory.

    Returns:
        IndexResult with collected records, warnings, and errors.
    """
    candidates_dir = Path(candidates_dir)
    drafts_dir = Path(drafts_dir)
    result = IndexResult()

    _collect_documents(candidates_dir, drafts_dir, result)
    _collect_provisions(candidates_dir, result)
    _collect_requirements(candidates_dir, result)
    _collect_topic_tags(candidates_dir, result)

    result.documents.sort(key=lambda d: d.get("document_id", ""))
    result.provisions.sort(key=lambda p: p.get("provision_id", ""))
    result.requirements.sort(key=lambda r: r.get("requirement_id", ""))

    return result


def _collect_documents(
    candidates_dir: Path, drafts_dir: Path, result: IndexResult
) -> None:
    """Collect document records from draft pages and metadata."""
    seen_ids: set[str] = set()
    doc_ids_from_metadata: set[str] = set()

    # Load metadata files
    meta_dir = candidates_dir / "metadata"
    if meta_dir.exists():
        for meta_path in sorted(meta_dir.glob("*.yaml")):
            doc_id = meta_path.stem
            meta = _load_yaml(meta_path)
            if not meta:
                result.warnings.append(f"Empty metadata: {meta_path}")
                continue
            doc_ids_from_metadata.add(doc_id)

            record = {
                "document_id": doc_id,
                "title": meta.get("title", "unknown"),
                "document_type": meta.get("document_type", "unknown"),
                "standard_id": meta.get("standard_id", "unknown"),
                "publisher": meta.get("publisher", "unknown"),
                "release_date": meta.get("release_date"),
                "effective_date": meta.get("effective_date"),
                "raw_path": meta.get("raw_path", "unknown"),
                "source_text": meta.get("source_text", "unknown"),
                "confidence": meta.get("confidence", "low"),
                "review_status": meta.get("review_status", "draft"),
                "source": str(meta_path),
            }
            result.documents.append(record)
            seen_ids.add(doc_id)

    # Load draft pages — they may carry additional frontmatter
    if drafts_dir.exists():
        for draft_path in sorted(drafts_dir.glob("*.md")):
            doc_id = draft_path.stem
            fm = _parse_draft_frontmatter(draft_path)

            existing = None
            for d in result.documents:
                if d.get("document_id") == doc_id:
                    existing = d
                    break

            if existing:
                # Merge frontmatter fields into existing record
                for key in ("review_status", "confidence", "generated_from"):
                    if key in fm and key not in existing:
                        existing[key] = fm[key]
                existing["draft_path"] = str(draft_path)
            elif fm:
                record = {
                    "document_id": doc_id,
                    "title": fm.get("title", "unknown"),
                    "document_type": fm.get("document_type", "unknown"),
                    "standard_id": fm.get("standard_id", "unknown"),
                    "source_text": fm.get("source_text", "unknown"),
                    "raw_path": fm.get("raw_path", "unknown"),
                    "confidence": fm.get("confidence", "low"),
                    "review_status": fm.get("review_status", "draft"),
                    "source": str(draft_path),
                    "draft_path": str(draft_path),
                }
                result.documents.append(record)
                seen_ids.add(doc_id)

    # Detect duplicate document IDs (shouldn't happen but check)
    id_counts: dict[str, int] = {}
    for d in result.documents:
        did = d.get("document_id", "")
        id_counts[did] = id_counts.get(did, 0) + 1
    for did, count in id_counts.items():
        if count > 1:
            result.errors.append(f"Duplicate document_id: {did} (count: {count})")


def _collect_provisions(candidates_dir: Path, result: IndexResult) -> None:
    """Collect provision records from JSONL files."""
    prov_dir = candidates_dir / "provisions"
    if not prov_dir.exists():
        return

    seen_ids: set[str] = set()
    for jsonl_path in sorted(prov_dir.glob("*.jsonl")):
        try:
            records = read_jsonl(jsonl_path)
        except Exception as e:
            result.errors.append(f"Failed to read {jsonl_path}: {e}")
            continue

        for rec in records:
            pid = rec.get("provision_id", "")
            if pid in seen_ids:
                result.errors.append(f"Duplicate provision_id: {pid}")
            seen_ids.add(pid)

            result.provisions.append({
                "provision_id": pid,
                "document_id": rec.get("document_id", "unknown"),
                "label": rec.get("label", "unknown"),
                "kind": rec.get("kind", "unknown"),
                "title": rec.get("title", "unknown"),
                "text": rec.get("text", ""),
                "confidence": rec.get("confidence", "low"),
                "review_status": rec.get("review_status", "machine_extracted"),
                "source": str(jsonl_path),
                "source_text": rec.get("source_text", "unknown"),
                "raw_path": rec.get("raw_path", "unknown"),
                "locator": rec.get("locator", {}),
            })


def _collect_requirements(candidates_dir: Path, result: IndexResult) -> None:
    """Collect requirement records from JSONL files."""
    req_dir = candidates_dir / "requirements"
    if not req_dir.exists():
        return

    seen_ids: set[str] = set()
    for jsonl_path in sorted(req_dir.glob("*.jsonl")):
        try:
            records = read_jsonl(jsonl_path)
        except Exception as e:
            result.errors.append(f"Failed to read {jsonl_path}: {e}")
            continue

        for rec in records:
            rid = rec.get("requirement_id", "")
            if rid in seen_ids:
                result.errors.append(f"Duplicate requirement_id: {rid}")
            seen_ids.add(rid)

            evidence = rec.get("evidence", {})
            result.requirements.append({
                "requirement_id": rid,
                "document_id": rec.get("document_id", "unknown"),
                "provision_id": rec.get("provision_id", "unknown"),
                "modality": rec.get("modality", "unknown"),
                "subject": rec.get("subject", "unknown"),
                "action": rec.get("action", "unknown"),
                "object": rec.get("object", "unknown"),
                "condition": rec.get("condition", "unknown"),
                "exception": rec.get("exception", "unknown"),
                "confidence": rec.get("confidence", "low"),
                "review_status": rec.get("review_status", "machine_extracted"),
                "source": str(jsonl_path),
                "evidence_quote": evidence.get("quote", ""),
                "source_text": evidence.get("source_text", "unknown"),
                "raw_path": evidence.get("raw_path", "unknown"),
            })


def _collect_topic_tags(candidates_dir: Path, result: IndexResult) -> None:
    """Collect topic/entity tags from _candidates/topic-tags/*.json."""
    tags_dir = candidates_dir / "topic-tags"
    if not tags_dir.exists():
        return

    for tags_path in sorted(tags_dir.glob("*.json")):
        try:
            data = json.loads(tags_path.read_text(encoding="utf-8"))
        except Exception as e:
            result.warnings.append(f"Failed to read {tags_path}: {e}")
            continue

        for entry in data.get("provisions", []):
            rid = entry.get("id", "")
            if rid:
                result.topic_tags[("provision", rid)] = {
                    "topics": entry.get("topics", []),
                    "entities": entry.get("entities", []),
                }

        for entry in data.get("requirements", []):
            rid = entry.get("id", "")
            if rid:
                result.topic_tags[("requirement", rid)] = {
                    "topics": entry.get("topics", []),
                    "entities": entry.get("entities", []),
                }


# --- Markdown index generation ---


def generate_documents_index(documents: list[dict]) -> str:
    """Generate Markdown index for documents."""
    lines = [
        "# Documents Index",
        "",
        "| Document ID | Title | Type | Standard ID | Confidence | Review Status | Source |",
        "|---|---|---|---|---|---|---|",
    ]
    for doc in documents:
        did = doc.get("document_id", "")
        title = doc.get("title", "unknown")
        dtype = doc.get("document_type", "unknown")
        sid = doc.get("standard_id", "unknown")
        conf = doc.get("confidence", "low")
        status = doc.get("review_status", "draft")
        source = doc.get("source", "")
        lines.append(f"| {did} | {title} | {dtype} | {sid} | {conf} | {status} | {source} |")
    lines.append("")
    return "\n".join(lines)


def generate_provisions_index(provisions: list[dict]) -> str:
    """Generate Markdown index for provisions."""
    lines = [
        "# Provisions Index",
        "",
        "| Provision ID | Document ID | Label | Kind | Confidence | Review Status | Source |",
        "|---|---|---|---|---|---|---|",
    ]
    for prov in provisions:
        pid = prov.get("provision_id", "")
        did = prov.get("document_id", "unknown")
        label = prov.get("label", "unknown")
        kind = prov.get("kind", "unknown")
        conf = prov.get("confidence", "low")
        status = prov.get("review_status", "machine_extracted")
        source = prov.get("source", "")
        lines.append(f"| {pid} | {did} | {label} | {kind} | {conf} | {status} | {source} |")
    lines.append("")
    return "\n".join(lines)


def generate_requirements_index(requirements: list[dict]) -> str:
    """Generate Markdown index for requirements."""
    lines = [
        "# Requirements Index",
        "",
        "| Requirement ID | Document ID | Provision ID | Modality | Confidence | Review Status | Source |",
        "|---|---|---|---|---|---|---|",
    ]
    for req in requirements:
        rid = req.get("requirement_id", "")
        did = req.get("document_id", "unknown")
        pid = req.get("provision_id", "unknown")
        mod = req.get("modality", "unknown")
        conf = req.get("confidence", "low")
        status = req.get("review_status", "machine_extracted")
        source = req.get("source", "")
        lines.append(f"| {rid} | {did} | {pid} | {mod} | {conf} | {status} | {source} |")
    lines.append("")
    return "\n".join(lines)


def generate_effective_dates_index(documents: list[dict]) -> str:
    """Generate Markdown index for effective dates."""
    lines = [
        "# Effective Dates Index",
        "",
        "| Document ID | Standard ID | Release Date | Effective Date | Review Status | Source |",
        "|---|---|---|---|---|---|",
    ]
    for doc in documents:
        did = doc.get("document_id", "")
        sid = doc.get("standard_id", "unknown")
        release = doc.get("release_date") or "—"
        effective = doc.get("effective_date") or "—"
        status = doc.get("review_status", "draft")
        source = doc.get("source", "")
        lines.append(f"| {did} | {sid} | {release} | {effective} | {status} | {source} |")
    lines.append("")
    return "\n".join(lines)


def generate_markdown_indexes(
    result: IndexResult,
    output_dir: str | Path,
) -> dict[str, str]:
    """Generate all Markdown index files.

    Args:
        result: IndexResult from collect_records.
        output_dir: Directory to write index files.

    Returns:
        Dict mapping index name to output file path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {}

    indexes = {
        "documents-index.md": generate_documents_index(result.documents),
        "provisions-index.md": generate_provisions_index(result.provisions),
        "requirements-index.md": generate_requirements_index(result.requirements),
        "effective-dates-index.md": generate_effective_dates_index(result.documents),
    }

    for filename, content in indexes.items():
        path = output_dir / filename
        path.write_text(content, encoding="utf-8")
        outputs[filename] = str(path)

    return outputs


# --- JSON export ---


def export_json(
    result: IndexResult,
    output_dir: str | Path,
) -> dict[str, str]:
    """Export deterministic JSON files.

    Args:
        result: IndexResult from collect_records.
        output_dir: Directory to write JSON files (typically db/json).

    Returns:
        Dict mapping filename to output file path.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    outputs = {}

    # Strip internal 'source' field for export — keep it in a dedicated field
    doc_records = _prepare_export_records(result.documents)
    prov_records = _prepare_export_records(result.provisions)
    req_records = _prepare_export_records(result.requirements)

    for filename, records in [
        ("documents.json", doc_records),
        ("provisions.json", prov_records),
        ("requirements.json", req_records),
    ]:
        path = output_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        outputs[filename] = str(path)

    # Manifest
    manifest = {
        "documents": len(doc_records),
        "provisions": len(prov_records),
        "requirements": len(req_records),
        "warnings": result.warnings,
        "errors": result.errors,
    }
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    outputs["manifest.json"] = str(manifest_path)

    return outputs


def _prepare_export_records(records: list[dict]) -> list[dict]:
    """Prepare records for JSON export — ensure deterministic key order."""
    return [dict(sorted(r.items())) for r in records]
