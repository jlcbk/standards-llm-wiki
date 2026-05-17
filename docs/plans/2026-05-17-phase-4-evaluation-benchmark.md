# Phase 4 Plan: Evaluation Benchmark Schema and Deterministic Checks

Date: 2026-05-17

Status: implemented

## Goal

Phase 4 turns the Phase 3.5 eval MVP into a structured benchmark layer with a formal JSONL check schema, deterministic validation types, and clear ownership boundaries.

The immediate outcome should be:

- a versioned check schema (`eval/qa/schema.md`) that defines all deterministic check types and their JSONL wire format;
- a Phase 4 plan document (this file) that splits remaining work into bounded task cards;
- updated meta documentation that clarifies Phase 4 MVP scope is deterministic checks, not answer-engine grading.

## Non-Goals

- Do not commit real PDFs or complete candidate generation artifacts.
- Do not build answer engine scoring or LLM-based evaluation in this phase.
- Do not modify existing code, tests, or pipeline outputs.
- Do not add vector/graph layers or API endpoints.

## Role Split

### Claude Code: Implementation Engineer

Claude Code owns:

- schema design and documentation files;
- implementation of bounded task cards;
- deterministic check type definitions and examples;
- no commits or pushes without explicit Codex approval.

### Codex: Quality Owner and Acceptance

Codex owns:

- reviewing schema design and check type coverage;
- validating deterministic check semantics against real pipeline behavior;
- final acceptance of each task card;
- committing approved changes.

## Task Cards

### P4-01: Benchmark Schema and Plan Document

Owner: Claude Code

Allowed files:

- `docs/plans/2026-05-17-phase-4-evaluation-benchmark.md`
- `eval/qa/schema.md`
- `_meta/evaluation-benchmark.md`

Requirements:

- define deterministic check JSONL schema with common fields: `id`, `type`, `category`, `severity`, `expected`, `notes`;
- enumerate check types: `document_id_exists`, `provision_label_exists`, `keyword_search`, `requirement_modality_exists`, `evidence_quote_exists`, `metadata_field_equals`, `topic_tag_exists`;
- provide one JSONL example and semantic description per check type;
- update `_meta/evaluation-benchmark.md` to reference schema and clarify MVP scope;
- split remaining Phase 4 work into P4-02 through P4-04 task cards.

Acceptance:

- schema is unambiguous and covers all existing Phase 3.5 smoke checks;
- each check type has a clear pass/fail criterion;
- meta documentation correctly scopes Phase 4 MVP as deterministic checks only.

### P4-02: Deterministic Check Runner Implementation

Owner: Claude Code

Allowed files:

- `src/standards_wiki/eval.py`
- `tools/eval_candidates.py`
- `eval/qa/phase4_smoke.jsonl`
- `tests/test_eval.py`
- `tests/test_eval_cli.py`

Requirements:

- extend eval runner to support all check types defined in schema;
- load checks from JSONL, validate against schema before execution;
- write structured failure reports with category and severity;
- backward-compatible with existing Phase 3.5 smoke checks.

Acceptance:

- all seven check types pass unit tests with synthetic data;
- existing Phase 3.5 smoke checks still pass unchanged;
- failure report includes category and severity for each failed check.

### P4-03: Real Sample Benchmark Suite

Owner: Codex (with Claude Code assistance)

Allowed files:

- `eval/qa/gb-7258-2017_factq.jsonl`
- `eval/qa/gb-7258-2017_dateq.jsonl`
- `eval/qa/gb-7258-2017_citationq.jsonl`

Requirements:

- write deterministic checks for `gb-7258-2017` covering document metadata, provision labels, keyword recall, requirement modalities, evidence quotes, and topic tags;
- target at least 30 checks across all check types;
- each check must have a ground-truth expected value derived from the source document.

Acceptance:

- all checks are deterministic and reproducible;
- check file passes schema validation;
- no real PDF or full candidate artifacts are committed.

### P4-04: Documentation and Roadmap Update

Owner: Claude Code

Allowed files:

- `README.md`
- `_meta/roadmap.md`
- `docs/plans/2026-05-17-phase-4-evaluation-benchmark.md`

Requirements:

- update roadmap Phase 4 status;
- document eval commands and schema reference;
- update this plan document with completion summary.

Acceptance:

- roadmap reflects Phase 4 progress;
- eval section in README references schema;
- no stale or misleading documentation.

## Recommended Execution

1. P4-01 schema and plan (this task card).
2. Codex reviews schema design.
3. P4-02 check runner implementation.
4. P4-03 real sample benchmark suite.
5. P4-04 documentation and roadmap update.

## Acceptance Gate

- schema is complete and unambiguous.
- all seven check types have JSONL examples.
- meta documentation scopes Phase 4 MVP correctly.
- no code, test, or generated artifact modifications.
- no commits without Codex approval.

## Completion Summary

Phase 4 deterministic benchmark layer is fully implemented:

- **P4-01 Schema**: `eval/qa/schema.md` defines 7 check types (`document_id_exists`, `provision_label_exists`, `keyword_search`, `requirement_modality_exists`, `evidence_quote_exists`, `metadata_field_equals`, `topic_tag_exists`) with common fields (`id`, `type`, `category`, `severity`, `expected`, `notes`) and backward compatibility for Phase 3.5 format.
- **P4-02 Runner**: `tools/eval_candidates.py` loads JSONL checks, validates against schema, executes all 7 check types, and writes structured failure reports with category and severity.
- **P4-03 Benchmark Suite**: 33 ground-truth checks across `gb-7258-2017_factq.jsonl`, `gb-7258-2017_dateq.jsonl`, `gb-7258-2017_citationq.jsonl`, and `phase4_smoke.jsonl` — all deterministic, hand-written fixtures derived from source document.
- **P4-04 Documentation**: README Phase 4 usage guide, roadmap status update, and this completion summary.

Benchmark JSONL files are small-scale hand-written/deterministic fixtures. No real PDF or complete candidate generation artifacts are committed to the repository.
