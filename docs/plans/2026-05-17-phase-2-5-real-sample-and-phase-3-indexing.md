# Phase 2.5 and Phase 3 MVP Plan

Date: 2026-05-17

Status: implemented

## Goal

Phase 2.5 validates the Phase 2 candidate pipeline against a real local sample.
Phase 3 MVP adds deterministic, rebuildable indexes without vector search or a service layer.

The combined outcome should be:

- one real document can run through compile, provision split, requirement extraction, candidate page generation, and validation;
- the run produces a review report that names quality issues instead of pretending extraction is perfect;
- Markdown and JSON indexes can be rebuilt from candidate outputs and draft document pages;
- a small local search command can find document IDs and provision labels from those deterministic indexes.

## Non-Goals

- Do not improve PDF-to-Markdown extraction quality in this phase.
- Do not commit large real sample PDFs or generated real candidate outputs unless explicitly approved.
- Do not build SQLite FTS5 yet.
- Do not add vector DB, graph DB, FastAPI, or answer generation.
- Do not promote machine-extracted content into formal `provisions/` or `clauses/`.

## Role Split

### Codex: Quality Owner

Codex owns:

- task slicing and Claude handoff prompts;
- reviewing diffs and schema choices;
- running real sample checks;
- deciding which real sample quality issues are in scope;
- final test gate and optional commit/push.

Codex may make small quality fixes when Claude stalls or when the issue is a narrow integration bug.

### Claude Code: Implementation Engineer

Claude Code owns bounded implementation tasks:

- implement one task card at a time;
- edit only allowed files;
- add focused tests;
- run task tests and report results;
- avoid real sample artifacts in commits;
- stop on unexpected conflicting changes.

## Phase 2.5 Task Cards

### P25-01: Real Sample Runner

Owner: Claude Code

Goal:

- add a command that runs the existing Phase 2 pipeline for one `document_id` and writes a machine-readable report.

Suggested files:

- `src/standards_wiki/real_run.py`
- `tools/run_phase2_sample.py`
- `tests/test_real_run.py`

Behavior:

- input: `document_id`;
- run compile document with overwrite option;
- run split provisions;
- run extract requirements;
- run generate candidate provision pages;
- run validate;
- write `_reviews/phase2-runs/<document_id>.json`;
- print counts and output paths.

Safety:

- default output may write generated artifacts locally;
- tests must use `tmp_path`;
- do not add real generated outputs to git.

Report fields:

```yaml
document_id: string
status: ok | failed
outputs:
  draft_document: string
  provisions_jsonl: string
  requirements_jsonl: string
  provision_pages_dir: string
counts:
  provisions: int
  requirements: int
  validation_errors: int
  validation_warnings: int
warnings: []
errors: []
```

### P25-02: Real Sample Quality Audit

Owner: Claude Code, reviewed by Codex

Goal:

- add a small audit module that summarizes candidate quality without making legal conclusions.

Suggested files:

- `src/standards_wiki/audit.py`
- `tools/audit_candidates.py`
- `tests/test_audit.py`

Checks:

- provisions with empty or very short text;
- labels that look like table-of-contents noise;
- fallback-only split;
- duplicate provision labels;
- unusually high requirement density;
- requirement candidates missing strong source wording;
- modality distribution.

Output:

- JSON report under `_reviews/phase2-runs/<document_id>-audit.json`;
- human-readable CLI summary.

### P25-03: Real GB 7258 Dry Run

Owner: Codex

Goal:

- run the real local `gb-7258-2017` sample through `tools/run_phase2_sample.py`;
- run `tools/audit_candidates.py`;
- inspect representative outputs;
- record whether additional splitter improvements are needed before Phase 3.

Commit rule:

- do not commit generated real outputs by default.

## Phase 3 MVP Task Cards

### P3-01: Index Data Collector

Owner: Claude Code

Goal:

- collect deterministic document, provision, and requirement records from draft pages and candidate JSONL.

Suggested files:

- `src/standards_wiki/indexer.py`
- `tests/test_indexer.py`

Inputs:

- `documents/drafts/*.md`;
- `_candidates/metadata/*.yaml`;
- `_candidates/provisions/*.jsonl`;
- `_candidates/requirements/*.jsonl`;
- optional `_candidates/provision-pages/**/*.md`.

Requirements:

- no network;
- deterministic sorting;
- tolerate missing optional files;
- report duplicate document IDs, provision IDs, and requirement IDs.

### P3-02: Markdown Index Generator

Owner: Claude Code

Goal:

- generate rebuildable Markdown indexes.

Suggested files:

- `src/standards_wiki/indexer.py`
- `tools/build_indexes.py`
- `tests/test_build_indexes_cli.py`

Outputs:

- `indexes/documents-index.md`;
- `indexes/provisions-index.md`;
- `indexes/requirements-index.md`;
- `indexes/effective-dates-index.md`.

Rules:

- keep machine-extracted review status visible;
- include source paths;
- sort rows by IDs;
- tests write to `tmp_path`, not repository indexes.

### P3-03: JSON Export MVP

Owner: Claude Code

Goal:

- export deterministic JSON files that can later feed SQLite or a search service.

Suggested files:

- `src/standards_wiki/indexer.py`
- `tools/export_json.py`
- `tests/test_export_json_cli.py`

Outputs:

- `db/json/documents.json`;
- `db/json/provisions.json`;
- `db/json/requirements.json`;
- `db/json/manifest.json`.

Rules:

- JSON uses UTF-8 with readable Chinese;
- manifest includes record counts;
- generated `db/json` should remain derived output and should not be committed by default unless explicitly selected.

### P3-04: Deterministic Search MVP

Owner: Claude Code

Goal:

- provide a simple local search command over deterministic records.

Suggested files:

- `src/standards_wiki/search.py`
- `tools/search.py`
- `tests/test_search.py`

Behavior:

- query over document title, document ID, standard ID, provision label, provision text, and requirement quote;
- support `--limit`;
- print record type, ID, title/label, review status, and source path;
- no vector search or external service.

### P3-05: README and Roadmap Update

Owner: Claude Code

Goal:

- document Phase 2.5 and Phase 3 MVP commands.

Suggested files:

- `README.md`
- `_meta/roadmap.md`

## Recommended Execution Order

1. P25-01 real sample runner.
2. P25-02 candidate audit.
3. P25-03 Codex real GB 7258 dry run and quality decision.
4. P3-01 index data collector.
5. P3-02 Markdown index generator.
6. P3-03 JSON export MVP.
7. P3-04 deterministic search MVP.
8. P3-05 docs update.

## Claude Code Handoff Template

```text
You are the implementation engineer for standards-llm-wiki.
Codex is the quality owner and reviewer.

Work on exactly this task: <TASK_ID>.

Allowed files:
<FILES>

Do not modify raw/, sources/, _candidates/ real sample artifacts, db/json generated output, or unrelated files.
Do not commit or push.
Use tmp_path fixtures in tests.
Run the listed tests and report changed files, test results, and risks.
```

## Acceptance Gate

- Phase 2.5 real run works for `gb-7258-2017` locally or produces an explicit report explaining why it failed.
- P3 indexes can be rebuilt from a clean test fixture.
- P3 search finds exact document IDs and provision labels.
- `.venv/bin/python -m pytest -q` passes.
- `git diff --check` passes.
- Real generated artifacts remain uncommitted unless explicitly approved.
