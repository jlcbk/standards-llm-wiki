# Phase 2 Development Plan: Provision and Requirement Candidates

Date: 2026-05-17

Status: implemented

## Phase Goal

Phase 2 turns Phase 1 extraction outputs into reviewable knowledge candidates:

- candidate document pages from `_candidates/documents/*.md` and `_candidates/metadata/*.yaml`;
- provision candidates in `_candidates/provisions/*.jsonl`;
- structured requirement candidates in `_candidates/requirements/*.jsonl`;
- validation gates that keep unreviewed machine output outside formal wiki pages.

This phase is deliberately not a PDF-to-Markdown quality phase. PDF extraction can improve later; Phase 2 should work from whatever `sources/` and `_candidates/` artifacts already exist.

## Non-Goals

- Do not build the final Q&A engine.
- Do not add vector DB, graph DB, or SQLite FTS exports.
- Do not make legal or compliance conclusions from unreviewed text.
- Do not silently promote draft candidates into formal topic or clause pages.
- Do not commit large sample PDFs or generated experiment outputs unless they are intentionally selected as small test fixtures.

## Current Baseline

The repository already has:

- ingestion scripts: `tools/ingest_pdf.py`, `tools/ingest_url.py`;
- package modules under `src/standards_wiki/`;
- candidate writers for `_candidates/metadata` and `_candidates/documents`;
- Phase 1 tests for archive, extraction, metadata, candidate writing, and ingest smoke behavior.

The next step is to add deterministic compile, split, extract, and validate layers on top of those candidates.

## Role Split

### Role A: Codex, Quality Owner

Codex owns architecture, quality gates, integration, and final acceptance.

Responsibilities:

- keep Phase 2 scope aligned with `_meta/roadmap.md`, `_meta/ingestion-pipeline.md`, `_meta/parser-strategy.md`, and `_meta/requirement-obligation-schema.md`;
- assign small task cards to Claude/GLM-5.1 with explicit allowed files;
- review diffs before integration;
- run the full test suite before accepting each slice;
- resolve schema or naming conflicts;
- keep generated real-world artifacts out of commits unless explicitly approved;
- prepare final Phase 2 seal commit when requested.

Codex may implement small glue or test fixes, but should avoid taking over Claude's active task unless the task is blocked.

### Role B: Claude/GLM-5.1, Implementation Engineer

Claude/GLM-5.1 owns small, bounded implementation slices.

Responsibilities:

- implement one task card at a time;
- only edit the allowed files listed in that card;
- write or update tests with the code change;
- use `tmp_path` or small inline fixtures for tests instead of repository sample artifacts;
- report changed paths, tests run, and assumptions;
- stop instead of overwriting unexpected uncommitted changes.

Claude/GLM-5.1 should not make final architecture decisions, change dependencies, push to GitHub, or promote unreviewed outputs into formal pages unless Codex explicitly approves that task.

## Collaboration Protocol

1. Codex assigns exactly one task card to Claude/GLM-5.1.
2. Claude/GLM-5.1 checks `git status --short` before editing.
3. Claude/GLM-5.1 edits only the task's allowed files.
4. Claude/GLM-5.1 runs the task-specific tests and reports results.
5. Codex reviews the diff, runs broader tests, and either accepts or asks for a focused fix.
6. Accepted slices can be committed individually with Chinese commit messages, for example `feat: 添加候选条款拆分器`.

Stop conditions:

- an allowed file already has unexpected uncommitted changes;
- the task appears to require a new dependency;
- a schema conflicts with `_meta/requirement-obligation-schema.md` or `_meta/parser-strategy.md`;
- generated outputs are too large or unstable to commit;
- tests require real PDFs or network access.

## Phase 2 Task Breakdown

### P2-00: Planning and Scope Lock

Primary owner: Codex

Goal:

- lock the Phase 2 execution plan and collaboration rules.

Allowed files:

- `docs/plans/2026-05-17-phase-2-provision-requirement-candidates.md`

Done criteria:

- plan exists;
- tasks are split into Claude-sized implementation cards;
- quality gates and non-goals are explicit.

### P2-01: Candidate IO Foundation

Primary owner: Claude/GLM-5.1

Goal:

- add a small, dependency-light module for loading metadata, candidate documents, and JSONL records.

Suggested files:

- `src/standards_wiki/candidates.py`
- `tests/test_candidates.py`

