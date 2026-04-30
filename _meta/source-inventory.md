# Source Inventory

This file defines how to track upstream sources, licenses, retrieval methods and build provenance. Inspired by mature biomedical KG projects such as RTX-KG2.

## Why Source Inventory Exists

Standards and regulations are high-trust domains. The project must know:

- where a document came from;
- whether the source is official;
- when it was retrieved;
- whether redistribution is allowed;
- which version was used;
- whether the derived pages are stale.

## Source Record Schema

```yaml
source_id: cn-gb-public-standards-system
name: 国家标准全文公开系统
source_type: official_website | standards_body | regulator | repository | manual_upload | unknown
jurisdiction: CN
issuer: SAC
url: https://openstd.samr.gov.cn/
access: public | restricted | paid | unknown
license_note: unknown
retrieval_method: manual | crawler | api | upload | unknown
last_checked: YYYY-MM-DD
reliability: high | medium | low
notes: "Official public standard text portal; verify download terms before redistributing raw PDFs."
```

## Document Provenance Schema

Every raw document should have a sidecar metadata record where practical:

```json
{
  "document_id": "gb-7258-2017",
  "source_id": "cn-gb-public-standards-system",
  "source_url": "https://...",
  "source_path": "raw/standards/gb/gb-7258-2017.pdf",
  "retrieved_at": "2026-04-30T00:00:00Z",
  "retrieved_by": "manual",
  "sha256": "...",
  "bytes": 123456,
  "license_note": "unknown",
  "redistribution_note": "verify before publishing raw file"
}
```

## Recommended Files

```text
_meta/source-inventory.md
_meta/source-licenses.md
_meta/build-log.md
_meta/validation-report.md
raw/**/<document_id>.source.json
sources/**/<document_id>.meta.json
```

## Initial Source Categories

| Category | Examples | Notes |
|---|---|---|
| CN standards | 国家标准全文公开系统、行业主管部门网站 | Official status and redistribution need care |
| ISO/IEC/SAE | standards body websites | Often paid/restricted; raw files may not be publishable |
| UNECE/ECE | UNECE regulation pages | Many documents are public; preserve official URL |
| EU rules | EUR-Lex | Good structured metadata and multilingual versions |
| CN policy | MIIT, SAMR, MOT, official gov portals | Webpage capture + URL provenance important |
| interpretations | official Q&A/training documents | Mark as interpretation, not primary rule |
| manual upload | user-provided PDFs | Access/licensing unknown unless specified |

## Licensing Rules

- Do not assume a public URL means raw redistribution is allowed.
- If uncertain, commit metadata and extracted references, but avoid committing restricted raw PDFs to public repos.
- Keep `license_note` and `redistribution_note` explicit.
- Generated summaries and indexes must still cite the original source.

## Build Log

Each batch run should append a build log entry:

```markdown
## [YYYY-MM-DD] build | batch name

- Inputs: N raw files
- Extracted: N source texts
- Generated: N documents, N provision candidates
- Reviewed: N pages
- Warnings: ...
- Tool versions: pymupdf x.y, marker x.y
```

## Validation Report

Validation should report:

- missing source paths;
- missing source URLs;
- unknown document types;
- low confidence pages;
- unreviewed effective dates;
- replacement relationships without citation;
- provisions without locator;
- requirements without evidence quote.

## Minimum Provenance for Formal Pages

A formal `documents/` page should not be marked `reviewed` or `verified` unless it has:

- `source_path` or `source_url`;
- `source_text` if extraction succeeded;
- `source_id` when available;
- `confidence`;
- `review_status`;
- enough citation locator information for key claims.
