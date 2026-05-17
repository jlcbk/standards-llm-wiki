"""Real sample runner — execute the full Phase 2 pipeline for a document."""

import json
import time
from pathlib import Path

from .candidates import write_jsonl, read_jsonl
from .compiler import compile_document, generate_provision_pages
from .provisions import split_provisions_from_candidates
from .requirements import extract_requirements_from_jsonl
from .validate import validate_candidate_chain

_DEFAULT_CANDIDATES_DIR = Path("_candidates")
_DEFAULT_DRAFTS_DIR = Path("documents/drafts")
_DEFAULT_PROVISION_PAGES_DIR = Path("_candidates") / "provision-pages"
_DEFAULT_REVIEWS_DIR = Path("_reviews") / "phase2-runs"


def run_phase2(
    document_id: str,
    candidates_dir: str | Path = _DEFAULT_CANDIDATES_DIR,
    draft_dir: str | Path = _DEFAULT_DRAFTS_DIR,
    provision_pages_dir: str | Path = _DEFAULT_PROVISION_PAGES_DIR,
    review_dir: str | Path = _DEFAULT_REVIEWS_DIR,
    overwrite: bool = False,
) -> dict:
    """Run the full Phase 2 pipeline for a single document.

    Steps: compile → split provisions → extract requirements →
           generate provision pages → validate.

    Args:
        document_id: Document identifier.
        candidates_dir: Root candidates directory.
        draft_dir: Output directory for compiled draft pages.
        provision_pages_dir: Output directory for provision pages.
        review_dir: Output directory for review reports.
        overwrite: Whether to overwrite existing outputs.

    Returns:
        Report dict with status, outputs, counts, warnings, errors.
    """
    candidates_dir = Path(candidates_dir)
    draft_dir = Path(draft_dir)
    provision_pages_dir = Path(provision_pages_dir)
    review_dir = Path(review_dir)

    report: dict = {
        "document_id": document_id,
        "status": "ok",
        "outputs": {},
        "counts": {
            "provisions": 0,
            "requirements": 0,
            "validation_errors": 0,
            "validation_warnings": 0,
        },
        "warnings": [],
        "errors": [],
    }

    try:
        # Step 1: compile document
        compile_result = compile_document(
            document_id,
            candidates_dir=candidates_dir,
            output_dir=draft_dir,
            overwrite=overwrite,
        )
        report["outputs"]["draft_document"] = compile_result["output_path"]

        # Step 2: split provisions
        provisions = split_provisions_from_candidates(
            document_id, candidates_dir=candidates_dir,
        )
        prov_path = candidates_dir / "provisions" / f"{document_id}.jsonl"
        write_jsonl(provisions, prov_path)
        report["outputs"]["provisions_jsonl"] = str(prov_path)
        report["counts"]["provisions"] = len(provisions)

        # Step 3: extract requirements
        requirements = extract_requirements_from_jsonl(
            document_id, candidates_dir=candidates_dir,
        )
        req_path = candidates_dir / "requirements" / f"{document_id}.jsonl"
        write_jsonl(requirements, req_path)
        report["outputs"]["requirements_jsonl"] = str(req_path)
        report["counts"]["requirements"] = len(requirements)

        # Step 4: generate provision pages
        page_results = generate_provision_pages(
            document_id,
            candidates_dir=candidates_dir,
            output_dir=provision_pages_dir,
            overwrite=overwrite,
        )
        report["outputs"]["provision_pages_dir"] = str(provision_pages_dir / document_id)

        # Step 5: validate
        validation_errors = validate_candidate_chain(
            document_id, candidates_dir=candidates_dir,
        )
        for ve in validation_errors:
            if ve.level == "error":
                report["counts"]["validation_errors"] += 1
                report["errors"].append(str(ve))
            else:
                report["counts"]["validation_warnings"] += 1
                report["warnings"].append(str(ve))

        if report["counts"]["validation_errors"] > 0:
            report["status"] = "failed"

    except Exception as exc:
        report["status"] = "failed"
        report["errors"].append(str(exc))

    # Write review report
    review_dir.mkdir(parents=True, exist_ok=True)
    report_path = review_dir / f"{document_id}.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    return report