Expected behavior:

- load YAML metadata from `_candidates/metadata/<document_id>.yaml`;
- load candidate Markdown from `_candidates/documents/<document_id>.md`;
- split Markdown frontmatter from body;
- write JSONL records deterministically with UTF-8 and one JSON object per line;
- read JSONL records back for validation tests.

Tests:

- metadata load success;
- missing file raises a clear `FileNotFoundError`;
- Markdown frontmatter/body split works with and without frontmatter;
- JSONL round trip preserves Unicode;
- writer creates parent directories under `tmp_path`.

Codex acceptance gate:

- no real candidate artifacts are read or written during tests;
- no new runtime dependency is added;
- `.venv/bin/python -m pytest tests/test_candidates.py -q` passes.

### P2-02: Document Compiler V1

Primary owner: Claude/GLM-5.1

Goal:

- compile a draft wiki document page from candidate metadata and candidate Markdown.

Suggested files:

- `src/standards_wiki/compiler.py`
- `tools/compile_document.py`
- `tests/test_compiler.py`

Expected behavior:

- input: `document_id`;
- read `_candidates/metadata/<document_id>.yaml`;
- read `_candidates/documents/<document_id>.md`;
- output a Markdown page with normalized frontmatter, provenance fields, and draft review status;
- default output path should be deterministic and review-safe.

Path decision:

- use `documents/drafts/<document_id>.md` for unreviewed compiled pages in Phase 2;
- do not write formal `standards/`, `clauses/`, or `topics/` pages yet.

Required frontmatter fields:

- `document_id`;
- `title`;
- `document_type`;
- `standard_id`;
- `source_text`;
- `raw_path`;
- `review_status: draft`;
- `confidence`;
- `generated_from: candidate`;

Tests:

- compiles with complete metadata;
- compiles with unknown optional fields;
- preserves body content;
- refuses to overwrite an existing page unless an explicit overwrite option is used;
- CLI returns non-zero for missing candidate inputs.

Codex acceptance gate:

- output is deterministic except timestamps should be avoided or injectable;
- no formal reviewed page is generated by default.

### P2-03: Provision Splitter V1

Primary owner: Claude/GLM-5.1

Goal:

- split candidate document text into provision candidates using stable labels when possible.

Suggested files:

- `src/standards_wiki/provisions.py`
- `tests/test_provisions.py`

Expected behavior:

- recognize GB/ISO/ECE-style numeric labels such as `1`, `4.1`, `4.1.1`, `11.6`;
- recognize Chinese article labels such as `第一条`;
- recognize annex labels such as `附录 A`, `Annex A`;
- preserve exact text quote for each provision;
- emit low-confidence fallback sections when no stable labels exist.

Minimum provision record:

```yaml
document_id: gb-7258-2017
provision_id: gb-7258-2017-11-6
label: "11.6"
kind: clause
title: unknown
text: "..."
locator:
  label: "11.6"
source_text: sources/standards/gb-7258-2017.md
raw_path: raw/standards/gb-7258-2017.pdf
confidence: medium
review_status: machine_extracted
evidence:
  quote: "..."
```

Tests:

- numeric labels split into stable ordered records;
- Chinese article labels split correctly;
- annex labels split correctly;
- generated IDs are path-safe;
- quote text is not normalized away.

Codex acceptance gate:

- splitter is rule-based and deterministic;
- parser hints can influence behavior but fallback parser always works;
- no LLM call is introduced.

### P2-04: Provision JSONL Writer and CLI

Primary owner: Claude/GLM-5.1

Goal:

- wire the provision splitter to `_candidates/provisions/<document_id>.jsonl`.

Suggested files:

- `src/standards_wiki/provisions.py`
- `tools/split_provisions.py`
- `tests/test_split_provisions_cli.py`

Expected behavior:

- command: `.venv/bin/python tools/split_provisions.py <document_id>`;
- reads candidate metadata and candidate document;
- writes `_candidates/provisions/<document_id>.jsonl`;
- prints a small summary: document ID, provision count, output path, warnings.

Tests:

- CLI writes JSONL under `tmp_path`;
- duplicate provision IDs are rejected or warned deterministically;
- missing candidate document returns non-zero;
- output records include locator and evidence quote.

Codex acceptance gate:

