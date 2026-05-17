# Phase 5 Plan: SQLite FTS5 and Graph JSONL Export MVP

Date: 2026-05-18

Status: completed

## Goal

Phase 5 adds a local, deterministic export layer on top of the canonical Markdown/JSONL candidates. The two deliverables are:

1. **SQLite FTS5 database** — full-text search over documents, provisions, and requirements without external services.
2. **Graph JSONL export** — node + edge files following the graph model defined in `_meta/graph-model.md`.

Both are derived artifacts. The canonical source remains `_candidates/` and `documents/`. No external services, vector DB, or Neo4j in this phase.

## Non-Goals

- Do not commit `db/` or generated export artifacts (they are reproducible from clean checkout).
- Do not introduce Neo4j, Qdrant, LanceDB, or any external service.
- Do not build vector embeddings or semantic search.
- Do not modify existing tools, tests, or pipeline outputs — only add new export tools.
- Do not change the canonical Markdown/JSONL candidate format.

## Principles

- **Derived = disposable**: `db/` contents are rebuildable. Canonical = Markdown pages + `_candidates/*.jsonl`.
- **Single source of truth**: all export tools read from `_candidates/` and `documents/`, never from `db/`.
- **No external dependencies**: SQLite is stdlib; JSONL is plain text. No `pip install` of graph or vector packages for MVP.
- **Backward compatible**: existing Phase 3/4 tools and eval benchmarks must continue to work unchanged.

## Task Cards

### P5-01: SQLite Schema and Exporter

**Goal**: create `tools/export_sqlite.py` that builds a SQLite database with relational tables and FTS5 virtual tables from canonical candidates.

**Allowed files**:

- `tools/export_sqlite.py` (new)
- `tests/test_export_sqlite.py` (new)

**Requirements**:

- Read from `_candidates/provisions/*.jsonl`, `_candidates/requirements/*.jsonl`, `_candidates/metadata/*.yaml`, `_candidates/topic-tags/*.json`.
- Create tables following `_meta/export-formats.md` SQLite schema:
  - `documents` — one row per document metadata YAML.
  - `provisions` — one row per provision JSONL record.
  - `requirements` — one row per requirement JSONL record.
  - `documents_fts` — FTS5 virtual table over document titles and source text.
  - `provisions_fts` — FTS5 virtual table over provision labels, titles, and text.
  - `requirements_fts` — FTS5 virtual table over requirement subjects, actions, objects, and evidence.
- Output to `db/kb.sqlite` by default, configurable via `--out`.
- Idempotent: running twice produces identical output.
- CLI entry: `python tools/export_sqlite.py [--out db/kb.sqlite]`.
- Tolerate missing optional files (same pattern as Phase 3 `build_indexes.py`).

**Acceptance**:

- `python tools/export_sqlite.py` produces a valid SQLite file with all tables populated.
- Row counts match candidate counts for `gb-7258-2017`.
- FTS5 tables return results for known provision labels and keywords.
- Re-running produces byte-identical output (idempotent).

---

### P5-02: SQLite FTS5 Search CLI

**Goal**: add `tools/search_sqlite.py` for deterministic full-text search against the exported SQLite database.

**Allowed files**:

- `tools/search_sqlite.py` (new)
- `tests/test_search_sqlite.py` (new)

**Requirements**:

- Read from `db/kb.sqlite` (default) or `--db` path.
- Support search modes:
  - `--mode provisions` — search provisions FTS (default).
  - `--mode documents` — search documents FTS.
  - `--mode requirements` — search requirements FTS.
  - `--mode all` — search all FTS tables, merge and rank.
- Filter options:
  - `--document-id <id>` — restrict to a single document.
  - `--limit N` — max results (default 20).
  - `--review-status <status>` — filter by review_status field.
- Output: JSON array of matching records with highlighted snippet.
- CLI entry: `python tools/search_sqlite.py "制动系统" --mode provisions --limit 5`.
- Fallback: if `db/kb.sqlite` does not exist, print error suggesting `export_sqlite.py`.

**Acceptance**:

- Searching a known keyword returns the correct provision(s).
- `--document-id` filter narrows results correctly.
- `--mode all` returns de-duplicated results across tables.
- Graceful error when database file is missing.
- Unit tests cover each search mode and filter.

---

### P5-03: Graph JSONL Export

**Goal**: create `tools/export_graph.py` that produces node and edge JSONL files following `_meta/graph-model.md`.

**Allowed files**:

- `tools/export_graph.py` (new)
- `tests/test_export_graph.py` (new)

**Requirements**:

- Read from `_candidates/` (provisions, requirements, metadata, topic-tags) and `documents/`.
- Output:
  - `db/graph/nodes.jsonl` — one JSON object per line, each with `id`, `type`, `props`.
  - `db/graph/edges.jsonl` — one JSON object per line, each with `source`, `target`, `type`, `props`.
- Node types (from graph model): `Document`, `Provision`, `Requirement`, `Topic`, `Entity`.
- Edge types (MVP subset):
  - `HAS_PROVISION` — Document → Provision.
  - `SUBSECTION_OF` — Provision → Provision (based on label hierarchy).
  - `HAS_REQUIREMENT` — Provision → Requirement.
  - `ABOUT` — Provision → Topic (from topic-tags).
  - `MENTIONS` — Provision → Entity (from topic-tags entities).
  - `REPLACES` / `REPLACED_BY` — Document → Document (from metadata if available).
