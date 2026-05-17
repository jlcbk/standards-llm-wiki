"""Graph JSONL export — produce node and edge files from candidate data."""

import json
from pathlib import Path

import yaml

from .candidates import read_jsonl


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _load_topic_tags(candidates_dir: Path) -> dict[str, dict]:
    tt_dir = candidates_dir / "topic-tags"
    if not tt_dir.exists():
        return {}

    result: dict[str, dict] = {}
    for tt_path in sorted(tt_dir.glob("*.json")):
        try:
            data = json.loads(tt_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for prov in data.get("provisions", []):
            pid = prov.get("id", "")
            if pid:
                result[pid] = {
                    "topics": prov.get("topics", []),
                    "entities": prov.get("entities", []),
                }
    return result


def _collect_nodes_provisions(
    candidates_dir: Path,
    nodes: dict[str, dict],
    edges: list[dict],
    topic_tags: dict[str, dict],
) -> int:
    prov_dir = candidates_dir / "provisions"
    if not prov_dir.exists():
        return 0

    # First pass: read all records and build (document_id, label) -> provision_id
    all_records: list[dict] = []
    label_map: dict[tuple[str, str], str] = {}

    for jsonl_path in sorted(prov_dir.glob("*.jsonl")):
        try:
            records = read_jsonl(jsonl_path)
        except Exception:
            continue
        for rec in records:
            pid = rec.get("provision_id", "")
            if not pid:
                continue
            all_records.append(rec)
            doc_id = rec.get("document_id", "")
            label = rec.get("label", "")
            if doc_id and label:
                label_map[(doc_id, label)] = pid

    # Second pass: create nodes and edges using the label_map for parent lookup
    count = 0
    for rec in all_records:
        pid = rec.get("provision_id", "")
        doc_id = rec.get("document_id", "")
        label = rec.get("label", "")

        nodes[pid] = {
            "id": pid,
            "type": "Provision",
            "props": {
                "document_id": doc_id,
                "label": label,
                "kind": rec.get("kind", ""),
                "title": rec.get("title", ""),
                "confidence": rec.get("confidence", ""),
                "review_status": rec.get("review_status", ""),
            },
        }

        if doc_id:
            edges.append({
                "source": doc_id,
                "target": pid,
                "type": "HAS_PROVISION",
                "props": {},
            })

        parent_id = _parent_provision_id(doc_id, label, label_map)
        if parent_id and parent_id in nodes:
            edges.append({
                "source": pid,
                "target": parent_id,
                "type": "SUBSECTION_OF",
                "props": {},
            })

        tt = topic_tags.get(pid, {})
        for topic in sorted(tt.get("topics", [])):
            topic_id = f"topic:{topic}"
            if topic_id not in nodes:
                nodes[topic_id] = {
                    "id": topic_id,
                    "type": "Topic",
                    "props": {"name": topic},
                }
            edges.append({
                "source": pid,
                "target": topic_id,
                "type": "ABOUT",
                "props": {},
            })

        for entity in sorted(tt.get("entities", [])):
            entity_id = f"entity:{entity}"
            if entity_id not in nodes:
                nodes[entity_id] = {
                    "id": entity_id,
                    "type": "Entity",
                    "props": {"name": entity},
                }
            edges.append({
                "source": pid,
                "target": entity_id,
                "type": "MENTIONS",
                "props": {},
            })

        count += 1

    return count


def _parent_provision_id(
    doc_id: str,
    label: str,
    label_map: dict[tuple[str, str], str],
) -> str | None:
    """Look up parent provision_id via the (document_id, label) mapping.

    Falls back to constructing an ID from the label if the parent label is
    not present in the mapping (e.g. the parent provision was not loaded).
    """
    if not label or not doc_id:
        return None

    parts = label.split(".")
    if len(parts) < 2:
        return None

    parent_label = ".".join(parts[:-1])
    return label_map.get((doc_id, parent_label))


def _collect_nodes_requirements(
    candidates_dir: Path,
    nodes: dict[str, dict],
    edges: list[dict],
) -> int:
    req_dir = candidates_dir / "requirements"
    if not req_dir.exists():
        return 0

    count = 0
    for jsonl_path in sorted(req_dir.glob("*.jsonl")):
        try:
            records = read_jsonl(jsonl_path)
        except Exception:
            continue

        for rec in records:
            rid = rec.get("requirement_id", "")
            if not rid:
                continue

            nodes[rid] = {
                "id": rid,
                "type": "Requirement",
                "props": {
                    "document_id": rec.get("document_id", ""),
                    "provision_id": rec.get("provision_id", ""),
                    "modality": rec.get("modality", ""),
                    "confidence": rec.get("confidence", ""),
                    "review_status": rec.get("review_status", ""),
                },
            }

            prov_id = rec.get("provision_id", "")
            if prov_id:
                edges.append({
                    "source": prov_id,
                    "target": rid,
                    "type": "HAS_REQUIREMENT",
                    "props": {},
                })

            count += 1

    return count


def _ensure_document_node(nodes: dict[str, dict], doc_id: str) -> None:
    """Create a minimal Document node if *doc_id* is not already present."""
    if doc_id not in nodes:
        nodes[doc_id] = {
            "id": doc_id,
            "type": "Document",
            "props": {
                "title": "",
                "document_type": "",
                "standard_id": "",
                "publisher": "",
                "confidence": "",
                "review_status": "",
            },
        }


def _collect_nodes_documents(
    candidates_dir: Path,
    nodes: dict[str, dict],
    edges: list[dict],
) -> int:
    meta_dir = candidates_dir / "metadata"
    if not meta_dir.exists():
        return 0

    count = 0
    for meta_path in sorted(meta_dir.glob("*.yaml")):
        doc_id = meta_path.stem
        meta = _load_yaml(meta_path)
        if not meta:
            continue

        nodes[doc_id] = {
            "id": doc_id,
            "type": "Document",
            "props": {
                "title": meta.get("title", ""),
                "document_type": meta.get("document_type", ""),
                "standard_id": meta.get("standard_id", ""),
                "publisher": meta.get("publisher", ""),
                "confidence": meta.get("confidence", ""),
                "review_status": meta.get("review_status", ""),
            },
        }

        replaced = meta.get("replaced", "")
        if replaced and isinstance(replaced, str) and replaced.strip():
            target_id = replaced.strip()
            edges.append({
                "source": doc_id,
                "target": target_id,
                "type": "REPLACED_BY",
                "props": {},
            })
            _ensure_document_node(nodes, target_id)

        replaces = meta.get("replaces", "")
        if replaces and isinstance(replaces, str) and replaces.strip():
            target_id = replaces.strip()
            edges.append({
                "source": doc_id,
                "target": target_id,
                "type": "REPLACES",
                "props": {},
            })
            _ensure_document_node(nodes, target_id)

        count += 1

    return count


def _deduplicate_edges(edges: list[dict]) -> list[dict]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict] = []
    for edge in edges:
        key = (edge["source"], edge["target"], edge["type"])
        if key not in seen:
            seen.add(key)
            unique.append(edge)
    return unique