- no repository-level real outputs are produced in tests;
- CLI remains simple and script-based, consistent with Phase 1 tools.

### P2-05: Requirement Extractor V1

Primary owner: Claude/GLM-5.1

Goal:

- extract structured requirement candidates from provision text with a rule-based modality detector.

Suggested files:

- `src/standards_wiki/requirements.py`
- `tests/test_requirements.py`

Expected behavior:

- map Chinese signals:
  - `必须`, `应`, `应当`, `须` -> `must`;
  - `不得`, `禁止`, `不应` -> `must_not`;
  - `宜`, `建议` -> `should`;
  - `可`, `可以` -> `may`;
  - `是指`, `定义为` -> `define`;
- map English signals:
  - `shall`, `must`, `is required to` -> `must`;
  - `shall not`, `must not`, `prohibited` -> `must_not`;
  - `should`, `recommended` -> `should`;
  - `may`, `permitted` -> `may`;
  - `means`, `refers to`, `is defined as` -> `define`;
- keep `subject`, `action`, `object`, `condition`, and `exception` as `unknown` when rule extraction is uncertain;
- always attach exact quote and source locator.

Minimum requirement record:

```yaml
requirement_id: gb-7258-2017-11-6-r1
document_id: gb-7258-2017
provision_id: gb-7258-2017-11-6
modality: must
subject: unknown
action: unknown
object: unknown
condition: unknown
exception: unknown
evidence:
  quote: "..."
  source_text: sources/standards/gb-7258-2017.md
  raw_path: raw/standards/gb-7258-2017.pdf
  locator:
    label: "11.6"
confidence: low
review_status: machine_extracted
```

Tests:

- each modality mapping has direct unit coverage;
- prohibitions are not misclassified as permissions;
- descriptive sentences without modality produce no requirement or `unknown` only when explicitly requested;
- exact quote is preserved.

Codex acceptance gate:

- extractor does not infer compliance meaning beyond detected wording;
- exceptions such as `除...外` are preserved in the quote even if not fully parsed.

### P2-06: Requirement JSONL Writer and CLI

Primary owner: Claude/GLM-5.1

Goal:

- wire requirement extraction to `_candidates/requirements/<document_id>.jsonl`.

Suggested files:

- `src/standards_wiki/requirements.py`
- `tools/extract_requirements.py`
- `tests/test_extract_requirements_cli.py`

Expected behavior:

- command: `.venv/bin/python tools/extract_requirements.py <document_id>`;
- reads `_candidates/provisions/<document_id>.jsonl`;
- writes `_candidates/requirements/<document_id>.jsonl`;
- prints a small summary: document ID, requirement count, modality counts, output path.

Tests:

- CLI reads provision JSONL and writes requirement JSONL under `tmp_path`;
- missing provisions file returns non-zero;
- requirement IDs are stable and ordered;
- modality count summary is deterministic.

Codex acceptance gate:

- requirements include modality, evidence, source locator, and review status;
- no LLM call is introduced.

### P2-07: Candidate Validation

Primary owner: Codex, with small implementation help from Claude/GLM-5.1 if needed

Goal:

- add validation that catches broken candidate chains before promotion.

Suggested files:

- `src/standards_wiki/validate.py`
- `tools/validate.py`
- `tests/test_validate.py`

Validation checks:

- candidate metadata has `document_id`, `title`, `review_status`, and provenance fields;
- candidate document exists for each selected `document_id`;
- provision JSONL is valid JSONL;
- provision IDs are unique;
- each provision includes `locator` and exact evidence quote;
- requirement JSONL is valid JSONL;
- each requirement has `modality`, `document_id`, `provision_id`, and evidence quote;
- generated formal pages are not required for draft candidates.

Codex acceptance gate:

- validation is strict enough to catch missing evidence;
- validation output is readable for humans and suitable for CI later.

### P2-08: Review-Safe Provision Page Generator

Primary owner: Claude/GLM-5.1

Goal:

- generate review-safe draft provision pages without pretending they are reviewed canonical pages.

Suggested files:

- `src/standards_wiki/compiler.py`
- `tools/generate_provision_pages.py`
- `tests/test_provision_page_generator.py`

Path decision:

- default output: `_candidates/provision-pages/<document_id>/<provision_id>.md`;
- formal `clauses/` or `provisions/` paths are deferred until review policy is locked.

Expected behavior:

