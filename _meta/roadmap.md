# Implementation Roadmap

This roadmap assumes the project is a Regulatory Knowledge Compiler with tiered build-time model resources.

## Phase 0 — Architecture Hardening

Status: in progress.

Deliverables:

- `SCHEMA.md`
- `_meta/architecture-principles.md`
- `_meta/ingestion-pipeline.md`
- `_meta/parser-strategy.md`
- `_meta/requirement-obligation-schema.md`
- `_meta/graph-model.md`
- `_meta/evaluation-benchmark.md`
- `_meta/source-inventory.md`
- `_meta/export-formats.md`

Exit criteria:

- clear canonical model;
- clear derived artifacts;
- clear review gates;
- clear benchmark categories.

## Phase 1 — CLI Skeleton and Local Extraction

Goal: make `raw → sources → documents` work for text PDFs and webpages.

Commands:

```bash
kb ingest-file raw/standards/example.pdf
kb ingest-url https://example.gov/doc.html
kb compile-document <document_id>
kb validate
```

Deliverables:

- Typer CLI under `tools/` or package directory;
- PyMuPDF extractor;
- webpage extractor;
- document page generator;
- frontmatter validator.

Exit criteria:

- one GB PDF, one ECE/ISO PDF and one policy webpage can become `documents/` pages;
- raw/source provenance metadata exists;
- validation catches missing source fields.

## Phase 2 — Provision and Requirement Candidates

Goal: produce reviewable candidate provisions and structured requirements.

Commands:

```bash
kb split-provisions <document_id>
kb extract-requirements <document_id>
kb promote-candidates <document_id>
```

Deliverables:

- parser hints: GB, ISO, ECE, CN policy, fallback;
- `_candidates/provisions/*.jsonl`;
- `_candidates/requirements/*.jsonl`;
- provision page generator.

Exit criteria:

- provision candidates include locator and exact quote;
- requirements include modality/subject/action/object/evidence;
- unreviewed outputs stay outside formal pages.

## Phase 3 — Deterministic Indexing

Status: MVP complete.

Goal: make the wiki searchable without relying on vector search.

Commands:

```bash
.venv/bin/python tools/build_indexes.py
.venv/bin/python tools/export_json.py
.venv/bin/python tools/search.py "电池安全 ECE" --limit 10
```

Deliverables (MVP):

- Markdown index generation (documents, provisions, requirements, effective dates);
- JSON export (documents.json, provisions.json, requirements.json, manifest.json);
- deterministic local search over documents, provisions, requirements;
- duplicate ID detection in collect step;
- tolerates missing optional files.

Remaining (post-MVP):

- SQLite FTS5 export;
- topic and entity filter layers.

Exit criteria:

- exact document IDs and provision labels are retrievable;
- index can be rebuilt from clean checkout.

## Phase 3.5 — Candidate Quality, Review, Tagging, and Eval MVP

Status: completed (MVP bridge between Phase 3 and Phase 4).

Goal: close the quality gap between machine-extracted candidates and formally promoted provisions.

Deliverables:

- provision splitter quality metadata (occurrence, source_offset, deterministic duplicate suffixes);
- review manifest workflow (`manifest` → `mark reviewed` → `promote reviewed`);
- rule-based topic/entity tagging with built-in keyword dictionary;
- deterministic eval MVP runner with JSONL checks and failure reporting;
- all functionality is local and deterministic — no external API calls.

Design decisions:

- eval MVP landed here as a lightweight smoke-test layer rather than waiting for Phase 4;
- Phase 4 retains the broader benchmark scope (rubric, failure categories, cross-document samples);
- real sample artifacts (e.g. `gb-7258-2017` candidates) are never auto-promoted or committed.

## Phase 4 — Evaluation Benchmark

Status: MVP complete.

Goal: establish deterministic benchmark layer with formal JSONL check schema and structured validation.

Deliverables (MVP):

- versioned check schema (`eval/qa/schema.md`) defining 7 deterministic check types;
- eval runner (`tools/eval_candidates.py`) supporting all check types with structured failure reports;
- 4 benchmark JSONL files: `phase4_smoke`, `gb-7258-2017_factq`, `gb-7258-2017_dateq`, `gb-7258-2017_citationq`;
- 33 ground-truth checks across all check types for `gb-7258-2017`;
- benchmark data is small-scale hand-written/deterministic fixture — no real PDF or full candidate artifacts committed.

Commands:

```bash
.venv/bin/python tools/eval_candidates.py eval/qa/*.jsonl --document-id <id>
```

Exit criteria (MVP — met):

- schema covers all 7 check types with unambiguous pass/fail semantics;
- each ingested sample document has FactQ/DateQ/CitationQ;
- failure report includes category and severity per failed check.

Remaining (post-MVP):

- answer-engine grading — LLM-based answer quality evaluation;
- LLM rubric — automated scoring against reference answers;
- cross-document samples (RelationQ/ComparisonQ/InferenceQ);
- wrong version and missing exception failure visibility.

## Phase 5 — Optional Graph and Vector Layers

Goal: improve cross-document reasoning and semantic recall.

Commands:

```bash
kb export graph-jsonl
kb export neo4j-csv
kb index-vector
```

Deliverables:

- JSONL graph export;
- optional Neo4j CSV;
- optional LanceDB/Qdrant index;
- graph-backed query planner.

Exit criteria:

- document tree, citation and topic edges are navigable;
- vector results are filtered by metadata and review status;
- final answers still cite Markdown/source pages.

## Phase 6 — Answer Engine and API

Goal: provide reliable user-facing Q&A.

Commands/API:

```bash
kb ask "ECE R100 和 GB 38031 对电池安全有什么差异？"
uvicorn app.api:app
```

Endpoints:

```text
/search
/document/{document_id}
/provision/{provision_id}
/ask
```

Exit criteria:

- answers contain citations;
- answers say `unknown` when source support is insufficient;
- query planner uses deterministic indexes first;
- benchmark score improves over naive RAG baseline.

## Default Build Philosophy

- Do not overbuild frontend before ingestion/indexing is reliable.
- Do not let graph/vector DB become canonical.
- Use long-context models for compile-time review and comparison.
- Keep every generated conclusion traceable to source text.
