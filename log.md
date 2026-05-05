# Standards Wiki Log

> Chronological record of wiki actions. Append-only.
> Format: `## [YYYY-MM-DD] action | subject`

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
