"""PDF extractor — high-quality text extraction from PDFs with OCR detection."""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pymupdf
import pymupdf4llm

from ..utils import ensure_parent

SourcesDir = Literal["standards", "regulations", "policies", "rules", "interpretations", "web"]
PdfEngine = Literal["auto", "pymupdf4llm", "marker"]

_MIN_TEXT_PAGES = 3
_MIN_CHAR_PER_PAGE = 50
_MIN_CHARS_FALLBACK = 500  # Switch to marker-pdf if pymupdf4llm yields less than this
_MARKER_MIN_PAGES = 10
_MARKER_TIMEOUT_SECONDS = 3600

_DEFAULT_SOURCES_DIR = Path("sources")


def _resolve_marker_single() -> str | None:
    """Return the marker_single executable path if available."""
    venv_candidate = Path(sys.executable).with_name("marker_single")
    if venv_candidate.exists():
        return str(venv_candidate)
    return shutil.which("marker_single")


def _extract_with_marker(
    pdf_path: Path,
    slug: str,
    target_dir: Path,
    use_ocr: bool,
) -> tuple[str, list[str]] | None:
    """Extract Markdown using marker-pdf CLI.

    The CLI path is used because marker-pdf 1.x changed its Python API, while
    `marker_single` remained stable in the lab project experiments.
    """
    marker_bin = _resolve_marker_single()
    if marker_bin is None:
        return None

    timeout = int(os.environ.get("STANDARDS_WIKI_MARKER_TIMEOUT", _MARKER_TIMEOUT_SECONDS))

    try:
        with tempfile.TemporaryDirectory(prefix="standards-wiki-marker-") as tmp:
            command = [
                marker_bin,
                str(pdf_path),
                "--output_dir",
                tmp,
                "--output_format",
                "markdown",
                "--disable_tqdm",
            ]
            if not use_ocr:
                command.append("--disable_ocr")

            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            md_files = sorted(Path(tmp).rglob("*.md"), key=lambda p: p.stat().st_size, reverse=True)
            if not md_files:
                return None

            marker_md = md_files[0]
            text = marker_md.read_text(encoding="utf-8")
            if len(text.strip()) <= 100:
                return None

            text, assets = _rewrite_marker_asset_links(text, marker_md.parent, target_dir, slug)
            return text, assets

    except Exception:
        return None


def _extract_with_pymupdf(pdf_path: Path) -> str:
    """Extract Markdown using pymupdf4llm (fast, best for text-based PDFs)."""
    return pymupdf4llm.to_markdown(pdf_path)


# Characters safe to unwrap from bracket artifacts like [—] [年版的] [)]
# Only CJK chars, CJK/fullwidth punctuation, and specific ASCII punctuation
# used in Chinese documents. Excludes digits, Latin letters, spaces to avoid
# touching real references like [1], [GB 7258], [Note].
_UNWRAP_SAFE = re.compile(
    r"^[一-鿿　-〿＀-￯—‘’“”,./\-、，。：；！？;:)+]+$"
)

# Image markers from marker-pdf: **==> picture [...] intentionally omitted <==**
_RE_PICTURE = re.compile(r"\*\*==>\s*picture.*?<==\*\*\n?")

# Concatenated English: split at lowercase->uppercase boundaries
_RE_CONCAT = re.compile(r"([a-z])([A-Z])")

# Stray <br> tags in markdown
_RE_BR = re.compile(r"<br\s*/?>")

# Isolated roman numeral headers (page numbers in headers/footers)
_RE_ROMAN = re.compile(r"^\s*[IVXⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+\s*$", re.MULTILINE)
_RE_MARKDOWN_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_RE_CJK_SPACED = re.compile(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])")
_RE_STANDARD_HEADER = re.compile(
    r"^#{0,6}\s*(?:GB\s*/?\s*T?|GB/T|ISO|IEC|ECE\s*R|UN\s*R)\s*[\dA-Z][\w./\s—\-:]*\d{4}\s*$",
    re.IGNORECASE,
)
_RE_PAGE_NUMBER = re.compile(r"^\s*(?:\d{1,3}|[IVXLC]+|[ⅠⅡⅢⅣⅤⅥⅦⅧⅨⅩⅪⅫ]+)\s*$")