- Output directory configurable via `--out` (default `db/graph/`).
- CLI entry: `python tools/export_graph.py [--out db/graph]`.
- Idempotent: running twice produces identical output.
- Tolerate missing optional files.

**Acceptance**:

- `python tools/export_graph.py` produces `nodes.jsonl` and `edges.jsonl`.
- Node count matches distinct entities across all candidate files.
- Edge count matches expected relationships for `gb-7258-2017`.
- Every edge references valid node IDs present in `nodes.jsonl`.
- Re-running produces byte-identical output.

---

### P5-04: Export-Level Benchmark and Smoke Checks

**Goal**: extend Phase 4 eval framework with export-specific deterministic checks.

**Allowed files**:

- `eval/qa/phase5_smoke.jsonl` (new)
- `tests/test_export_benchmark.py` (new)

**Requirements**:

- Define Phase 5 check types (extend Phase 4 schema or add new categories):
  - `sqlite_table_row_count` — verify minimum row count in a SQLite table.
  - `sqlite_fts_result` — verify FTS5 returns expected result for a query.
  - `graph_node_exists` — verify a node exists in `nodes.jsonl`.
  - `graph_edge_exists` — verify an edge exists in `edges.jsonl`.
  - `graph_edge_integrity` — verify all edge endpoints exist as nodes.
- Write at least 15 smoke checks covering:
  - SQLite table population for `gb-7258-2017`.
  - FTS5 recall of known provision labels and keywords.
  - Graph node presence for document, provisions, requirements.
  - Graph edge integrity (no dangling edges).
- Checks run against generated `db/` artifacts, not committed files.
- Smoke checks are runnable via existing `eval_candidates.py` or a new `tools/eval_exports.py`.

**Acceptance**:

- All 15+ smoke checks pass against a freshly built export.
- Check types have clear pass/fail semantics.
- No committed `db/` artifacts — checks assume export has been run.

---

### P5-05: Documentation and Roadmap Closeout

**Goal**: update project documentation to reflect Phase 5 completion.

**Allowed files**:

- `docs/plans/2026-05-18-phase-5-export-layer.md` (this file)
- `_meta/roadmap.md`
- `_meta/export-formats.md` (minor updates if needed)

**Requirements**:

- Update roadmap Phase 5 status from `next` to `completed`.
- Document new CLI commands in this plan:
  - `python tools/export_sqlite.py`
  - `python tools/search_sqlite.py`
  - `python tools/export_graph.py`
- Record Phase 5 design decisions:
  - `db/` is derived, not committed.
  - Canonical source remains Markdown/JSONL candidates.
  - MVP scope excludes Neo4j, Qdrant, vector embeddings.
- Add completion summary.

**Acceptance**:

- Roadmap accurately reflects Phase 5 MVP status.
- New CLI commands are documented.
- No stale or misleading information.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite FTS5 only, no vector DB | Deterministic, zero-dependency, sufficient for label/keyword recall |
| Graph JSONL, no Neo4j CSV | Simplest interchange; Neo4j CSV can be derived from JSONL later |
| `db/` is derived, never committed | Keeps repo lean; export is reproducible from clean checkout |
| No external packages for MVP | Avoids supply-chain complexity; stdlib sqlite3 + json is sufficient |
| Export reads from `_candidates/`, not `documents/` for provisions | Candidates are the structured source; documents are presentation |

## Execution Order

1. P5-01 → P5-02 (search depends on exported database)
2. P5-03 (independent of SQLite, can run in parallel)
3. P5-04 (depends on P5-01 and P5-03 outputs)
4. P5-05 (closeout, depends on all above)

## Acceptance Gate

- SQLite export produces valid, queryable database.
- FTS5 search returns correct results for known queries.
- Graph JSONL has no dangling edges and matches candidate counts.
- All Phase 5 smoke checks pass.
- No external services or non-stdlib dependencies introduced.
- No changes to existing tools, tests, or canonical artifacts.

## Implemented Commands

```bash
.venv/bin/python tools/export_sqlite.py --candidates-dir _candidates --out db/kb.sqlite
.venv/bin/python tools/search_sqlite.py "制动" --db db/kb.sqlite --mode provisions --limit 5
.venv/bin/python tools/export_graph.py --candidates-dir _candidates --out db/graph
.venv/bin/python tools/eval_exports.py eval/qa/phase5_smoke.jsonl --candidates-dir _candidates
```

## Completion Summary

- P5-01 added a deterministic SQLite exporter with relational tables and FTS5 indexes.
- P5-02 added a JSON search CLI for SQLite FTS5 exports.
- P5-03 added deterministic Graph JSONL export for `Document`, `Provision`, `Requirement`, `Topic`, and `Entity` nodes plus MVP edges.
- P5-04 added export-level deterministic checks and a 15-check Phase 5 smoke benchmark.
- P5-05 closed roadmap/docs while keeping `db/` as a derived, uncommitted artifact.

Final smoke evidence:

```bash
.venv/bin/python tools/eval_exports.py eval/qa/phase5_smoke.jsonl --candidates-dir _candidates --sqlite-db /tmp/standards-p5-eval/kb.sqlite --graph-dir /tmp/standards-p5-eval/graph
# total: 15  passed: 15  failed: 0
```