def _sort_edges(edges: list[dict]) -> list[dict]:
    return sorted(edges, key=lambda e: (e["type"], e["source"], e["target"]))


def _sort_nodes(nodes: dict[str, dict]) -> list[dict]:
    return sorted(nodes.values(), key=lambda n: (n["type"], n["id"]))


def _write_jsonl(records: list[dict], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    return len(records)


def export_graph(candidates_dir: str | Path, out_dir: str | Path) -> dict:
    """Build graph JSONL (nodes + edges) from candidate data.

    Args:
        candidates_dir: Root candidates directory containing metadata/,
            provisions/, requirements/, and optionally topic-tags/ subdirs.
        out_dir: Output directory for nodes.jsonl and edges.jsonl.

    Returns:
        Dict with node/edge counts and resolved output paths.
    """
    candidates_dir = Path(candidates_dir)
    out_dir = Path(out_dir)

    topic_tags = _load_topic_tags(candidates_dir)

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    doc_count = _collect_nodes_documents(candidates_dir, nodes, edges)
    prov_count = _collect_nodes_provisions(
        candidates_dir, nodes, edges, topic_tags,
    )
    req_count = _collect_nodes_requirements(candidates_dir, nodes, edges)

    edges = _deduplicate_edges(edges)
    edges = [e for e in edges if e["source"] in nodes and e["target"] in nodes]
    edges = _sort_edges(edges)
    sorted_nodes = _sort_nodes(nodes)

    node_count = _write_jsonl(sorted_nodes, out_dir / "nodes.jsonl")
    edge_count = _write_jsonl(edges, out_dir / "edges.jsonl")

    return {
        "nodes": node_count,
        "edges": edge_count,
        "documents": doc_count,
        "provisions": prov_count,
        "requirements": req_count,
        "nodes_path": str(out_dir / "nodes.jsonl"),
        "edges_path": str(out_dir / "edges.jsonl"),
    }
