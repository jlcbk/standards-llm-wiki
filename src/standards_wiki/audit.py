"""Candidate quality audit — summarize extraction quality without legal conclusions."""

import json
import re
from pathlib import Path

from .candidates import read_jsonl

_DEFAULT_CANDIDATES_DIR = Path("_candidates")
_DEFAULT_REVIEWS_DIR = Path("_reviews") / "phase2-runs"

_SHORT_TEXT_THRESHOLD = 5
_WEAK_EVIDENCE_THRESHOLD = 3

# Patterns that suggest table-of-contents noise
_TOC_LABEL_PATTERNS = [
    re.compile(r"^目\s*录$"),
    re.compile(r"^Contents?$", re.IGNORECASE),
    re.compile(r"^(?:第[一二三四五六七八九十百千零\d]+[篇章节])"),
]

_TOC_TEXT_PATTERNS = [
    re.compile(r"^\s*[\d.]+\s+.+\s*\.{2,}\s*\d+\s*$", re.MULTILINE),
    re.compile(r"^\s*\.{3,}\s*$", re.MULTILINE),
]


def _is_toc_label(label: str) -> bool:
    return any(p.search(label) for p in _TOC_LABEL_PATTERNS)


def _has_toc_text(text: str) -> bool:
    return any(p.search(text) for p in _TOC_TEXT_PATTERNS)


def audit_candidates(
    document_id: str,
    candidates_dir: str | Path = _DEFAULT_CANDIDATES_DIR,
    review_dir: str | Path = _DEFAULT_REVIEWS_DIR,
) -> dict:
    """Run quality audit checks on candidate provisions and requirements.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory.
        review_dir: Output directory for audit reports.

    Returns:
        Audit report dict.
    """
    candidates_dir = Path(candidates_dir)
    review_dir = Path(review_dir)

    report: dict = {
        "document_id": document_id,
        "checks": {},
        "summary": {},
    }

    prov_path = candidates_dir / "provisions" / f"{document_id}.jsonl"
    req_path = candidates_dir / "requirements" / f"{document_id}.jsonl"

    provisions = read_jsonl(prov_path) if prov_path.exists() else []
    requirements = read_jsonl(req_path) if req_path.exists() else []

    # 1. Empty / short provision text
    short_provisions = []
    for p in provisions:
        text = p.get("text", "").strip()
        if len(text) < _SHORT_TEXT_THRESHOLD:
            short_provisions.append({
                "provision_id": p.get("provision_id", "unknown"),
                "label": p.get("label", ""),
                "text_length": len(text),
            })
    report["checks"]["short_provisions"] = short_provisions

    # 2. Fallback-only split
    has_fallback = any(
        p.get("label") == "fallback" for p in provisions
    )
    has_real = any(
        p.get("label") != "fallback" for p in provisions
    )
    report["checks"]["fallback_only_split"] = has_fallback and not has_real

    # 3. Duplicate provision labels
    label_counts: dict[str, int] = {}
    for p in provisions:
        label = p.get("label", "")
        if label and label != "fallback":
            label_counts[label] = label_counts.get(label, 0) + 1
    duplicates = {lbl: cnt for lbl, cnt in label_counts.items() if cnt > 1}
    report["checks"]["duplicate_labels"] = duplicates

    # 4. Table-of-contents-looking labels / text
    toc_provisions = []
    for p in provisions:
        label = p.get("label", "")
        text = p.get("text", "")
        if _is_toc_label(label) or _has_toc_text(text):
            toc_provisions.append({
                "provision_id": p.get("provision_id", "unknown"),
                "label": label,
                "reason": "toc_label" if _is_toc_label(label) else "toc_text",
            })
    report["checks"]["toc_noise"] = toc_provisions

    # 5. High requirement density
    density = len(requirements) / len(provisions) if provisions else 0.0
    report["checks"]["requirement_density"] = round(density, 2)
    report["checks"]["high_density_flag"] = density > 2.0

    # 6. Modality distribution
    modality_dist: dict[str, int] = {}
    for r in requirements:
        m = r.get("modality", "unknown")
        modality_dist[m] = modality_dist.get(m, 0) + 1
    report["checks"]["modality_distribution"] = dict(sorted(modality_dist.items()))

    # 7. Requirements with missing or weak evidence
    weak_evidence = []
    for r in requirements:
        evidence = r.get("evidence", {})
        quote = evidence.get("quote", "").strip() if evidence else ""
        if not quote or len(quote) < _WEAK_EVIDENCE_THRESHOLD:
            weak_evidence.append({
                "requirement_id": r.get("requirement_id", "unknown"),
                "issue": "missing" if not quote else "very_short",
            })
    report["checks"]["weak_evidence"] = weak_evidence

    # Summary
    total_issues = (
        len(short_provisions)
        + len(duplicates)
        + len(toc_provisions)
        + len(weak_evidence)
        + (1 if report["checks"]["fallback_only_split"] else 0)
    )
    report["summary"] = {
        "total_provisions": len(provisions),
        "total_requirements": len(requirements),
        "total_issues": total_issues,
    }

    # Write report
    review_dir.mkdir(parents=True, exist_ok=True)
    report_path = review_dir / f"{document_id}-audit.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    return report


def format_summary(report: dict) -> str:
    """Format audit report into a human-readable summary string."""
    lines = []
    doc_id = report["document_id"]
    lines.append(f"Audit: {doc_id}")
    lines.append("")

    summary = report.get("summary", {})
    lines.append(f"Provisions: {summary.get('total_provisions', 0)}")
    lines.append(f"Requirements: {summary.get('total_requirements', 0)}")

    checks = report.get("checks", {})

    if checks.get("fallback_only_split"):
        lines.append("  [ISSUE] Fallback-only split — no real labels detected")

    short = checks.get("short_provisions", [])
    if short:
        lines.append(f"  [ISSUE] {len(short)} short provisions (< {_SHORT_TEXT_THRESHOLD} chars)")
        for s in short[:5]:
            lines.append(f"    - {s['provision_id']} ({s['label']}): {s['text_length']} chars")

    dups = checks.get("duplicate_labels", {})
    if dups:
        lines.append(f"  [ISSUE] {len(dups)} duplicate labels")
        for lbl, cnt in list(dups.items())[:5]:
            lines.append(f"    - {lbl}: {cnt} occurrences")

    toc = checks.get("toc_noise", [])
    if toc:
        lines.append(f"  [ISSUE] {len(toc)} TOC-noise provisions")

    density = checks.get("requirement_density", 0)
    if checks.get("high_density_flag"):
        lines.append(f"  [ISSUE] High requirement density: {density}")

    modalities = checks.get("modality_distribution", {})
    if modalities:
        lines.append("  Modality distribution:")
        for m, cnt in modalities.items():
            lines.append(f"    {m}: {cnt}")

    weak = checks.get("weak_evidence", [])
    if weak:
        lines.append(f"  [ISSUE] {len(weak)} requirements with weak evidence")

    total = summary.get("total_issues", 0)
    lines.append("")
    if total == 0:
        lines.append("Result: clean")
    else:
        lines.append(f"Result: {total} issue(s) found")

    return "\n".join(lines)
