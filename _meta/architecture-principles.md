# Architecture Principles

This project should be treated as a **Regulatory Knowledge Compiler**, not a conventional RAG chatbot.

## Core Positioning

```text
Heterogeneous raw regulatory sources
  → deterministic extraction
  → long-context compile-time understanding
  → reviewed Markdown knowledge layer
  → reproducible search/graph/vector artifacts
  → citation-grounded answers
```

The system deliberately avoids the weak form of RAG:

```text
PDF → arbitrary chunks → embedding top_k → answer
```

Instead it compiles sources into durable, reviewable knowledge assets:

```text
raw/ → sources/ → documents/ → provisions/ → topics/entities/timelines/comparisons → indexes/db
```

## Why Compiler-First

Standards, regulations and policy documents are not ordinary articles:

- applicability depends on scope, definitions, exceptions and annexes;
- version and effective-date errors are high impact;
- provisions often depend on nearby provisions and cited documents;
- answers must be traceable to exact source text;
- contradiction and replacement relationships must be explicit.

Therefore the expensive reasoning should happen mostly at **build time**, not at every user query.

## Use Tiered Model Resources at Build Time

The project should use different model tiers deliberately:

1. reliable high-quality immediate model: final architecture, legal/regulatory interpretation, difficult comparisons, final review;
2. reliable medium-quality immediate model: metadata drafts, outline extraction, candidate topic/entity tags, first-pass provision splitting;
3. unstable high-capability models: background drafts, alternate reviews, contradiction checks, benchmark question generation, non-blocking cross-checks.

Use these resources mainly for:

1. complete-document reading;
2. provision-level structuring;
3. requirement/obligation extraction;
4. cross-document comparison;
5. contradiction checks;
6. citation/source traceability audits;
7. benchmark question generation.

Do **not** spend model capacity only by stuffing more raw PDF text into every query-time prompt.

## Canonical Source of Truth

Markdown remains canonical:

```text
Markdown wiki = source of truth
SQLite / JSON / vector DB / graph DB = derived artifacts
```

Derived artifacts must be reproducible from the repo.

## Retrieval Philosophy

Use deterministic retrieval before semantic retrieval:

1. exact document ID / standard ID lookup;
2. metadata filtering;
3. topic/entity indexes;
4. citation/effective-date/replacement indexes;
5. full-text search;
6. vector search as recall expansion;
7. original source lookup for final verification.

Vector search is useful, but should not be the only authority.

## Review Gates

Weak or slow model outputs are useful but cannot directly become formal regulatory conclusions.

```text
_drafts/ and _candidates/ → _reviews/ → formal wiki pages
```

Final user-facing answers about obligations, applicability, effective dates, replacement relationships or compliance impact must cite reviewed source-backed pages.

## Influences from Related Projects

| Project | Useful Pattern | Adopted As |
|---|---|---|
| Karpathy LLM Wiki | persistent Markdown wiki over raw sources | canonical wiki layer |
| csps-efpc/regkg-rcreg | RDF/SQLite/JSON derived outputs | reproducible export plan |
| OpenRegs / ADGM KG | regulation-as-code extraction | requirement/obligation schema |
| DORA/FFIEC GraphRAG | document tree + paragraph graph + embeddings | graph model |
| LegalRAG-KnowledgeGraph | phased pipeline with CSV/graph/RAG outputs | candidate/intermediate artifacts |
| NeuReg | fact/relationship/comparison/inference QA | evaluation benchmark |
| RTX-KG2 | source inventory, build logs, validation reports | provenance discipline |

## Near-Term System Shape

MVP should build these first:

```text
kb ingest        raw → sources + metadata
kb compile       sources → documents + candidates
kb review        candidates → reviewed formal pages
kb index         Markdown → SQLite FTS5 + JSON index
kb ask           deterministic lookup + cited synthesis
```

Graph/vector systems should remain optional derived layers until the Markdown compiler path is stable.