def _rewrite_marker_asset_links(
    md_text: str,
    marker_dir: Path,
    target_dir: Path,
    slug: str,
) -> tuple[str, list[str]]:
    """Copy marker image assets next to the source Markdown and rewrite links."""
    asset_dir = target_dir / f"{slug}_assets"
    copied_assets: list[str] = []

    def _replace(match: re.Match) -> str:
        alt_text, link = match.groups()
        if re.match(r"^(?:https?://|data:)", link):
            return match.group(0)

        source_asset = (marker_dir / link).resolve()
        if not source_asset.exists() or not source_asset.is_file():
            return match.group(0)

        asset_dir.mkdir(parents=True, exist_ok=True)
        target_asset = asset_dir / source_asset.name
        if target_asset.exists() and source_asset.read_bytes() != target_asset.read_bytes():
            target_asset = asset_dir / f"{len(copied_assets) + 1}-{source_asset.name}"
        shutil.copy2(source_asset, target_asset)
        copied_assets.append(str(target_asset))
        return f"![{alt_text}]({asset_dir.name}/{target_asset.name})"

    return _RE_MARKDOWN_IMAGE.sub(_replace, md_text), copied_assets


def _normalize_standard_tokens(text: str) -> str:
    """Normalize common GB/ISO token artifacts from PDF extractors."""
    text = re.sub(r"\bGB\s*/\s*T\s*", "GB/T ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bGB\s+/\s+T\s*", "GB/T ", text, flags=re.IGNORECASE)
    text = re.sub(r"\bGB/T\s+(\d)", r"GB/T \1", text, flags=re.IGNORECASE)
    text = re.sub(r"\bGB\s*(\d{3,})\s*[—-]\s*(\d{4})", r"GB \1—\2", text, flags=re.IGNORECASE)
    text = re.sub(r"\bGB/T\s*(\d{3,})\s*[—-]\s*(\d{4})", r"GB/T \1—\2", text, flags=re.IGNORECASE)
    text = re.sub(r"([—-])\s+(\d{4})(?=\D|$)", r"\1\2", text)
    return text


def _collapse_cjk_spacing(text: str) -> str:
    """Collapse character-level CJK spacing without merging normal prose gaps."""
    lines = []
    for line in text.split("\n"):
        if len(_RE_CJK_SPACED.findall(line)) >= 4:
            line = _RE_CJK_SPACED.sub("", line)
        lines.append(line)
    return "\n".join(lines)


def _remove_page_noise(text: str) -> str:
    """Remove repeated standard headers, standalone page numbers, and watermarks."""
    lines = text.split("\n")
    header_counts: dict[str, int] = {}
    for line in lines:
        stripped = line.strip()
        normalized = re.sub(r"\s+", "", stripped.lstrip("#").strip()).upper()
        if _RE_STANDARD_HEADER.match(stripped):
            header_counts[normalized] = header_counts.get(normalized, 0) + 1

    seen_headers: set[str] = set()
    cleaned = []
    for line in lines:
        stripped = line.strip()
        normalized = re.sub(r"\s+", "", stripped.lstrip("#").strip()).upper()

        if stripped == "SAC":
            continue
        if stripped.startswith("ICS") and "CCS" in stripped:
            continue
        if _RE_PAGE_NUMBER.match(stripped):
            continue
        if _RE_STANDARD_HEADER.match(stripped) and header_counts.get(normalized, 0) > 1:
            if normalized in seen_headers:
                continue
            seen_headers.add(normalized)

        cleaned.append(line)

    return "\n".join(cleaned)


