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

Goal: make the wiki searchable without relying on vector search.

Commands:

```bash
kb export sqlite --out db/kb.sqlite
kb export json --out db/json
kb search "电池安全 ECE"
```

Deliverables:

- SQLite FTS5 export;
- JSON index export;
- topic/document/provision lookup;
- duplicate ID detection.

Exit criteria:

- exact document IDs and provision labels are retrievable;
- topic and entity filters work;
- index can be rebuilt from clean checkout.

## Phase 4 — Evaluation Benchmark

Goal: turn quality failures into a feedback loop.

Commands:

```bash
kb eval --qa eval/qa/*.jsonl
kb eval-report
```

Deliverables:

- benchmark JSONL files;
- rubric implementation;
- failure categories;
- failure report to `_reviews/eval-failures/`.

Exit criteria:

- each ingested sample document has FactQ/DateQ/CitationQ;
- cross-document samples have RelationQ/ComparisonQ/InferenceQ;
- wrong version and missing exception failures are visible.

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
