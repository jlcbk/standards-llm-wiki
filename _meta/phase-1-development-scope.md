# Phase 1 Development Scope / 第一阶段开发范围

> Updated: 2026-05-05

第一阶段目标：让项目真正具备“持续补充内容入口”。也就是：用户可以提供 PDF 文件或网页链接，程序将其保存、提取、初步结构化，并写入候选区。

## Goal

```text
PDF / URL → raw → sources → _candidates → _jobs
```

第一阶段不追求最终答案质量，而追求导入链路稳定、可追溯、可重复。

## Required Modules

```text
src/standards_wiki/
├── __init__.py
├── ingest.py
├── archive.py
├── classifier.py
├── metadata.py
├── jobs.py
├── extractors/
│   ├── __init__.py
│   ├── pdf.py
│   └── html.py
└── writers/
    ├── __init__.py
    ├── candidate_writer.py
    └── job_writer.py

tools/
├── ingest_pdf.py
└── ingest_url.py

tests/
├── test_archive.py
├── test_classifier.py
├── test_metadata.py
└── test_ingest_smoke.py
```

## Module List

| Module | Purpose |
|---|---|
| `ingest` | Pipeline orchestration |
| `archive` | Save raw PDF/HTML and compute hash |
| `extractors.pdf` | Convert text PDF to Markdown/text |
| `extractors.html` | Fetch webpage and convert content to Markdown |
| `classifier` | Identify document type and standard family |
| `metadata` | Extract candidate metadata fields |
| `writers` | Write candidate Markdown/YAML/JSON |
| `jobs` | Track pending/running/completed/failed jobs |

## Minimal Dependencies

Recommended first implementation:

```text
pymupdf
pymupdf4llm
requests
beautifulsoup4
markdownify
pyyaml
pytest
```

OCR dependencies are intentionally excluded from phase 1.

## Candidate Output Directories

```text
_candidates/documents/
_candidates/metadata/
_candidates/sources/
```

Formal directories such as `documents/`, `standards/`, `provisions/`, `topics/`, and `indexes/` should only receive reviewed content in later phases.

## Definition of Done

Phase 1 is done when these commands work on representative samples:

```bash
python tools/ingest_pdf.py ./samples/example.pdf
python tools/ingest_url.py "https://example.gov.cn/notice.html"
```

And each command produces:

```text
raw/...
sources/...
_candidates/metadata/...
_candidates/documents/...
_jobs/completed/...
```

If extraction fails, it should produce `_jobs/failed/...json` with an actionable error message.

## Sample Inputs Needed

Recommended validation samples:

1. one text-based standard PDF;
2. one scanned/image PDF, if available, to verify `ocr_required: true` detection;
3. one official regulation/notice webpage URL;
4. one webpage with PDF attachment, if available.