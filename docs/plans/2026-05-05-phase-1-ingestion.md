# Phase 1 Ingestion Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the first working ingestion pipeline for PDF files and webpage URLs.

**Architecture:** Keep Markdown/wiki as the source of truth. Phase 1 writes only raw files, extracted source text, candidate metadata, candidate documents, and job records. It does not promote content into final standards/provisions/topics indexes.

**Tech Stack:** Python, PyMuPDF/pymupdf4llm, requests, BeautifulSoup, markdownify, PyYAML, pytest.

---

## Task 1: Add Python project scaffold

**Objective:** Create a minimal Python package layout for ingestion code.

**Files:**
- Create: `pyproject.toml`
- Create: `src/standards_wiki/__init__.py`
- Create: `tests/.gitkeep`

**Verification:**

```bash
python -m pytest -q
```

Expected: pytest runs, even if there are no tests yet or only placeholder tests.

---

## Task 2: Implement path and slug helpers

**Objective:** Add reusable helpers for safe filenames, timestamps, and relative paths.

**Files:**
- Create: `src/standards_wiki/utils.py`
- Test: `tests/test_utils.py`

**Key behaviors:**

- `slugify("GB 7258-2017 机动车运行安全技术条件")` returns a stable lowercase ASCII-ish slug when possible.
- `utc_now_iso()` returns ISO timestamp ending with `Z`.
- `ensure_parent(path)` creates parent directories.

---

## Task 3: Implement job records

**Objective:** Track pipeline state under `_jobs/`.

**Files:**
- Create: `src/standards_wiki/jobs.py`
- Test: `tests/test_jobs.py`

**Key behaviors:**

- create pending job JSON;
- move job to running/completed/failed;
- include `job_id`, `input_type`, `input`, timestamps, and error when failed.

---

## Task 4: Implement archive module

**Objective:** Store raw PDF files and HTML snapshots with SHA256 fingerprints.

**Files:**
- Create: `src/standards_wiki/archive.py`
- Test: `tests/test_archive.py`

**Key behaviors:**

- local PDF copied into `raw/standards/` by default;
- HTML text saved into `raw/web/`;
- SHA256 calculated;
- output includes raw path and hash.

---

## Task 5: Implement document classifier

**Objective:** Use deterministic rules to classify basic document type and standard family.

**Files:**
- Create: `src/standards_wiki/classifier.py`
- Test: `tests/test_classifier.py`

**Rules:**

- `GB/T` → `standard_type: gb-t`;
- `GB` → `standard_type: gb`;
- `ISO` → `standard_type: iso`;
- `ECE R` / `UN R` → `standard_type: ece`;
- otherwise `unknown`.

---

## Task 6: Implement PDF extractor

**Objective:** Extract Markdown/text from text-based PDFs and detect likely OCR requirement.

**Files:**
- Create: `src/standards_wiki/extractors/pdf.py`
- Test: `tests/test_pdf_extractor.py`

**Behavior:**

- write extracted text to `sources/standards/{slug}.md`;
- if extracted text is too short, mark `ocr_required: true`;
- do not perform OCR in phase 1.

---

## Task 7: Implement HTML extractor

**Objective:** Fetch webpage URL, save HTML snapshot, and convert content to Markdown.

**Files:**
- Create: `src/standards_wiki/extractors/html.py`
- Test: `tests/test_html_extractor.py`

**Behavior:**

- fetch URL using requests;
- save raw HTML to `raw/web/`;
- convert main body to Markdown in `sources/web/`;
- collect attachment links ending in `.pdf`, `.doc`, `.docx`.

---

## Task 8: Implement metadata extraction

**Objective:** Extract candidate metadata from source text and paths.

**Files:**
- Create: `src/standards_wiki/metadata.py`
- Test: `tests/test_metadata.py`

**Fields:**

```yaml
title: unknown
document_type: unknown
standard_id: unknown
publisher: unknown
release_date: unknown
effective_date: unknown
source_url: null
raw_path: raw/...
source_text: sources/...
sha256: ...
retrieved_at: ...
confidence: low
review_status: draft
```

---

## Task 9: Implement candidate writers

**Objective:** Persist metadata YAML and candidate document Markdown.

**Files:**
- Create: `src/standards_wiki/writers/candidate_writer.py`
- Test: `tests/test_candidate_writer.py`

**Outputs:**

```text
_candidates/metadata/{slug}.yaml
_candidates/documents/{slug}.md
```

---

## Task 10: Implement CLI scripts

**Objective:** Provide simple user-facing commands.

**Files:**
- Create: `tools/ingest_pdf.py`
- Create: `tools/ingest_url.py`
- Create: `src/standards_wiki/ingest.py`
- Test: `tests/test_ingest_smoke.py`

**Commands:**

```bash
python tools/ingest_pdf.py ./samples/example.pdf
python tools/ingest_url.py "https://example.gov.cn/notice.html"
```

---

## Task 11: Add README usage section

**Objective:** Document how to use the phase-1 ingestion pipeline.

**Files:**
- Modify: `README.md`
- Modify: `log.md`

**Content:**

- install dependencies;
- run PDF ingestion;
- run URL ingestion;
- explain generated output directories;
- explain OCR limitation.

---

## Task 12: Run final verification

**Objective:** Verify the implementation with tests and one sample file/URL.

**Commands:**

```bash
python -m pytest -q
python tools/ingest_pdf.py ./samples/example.pdf
python tools/ingest_url.py "https://example.gov.cn/notice.html"
git status --short
```

Expected:

- tests pass;
- generated files appear under `raw/`, `sources/`, `_candidates/`, `_jobs/`;
- no unreviewed generated sample artifacts are committed unless explicitly intended.