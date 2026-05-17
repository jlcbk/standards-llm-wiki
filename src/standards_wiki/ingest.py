"""Ingestion pipeline orchestration for PDF and URL sources."""

from pathlib import Path
from typing import Literal

from .archive import archive_pdf, archive_html
from .classifier import classify_standard_type
from .extractors.html import extract_html as extract_html_content
from .extractors.pdf import extract_pdf as extract_pdf_content
from .jobs import create_job, update_job
from .metadata import extract_metadata
from .utils import slugify, utc_now_iso
from .writers.candidate_writer import write_candidate_document, write_candidate_metadata

IngestType = Literal["pdf", "url"]


def ingest_pdf(
    pdf_path: str | Path,
    job_id: str | None = None,
) -> dict:
    """Ingest a PDF file through the full pipeline.

    Pipeline:
        1. Archive raw PDF → raw/
        2. Extract text → sources/
        3. Extract metadata → candidates/metadata/
        4. Write candidate document → candidates/documents/
        5. Update job status

    Args:
        pdf_path: Path to the PDF file.
        job_id: Optional job ID (auto-generated if not provided).

    Returns:
        dict with job_id, status, and output paths.
    """
    pdf_path = Path(pdf_path)
    if job_id is None:
        job_id = f"pdf-{utc_now_iso().replace(':', '').replace('-', '').replace('T', '')[:12]}"

    # Create job
    job = create_job(job_id, "pdf", str(pdf_path))

    try:
        # Step 1: Archive raw PDF
        slug = slugify(pdf_path.stem)
        archive_result = archive_pdf(pdf_path, doc_type="standard", slug=slug)

        # Step 2: Extract PDF content
        extract_result = extract_pdf_content(pdf_path, slug=slug, sources_dir="standards")

        # Step 3: Extract metadata
        source_text_path = Path(extract_result["source_text"])
        source_text = source_text_path.read_text(encoding="utf-8")

        metadata = extract_metadata(
            source_text,
            source_path=archive_result["raw_path"],
            sha256=archive_result["sha256"],
        )
        metadata["document_id"] = slug
        metadata["source_text"] = extract_result["source_text"]
        metadata["ocr_required"] = extract_result["ocr_required"]

        # Step 4: Write candidate metadata
        metadata_path = write_candidate_metadata(metadata, slug)

        # Step 5: Write candidate document
        doc_content = f"<!-- Extracted from: {pdf_path.name} -->\n\n{source_text}"
        doc_path = write_candidate_document(
            title=metadata["title"],
            content=doc_content,
            slug=slug,
            metadata={"document_id": slug, "ocr_required": extract_result["ocr_required"]},
        )

        # Update job to completed
        update_job(job_id, "completed")

        return {
            "job_id": job_id,
            "status": "completed",
            "raw_path": archive_result["raw_path"],
            "source_text": extract_result["source_text"],
            "metadata_path": metadata_path,
            "document_path": doc_path,
            "ocr_required": extract_result["ocr_required"],
        }

    except Exception as e:
        update_job(job_id, "failed", error=str(e))
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }


def ingest_url(
    url: str,
    job_id: str | None = None,
) -> dict:
    """Ingest a webpage URL through the full pipeline.

    Pipeline:
        1. Fetch and archive raw HTML → raw/web/
        2. Extract content → sources/web/
        3. Extract metadata → candidates/metadata/
        4. Write candidate document → candidates/documents/
        5. Update job status

    Args:
        url: URL to fetch.
        job_id: Optional job ID (auto-generated if not provided).

    Returns:
        dict with job_id, status, and output paths.
    """
    if job_id is None:
        job_id = f"url-{utc_now_iso().replace(':', '').replace('-', '').replace('T', '')[:12]}"

    # Create job
    job = create_job(job_id, "url", url)

    try:
        # Step 1 & 2: Fetch and extract HTML content (archive_html is called inside extract_html)
        slug = slugify(url.split("/")[-1].replace(".html", "").replace(".htm", ""))
        if not slug:
            slug = f"webpage-{utc_now_iso()[:10]}"

        extract_result = extract_html_content(url, slug=slug, sources_dir="web")

        # Step 3: Extract metadata
        source_text_path = Path(extract_result["source_text"])
        source_text = source_text_path.read_text(encoding="utf-8")

        metadata = extract_metadata(
            source_text,
            source_path=extract_result["raw_path"],
            source_url=url,
            document_type="policy_notice",  # Web content defaults to policy_notice
        )
        metadata["document_id"] = slug

        # Step 4: Write candidate metadata
        metadata_path = write_candidate_metadata(metadata, slug)

        # Step 5: Write candidate document
        doc_content = f"<!-- Source URL: {url} -->\n\n{source_text}"
        doc_path = write_candidate_document(
            title=metadata["title"],
            content=doc_content,
            slug=slug,
            metadata={"document_id": slug, "source_url": url},
        )

        # Update job to completed
        update_job(job_id, "completed")

        return {
            "job_id": job_id,
            "status": "completed",
            "raw_path": extract_result["raw_path"],
            "source_text": extract_result["source_text"],
            "metadata_path": metadata_path,
            "document_path": doc_path,
            "attachments": extract_result.get("attachments", []),
        }

    except Exception as e:
        update_job(job_id, "failed", error=str(e))
        return {
            "job_id": job_id,
            "status": "failed",
            "error": str(e),
        }
