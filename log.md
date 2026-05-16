# Standards Wiki Log

> Chronological record of wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`

## [2026-05-16] seal | Phase 1 ingestion pipeline ready for promotion work

- Isolated CLI smoke tests so subprocess-based ingestion tests write only to pytest temporary directories.
- Added ignore rules for Python build and coverage artifacts such as `*.egg-info/` and `.coverage*`.
- Normalized README and CLI usage examples to `.venv/bin/python` so commands do not depend on a system-level `python` executable.
- Re-ran the Phase 1 test suite before closing this phase.

## [2026-05-16] improve | Borrow standard-pdf-md-lab PDF conversion findings

- Added optional `marker-pdf` / `marker_single` extraction path for larger text-based standards, with automatic fallback to `pymupdf4llm`.
- Added Marker asset copying and Markdown image-link rewriting under `sources/{type}/{slug}_assets/`.
- Strengthened Markdown cleanup for GB/T bracket artifacts, CJK character spacing, repeated page headers, page numbers, and standard token normalization.
- Improved metadata extraction for compact dates such as `20170929发布` and classification from detected standard IDs when the visible title is generic.
- Added regression tests for the new PDF cleanup, Marker asset handling, and compact date metadata behavior.

## [2026-05-13] implement | Phase 1 ingestion pipeline — all 12 tasks complete

- Implemented full ingestion pipeline with 12 modules and 78 tests:
  - `src/standards_wiki/utils.py` — slugify, utc_now_iso, ensure_parent helpers
  - `src/standards_wiki/jobs.py` — job tracking (pending/running/completed/failed)
  - `src/standards_wiki/archive.py` — raw PDF/HTML archival with SHA256 fingerprints
  - `src/standards_wiki/classifier.py` — deterministic GB/GB/T/ISO/ECE classification
  - `src/standards_wiki/extractors/pdf.py` — text PDF → Markdown extraction with OCR detection
  - `src/standards_wiki/extractors/html.py` — URL fetch + HTML → Markdown conversion + attachment collection
  - `src/standards_wiki/metadata.py` — candidate metadata extraction (title, dates, publisher, standard ID)
  - `src/standards_wiki/writers/candidate_writer.py` — YAML metadata + Markdown document writers
  - `src/standards_wiki/ingest.py` — full pipeline orchestration for PDF and URL
  - `tools/ingest_pdf.py` — CLI for PDF ingestion
  - `tools/ingest_url.py` — CLI for URL ingestion
- Added comprehensive test suites: test_utils (12), test_jobs (14), test_archive (17), test_classifier (17), test_pdf_extractor (7), test_html_extractor (11), test_metadata (29), test_candidate_writer (8), test_ingest_smoke (4) = 119 tests total
- Updated README.md with Phase 1 usage guide (install, CLI commands, output dirs, OCR limitation)
- All tests pass; CLI verified with smoke tests

## [2026-05-05] update | Phase 1 ingestion development scope

- Added `_meta/phase-1-development-scope.md` describing required modules, outputs, dependencies, and acceptance criteria.
- Extended `_meta/ingestion-pipeline.md` with phase-1 PDF/URL import scope, directory mapping, module responsibilities, and non-goals.
- Added `docs/plans/2026-05-05-phase-1-ingestion.md` as the implementation plan.
- Added placeholder directories for `src/standards_wiki/`, `tools/`, `tests/`, and candidate document/source outputs.
- Updated README with the latest phase-1 development status.

## [2026-04-30] update | Add compiler-first architecture, graph, obligation, benchmark and provenance design

- Added `_meta/architecture-principles.md` to position the project as a Regulatory Knowledge Compiler rather than naive RAG.
- Added `_meta/graph-model.md` for derived document/provision/topic/entity graph exports.
- Added `_meta/requirement-obligation-schema.md` for structured regulatory obligation extraction.
- Added `_meta/evaluation-benchmark.md` plus `eval/` placeholders and rubric for FactQ/RelationQ/ComparisonQ/InferenceQ evaluation.
- Added `_meta/source-inventory.md` and `_meta/export-formats.md` for provenance and reproducible SQLite/JSON/graph/RDF artifacts.
- Added `_meta/roadmap.md` for phased implementation.
- Updated README, SCHEMA and index to reflect the compiler-first route.

## [2026-04-30] update | Generalize to heterogeneous standards, regulations, policies and rules

- Upgraded schema from GB-oriented `standard/clause` model to generic `document/provision/topic/entity` model.
- Added `documents/` and `provisions/` as recommended formal directories for heterogeneous content.
- Added raw/source categories for `policies/` and `rules/`.
- Added `_meta/ingestion-pipeline.md`, `_meta/tooling.md`, and `_meta/parser-strategy.md`.
- Added indexes for documents, provisions, topic-to-documents, and cited documents.
- Updated README and index to describe the new heterogeneous architecture.

## [2026-04-29] update | Model strategy and async workflow directories

- Added `_meta/model-strategy.md` describing model capabilities, task allocation, model selection criteria, and ingestion rules.
- Added `_drafts/`, `_candidates/`, `_reviews/`, and `_jobs/` directories for weak/slow model outputs and asynchronous processing.
- Updated README to reference the model strategy.

## [2026-04-29] create | Initial repository structure

- Created initial architecture for an AI-facing standards and regulations wiki.
- Added README, SCHEMA, index, log, metadata templates, and placeholder directories.
