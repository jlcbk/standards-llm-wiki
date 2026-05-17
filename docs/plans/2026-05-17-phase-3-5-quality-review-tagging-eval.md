# Phase 3.5 Plan: Candidate Quality, Review Workflow, Tagging, and Eval MVP

Date: 2026-05-17

Status: implemented

## Completion Summary

All five task cards (P35-01 through P35-05) completed:

- **P35-01**: Splitter now emits `occurrence` + `source_offset` per locator; duplicate labels get deterministic suffixes; audit reports actionable examples.
- **P35-02**: Review manifest → mark reviewed → promote reviewed workflow implemented; unreviewed candidates are never promoted.
- **P35-03**: Rule-based tagging with built-in Chinese keyword dictionary covering `座椅`、`制动`、`灯光`、`校车` etc.; output to `_candidates/topic-tags/`.
- **P35-04**: Deterministic eval runner loads JSONL checks, validates against current candidate data, writes failure reports to `_reviews/eval-failures/`; exits non-zero on failure.
- **P35-05**: Documentation updated in README, roadmap, and this plan document.

All tests pass (`pytest -q`). Real `gb-7258-2017` dry run completes successfully.

## Goal

Phase 3.5 improves candidate quality before the project moves toward answer generation.
The current pipeline can ingest, split, extract, index, and search. A real `gb-7258-2017`
dry run also showed that the pipeline can complete, but candidate quality still needs
work before formal promotion.

Primary goals:

- reduce obvious provision splitter noise from tables of contents, page headers, and page numbers;
- make duplicate labels traceable with occurrence and source offset metadata;
- add a review/promotion workflow for machine-extracted provisions;
- add rule-based topic/entity tagging;
- add a small eval benchmark runner to measure quality regressions.

## Non-Goals

- Do not improve PDF-to-Markdown conversion here.
- Do not add LLM calls.
- Do not create a chatbot or answer engine.
- Do not commit generated real sample artifacts by default.
- Do not promote machine-extracted real `gb-7258-2017` candidates unless explicitly requested.

## Role Split

### Codex: Quality Owner

Codex owns task slicing, Claude Code prompts, review, real sample smoke tests, and final acceptance.
Codex may make small integration fixes after Claude Code produces the main implementation.

### Claude Code: Implementation Engineer

Claude Code owns implementation slices. It should edit only allowed files, add tests, avoid generated real artifacts, and not commit or push.

## Task Cards

### P35-01: Splitter Quality Metadata

Owner: Claude Code

Allowed files:

- `src/standards_wiki/provisions.py`
- `src/standards_wiki/audit.py`
- `tests/test_provisions.py`
- `tests/test_audit.py`

Requirements:

- add `occurrence` and `source_offset` to each provision locator;
- keep `label` as the original source label;
- keep `provision_id` unique with deterministic duplicate suffixes;
- filter obvious TOC/page-noise matches where possible;
- enhance audit output to report duplicate labels with examples, not just counts.

Acceptance:

- unit tests cover duplicate occurrence metadata;
- `gb-7258-2017` audit remains explicit about remaining duplicate labels.

### P35-02: Review and Promotion Workflow

Owner: Claude Code

Allowed files:

- `src/standards_wiki/review.py`
- `tools/review_candidates.py`
- `tools/promote_candidates.py`
- `tests/test_review.py`
- `tests/test_review_cli.py`

Requirements:

- create a review manifest from candidate provisions;
- support marking selected provision IDs as `reviewed`;
- promote only reviewed provisions to `provisions/<document_id>/<provision_id>.md`;
- never promote unreviewed candidates;
- preserve source locator and evidence quote in promoted pages.

Acceptance:

- tests prove unreviewed candidates are skipped;
- promoted pages have `review_status: reviewed`.

### P35-03: Rule-Based Topic and Entity Tagging

Owner: Claude Code

Allowed files:

- `src/standards_wiki/tagging.py`
- `tools/tag_candidates.py`
- `tests/test_tagging.py`
- `tests/test_tagging_cli.py`

Requirements:

- use a small built-in rule dictionary;
- tag provisions and requirements with `topics` and `entities`;
- write `_candidates/topic-tags/<document_id>.json`;
- include topic IDs such as `seats`, `braking-system`, `lighting-system`, `vehicle-dimensions`, `school-bus`;
- do not call external services.

Acceptance:

- tests cover Chinese keywords such as `座椅`, `制动`, `灯光`, `校车`.

### P35-04: Eval Benchmark MVP

Owner: Claude Code

Allowed files:

- `src/standards_wiki/eval.py`
- `tools/eval_candidates.py`
- `eval/qa/phase3_5_smoke.jsonl`
- `tests/test_eval.py`
- `tests/test_eval_cli.py`

Requirements:

- load JSONL QA checks;
- support simple deterministic checks over current records/search results;
- write `_reviews/eval-failures/<run_id>.json`;
- report pass/fail counts;
- include smoke checks for exact document ID, provision label, and keyword search.

Acceptance:

- tests use `tmp_path`;
- eval runner exits non-zero when checks fail.

### P35-05: Documentation

Owner: Claude Code

Allowed files:

- `README.md`
- `_meta/roadmap.md`

Requirements:

- document Phase 3.5 commands and boundaries;
- keep generated real artifacts out of examples.

## Recommended Execution

1. P35-01 splitter and audit quality metadata.
2. Codex runs real `gb-7258-2017` smoke and decides whether remaining noise is acceptable.
3. P35-02 review/promotion workflow.
4. P35-03 topic/entity tagging.
5. P35-04 eval benchmark.
6. P35-05 docs and final verification.

## Acceptance Gate

- `.venv/bin/python -m pytest -q` passes.
- `git diff --check` passes.
- real `gb-7258-2017` dry run still completes.
- audit report includes actionable duplicate-label examples.
- promotion workflow refuses unreviewed candidates.
- topic tagging and eval are deterministic and local.