- render provision text;
- embed structured requirement candidates when available;
- include `review_status: machine_extracted`;
- include source locator and warning banner;
- refuse to overwrite manual edits unless explicitly requested.

Codex acceptance gate:

- generated pages are clearly draft/candidate;
- no unreviewed page lands in `standards/`, `clauses/`, `topics/`, or `provisions/` by default.

### P2-09: End-to-End Sample Run

Primary owner: Codex

Goal:

- prove that Phase 2 works end to end on one controlled sample.

Recommended sample strategy:

- prefer a small synthetic Markdown fixture for tests;
- optionally run the real `gb-7258-2017` sample locally, but do not commit generated real outputs unless explicitly approved.

Commands to verify:

```bash
.venv/bin/python tools/compile_document.py gb-7258-2017
.venv/bin/python tools/split_provisions.py gb-7258-2017
.venv/bin/python tools/extract_requirements.py gb-7258-2017
.venv/bin/python tools/validate.py --document-id gb-7258-2017
.venv/bin/python -m pytest -q
```

Done criteria:

- compile, split, extract, and validate work in sequence;
- outputs can be regenerated from candidates;
- all tests pass;
- unstable sample artifacts stay uncommitted unless selected intentionally.

### P2-10: Phase 2 Closeout

Primary owner: Codex

Goal:

- seal Phase 2 only after the candidate pipeline is deterministic and review-safe.

Done criteria:

- tests pass;
- `git diff --check` passes;
- `git status --short` contains only intentional changes;
- docs mention Phase 2 commands and limitations;
- final commit uses Chinese commit format;
- no generated candidate is promoted as reviewed without human approval.

## Recommended Execution Order

1. P2-01 Candidate IO Foundation.
2. P2-02 Document Compiler V1.
3. P2-03 Provision Splitter V1.
4. P2-04 Provision JSONL Writer and CLI.
5. P2-05 Requirement Extractor V1.
6. P2-06 Requirement JSONL Writer and CLI.
7. P2-07 Candidate Validation.
8. P2-08 Review-Safe Provision Page Generator.
9. P2-09 End-to-End Sample Run.
10. P2-10 Phase 2 Closeout.

This order keeps each task independently testable and avoids building requirement extraction before provision IDs are stable.

## First Claude/GLM-5.1 Handoff Prompt

Use this prompt for the first implementation slice:

```text
你是本项目的 Claude/GLM-5.1 实现工程师。当前任务是 P2-01 Candidate IO Foundation。

目标：
- 新增一个轻量候选数据 IO 模块，用于读取 YAML metadata、读取候选 Markdown、拆分 frontmatter/body、读写 JSONL。

允许修改：
- src/standards_wiki/candidates.py
- tests/test_candidates.py

禁止修改：
- PDF/HTML extractor；
- ingest pipeline；
- 任何 raw/、sources/、_candidates/ 真实样例文件；
- pyproject.toml 依赖。

实现要求：
- 不新增第三方依赖；
- 所有文件 IO 支持 Path 或 str；
- JSONL 使用 UTF-8，保持中文可读；
- 缺失输入文件时抛出清晰的 FileNotFoundError；
- 测试全部使用 tmp_path。

请运行：
.venv/bin/python -m pytest tests/test_candidates.py -q

完成后请报告：
- 修改了哪些文件；
- 运行了哪些测试；
- 有哪些假设或需要 Codex 决策的问题。

如果发现允许文件里已有你无法判断来源的未提交改动，请停止并报告，不要覆盖。
```

## Shared Acceptance Checklist

Before any Phase 2 slice is accepted:

- [ ] The change stays inside its task scope.
- [ ] New public behavior has tests.
- [ ] Tests do not depend on network access or real large PDFs.
- [ ] Candidate outputs keep exact source quotes.
- [ ] Review status is explicit.
- [ ] Unknown fields use `unknown` instead of invented values.
- [ ] Generated files are deterministic.
- [ ] `.venv/bin/python -m pytest -q` passes before phase close.

## Open Decisions for Codex

- Whether formal reviewed provision pages should ultimately live under `provisions/` or `clauses/`.
- Whether Phase 2 should add package-level console scripts or keep script files in `tools/`.
- Which real standard sample, if any, should be committed as a small stable fixture.
- Whether `documents/drafts/` should remain after Phase 2 or be replaced by a formal review workflow.