def _remove_duplicate_table_titles(text: str) -> str:
    """Remove table rows whose text content duplicates the preceding plain text.

    pymupdf4llm often emits the table title twice: once as paragraph text and
    again as a broken table row (e.g. |表|1 栏|...). This detects and removes
    the duplicate by comparing normalized text content.
    """
    lines = text.split("\n")
    result = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line starts a table (has | but isn't a separator)
        if "|" in stripped and not re.match(r"^\|[\s\-:|]+\|$", stripped):
            # Get the text content of this line: remove | and whitespace
            row_content = re.sub(r"\s+", "", stripped.replace("|", ""))

            # Look backward for the preceding non-empty plain text lines
            prev_lines = []
            j = len(result) - 1
            while j >= 0 and len(prev_lines) < 3:
                prev = result[j].strip()
                if prev and "|" not in prev:
                    prev_lines.insert(0, prev)
                j -= 1

            # Build combined preceding text
            prev_text = re.sub(r"\s+", "", "".join(prev_lines))

            # If the row content is a substring of the preceding text
            # (or vice versa), it's a duplicate title row — skip it.
            if row_content and prev_text and len(row_content) > 5:
                if row_content in prev_text or prev_text in row_content:
                    i += 1
                    continue

        result.append(line)
        i += 1

    return "\n".join(result)


def _clean_artifacts(text: str) -> str:
    """Clean common extraction artifacts from Markdown text.

    Handles artifacts from both marker-pdf and pymupdf4llm output.
    """
    # 1. Remove image markers
    text = _RE_PICTURE.sub("", text)

    # 2. Unwrap bracket artifacts: [X] -> X when X is purely CJK/punctuation.
    #    marker-pdf wraps uncertain tokens in brackets like [—] [年版的] [)] [,]
    def _unwrap(m: re.Match) -> str:
        content = m.group(1)
        if _UNWRAP_SAFE.match(content):
            return content
        return m.group(0)

    text = re.sub(r"\[([^\]]+?)\]", _unwrap, text)

    # 3. Normalize common standard-token artifacts before structural cleanup
    text = _normalize_standard_tokens(text)

    # 4. Collapse character-level CJK spacing from layout tools
    text = _collapse_cjk_spacing(text)

    # 5. Split concatenated English words at lowercase->uppercase boundaries
    text = _RE_CONCAT.sub(r"\1 \2", text)

    # 6. Remove stray <br> tags
    text = _RE_BR.sub("", text)

    # 7. Remove duplicate table title rows (|表|1 栏|...) that repeat text above
    text = _remove_duplicate_table_titles(text)

    # 8. Remove stray page headers and footer noise
    text = _remove_page_noise(text)

    # 9. Collapse 3+ blank lines into 2
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def _select_pdf_engine(engine: PdfEngine, page_count: int, ocr_required: bool) -> PdfEngine:
    """Select extraction engine for this document."""
    if engine != "auto":
        return engine
    if not ocr_required and page_count >= _MARKER_MIN_PAGES and _resolve_marker_single():
        return "marker"
    return "pymupdf4llm"


def _assess_quality(md_text: str, page_count: int) -> dict:
    """Assess the quality of extracted Markdown.

    Returns dict with quality metrics.
    """
    total_chars = len(md_text)
    avg_chars_per_page = total_chars / max(page_count, 1)
    line_count = len([l for l in md_text.split("\n") if l.strip()])

    omitted_count = len(re.findall(r"\*\*==>\s*picture.*?omitted", md_text))
    long_no_space = len(re.findall(r"[a-zA-Z]{50,}", md_text))

    is_poor = (
        avg_chars_per_page < _MIN_CHAR_PER_PAGE
        or omitted_count > page_count * 0.5
        or long_no_space > 10
    )

    return {
        "total_chars": total_chars,
        "avg_chars_per_page": round(avg_chars_per_page, 1),
        "line_count": line_count,
        "omitted_images": omitted_count,
        "concatenated_words": long_no_space,
        "is_poor": is_poor,
    }


def extract_pdf(
    pdf_path: str | Path,
    slug: str,
    sources_dir: SourcesDir = "standards",
    output_base: Path | None = None,
    engine: PdfEngine | None = None,
) -> dict:
    """Extract Markdown/text from a PDF.

    Automatically selects the best extraction method:
    - pymupdf4llm for text-based PDFs (GB/ISO standards, regulations)
    - marker-pdf for scanned/image-based PDFs that need OCR

    Args:
        pdf_path: Path to the source PDF file.
        slug: Slug for the output filename.
        sources_dir: Target subdirectory under sources/.
        output_base: Base directory for sources output (defaults to CWD/sources).
        engine: Extraction engine. Defaults to STANDARDS_WIKI_PDF_ENGINE or auto.

    Returns:
        dict with:
            - source_text: path to extracted Markdown file
            - ocr_required: bool indicating if PDF likely needs OCR
            - page_count: total pages in PDF
            - text_pages: number of pages with extractable text
            - extracted_chars: total character count
            - extraction_method: which tool was used
            - quality: quality assessment dict
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    # Count pages and check text density per page
    doc = pymupdf.open(pdf_path)
    page_count = len(doc)

    text_pages = 0
    total_chars = 0
    for page in doc:
        text = page.get_text()
        if len(text.strip()) > 50:
            text_pages += 1
        total_chars += len(text)

    doc.close()

    ocr_required = text_pages < _MIN_TEXT_PAGES

    # Write extracted Markdown to sources/
    base = output_base if output_base is not None else _DEFAULT_SOURCES_DIR
    target_dir = base / sources_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    # Extract using best method for this PDF type
    md_text = ""
    extraction_method = "unknown"
    assets: list[str] = []
    selected_engine = _select_pdf_engine(
        (engine or os.environ.get("STANDARDS_WIKI_PDF_ENGINE", "auto")).lower(),  # type: ignore[arg-type]
        page_count,
        ocr_required,
    )

    if selected_engine == "marker":
        marker_result = _extract_with_marker(
            pdf_path,
            slug=slug,
            target_dir=target_dir,
            use_ocr=ocr_required,
        )
        if marker_result:
            md_text, assets = marker_result
            extraction_method = "marker-pdf"
            if ocr_required:
                extraction_method += " (OCR)"
        else:
            md_text = _extract_with_pymupdf(pdf_path)
            extraction_method = "pymupdf4llm (marker failed)"
    else:
        # Text-based PDF: pymupdf4llm produces cleaner output
        md_text = _extract_with_pymupdf(pdf_path)
        extraction_method = "pymupdf4llm"

        # Fall back to marker-pdf if pymupdf4llm produced very little
        if not ocr_required and len(md_text.strip()) < _MIN_CHARS_FALLBACK:
            marker_result = _extract_with_marker(
                pdf_path,
                slug=slug,
                target_dir=target_dir,
                use_ocr=ocr_required,
            )
            if marker_result and len(marker_result[0].strip()) > len(md_text.strip()):
                md_text, assets = marker_result
                extraction_method = "marker-pdf (pymupdf4llm sparse)"

    # Clean artifacts before quality assessment
    md_text = _clean_artifacts(md_text)

    # Assess quality AFTER cleaning
    quality = _assess_quality(md_text, page_count)

    output_filename = f"{slug}.md"
    output_path = target_dir / output_filename

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"<!-- Source: {pdf_path.name} -->\n")
        f.write(f"<!-- Extracted at: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} -->\n")
        f.write(f"<!-- Extraction method: {extraction_method} -->\n")
        if ocr_required:
            f.write("<!-- WARNING: OCR required — low text density detected -->\n")
        if quality["is_poor"]:
            f.write(f"<!-- WARNING: Extraction quality may be low — avg {quality['avg_chars_per_page']} chars/page -->\n")
        f.write("\n")
        f.write(md_text)

    return {
        "source_text": str(output_path),
        "ocr_required": ocr_required,
        "page_count": page_count,
        "text_pages": text_pages,
        "extracted_chars": len(md_text),
        "extraction_method": extraction_method,
        "assets": assets,
        "quality": quality,
    }
