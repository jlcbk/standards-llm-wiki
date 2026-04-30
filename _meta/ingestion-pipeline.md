# Ingestion Pipeline

本文件定义异构标准、法规、政策、规则文档从原始资料进入知识库的推荐流水线。

## Pipeline Overview

```text
1. collect
   PDF / DOCX / webpage / scan / image

2. fingerprint
   sha256、文件大小、来源 URL、获取时间

3. classify
   document_type、jurisdiction、issuer、language、source_type、是否扫描件

4. extract
   raw → sources/*.md + sources/*.meta.json

5. parse
   metadata、章节结构、provision candidates、引用文档、日期、适用对象

6. normalize
   统一 document_id、路径、frontmatter、locator、citation

7. generate
   documents/ 页面、provisions/ 候选、topics/entities 候选、indexes 草稿

8. review
   弱模型/规则候选 → 强模型/人工审核 → formal pages

9. index
   Markdown → SQLite FTS5 / vector DB / topic indexes

10. answer
   用户问题 → hybrid retrieval → cited answer
```

## Stage 1: Collect

输入可以来自：

- 本地文件：`raw/standards/gb/gb-7258-2017.pdf`
- 官方网页：保存 HTML 或 Markdown 快照到 `raw/web/`
- Word：`raw/rules/...docx`
- 扫描件/图片：`raw/.../scan.pdf` 或 `raw/.../*.png`

必须记录：

```yaml
source_url: unknown | https://...
retrieved_at: YYYY-MM-DDTHH:MM:SSZ
retrieved_by: manual | script | crawler
license_or_access_note: unknown
```

## Stage 2: Fingerprint

每个原始文件生成 sidecar metadata：

```json
{
  "source_path": "raw/standards/gb/gb-7258-2017.pdf",
  "sha256": "...",
  "bytes": 123456,
  "retrieved_at": "2026-04-30T00:00:00Z",
  "source_url": "unknown"
}
```

用途：

- 防止重复导入；
- 支持重新抽取；
- 支持证据追溯。

## Stage 3: Classify

分类器输出建议：

```yaml
document_type: standard | regulation | policy_notice | certification_rule | unknown
jurisdiction: CN | UNECE | EU | international | unknown
issuer: SAC | ISO | UNECE | MIIT | unknown
language: zh | en | multi | unknown
source_type: pdf | webpage | docx | scan | image | unknown
is_scanned: true | false | unknown
parser_hint: gb_standard | iso_standard | ece_regulation | cn_policy | generic | fallback
```

分类不要阻塞导入；不确定就用 `unknown` + `fallback`。

## Stage 4: Extract

### Default Decision Tree

```text
Has official URL?
  → fetch webpage/PDF and save raw copy

PDF text layer exists and layout simple?
  → PyMuPDF / pymupdf4llm

PDF scanned or complex tables/annexes?
  → marker-pdf or docling OCR

DOCX?
  → python-docx

HTML webpage?
  → trafilatura/readability + preserve URL and raw HTML

Still fails?
  → save raw only, create Level 1 document with low confidence
```

### Output

```text
sources/<category>/<family>/<document_id>.md
sources/<category>/<family>/<document_id>.meta.json
```

`source .meta.json` 示例：

```json
{
  "document_id": "ece-r100-rev3",
  "source_path": "raw/regulations/ece/ece-r100-rev3.pdf",
  "source_text": "sources/regulations/ece/ece-r100-rev3.md",
  "extractor": "pymupdf4llm",
  "pages": 128,
  "quality": "medium",
  "warnings": ["tables require review"],
  "extracted_at": "2026-04-30T00:00:00Z"
}
```

## Stage 5: Parse

解析器采用插件式，不要求所有文档统一格式：

```text
parsers/
├── gb_standard
├── iso_standard
├── ece_regulation
├── cn_policy
├── generic_policy
└── fallback
```

### Parser Responsibilities

- 提取 metadata：标题、编号、issuer、发布日期、实施日期、版本、替代关系；
- 提取 outline：章节、条款、附件、表格；
- 生成 provision candidates；
- 生成 topic/entity candidates；
- 标记不确定项。

### Parser Output Goes To Candidates First

```text
_candidates/metadata/<document_id>.json
_candidates/provisions/<document_id>.jsonl
_candidates/topic-tags/<document_id>.json
_candidates/cited-documents/<document_id>.json
```

不要让弱模型或规则解析结果直接成为 verified 结论。

## Stage 6: Normalize

规范化内容：

- `document_id`：稳定、可读、路径安全；
- `provision_id`：`<document_id>-<label-normalized>`；
- 日期：ISO `YYYY-MM-DD`，无法确定写 `unknown`；
- locator：页码、章节号、原文 label 尽量保留；
- source path：必须能追溯到 `raw/` 和 `sources/`。

## Stage 7: Generate Pages

最低入库输出：

```text
documents/<jurisdiction-or-family>/<family>/<document_id>.md
```

可选增强输出：

```text
provisions/<document_id>/<provision_id>.md
topics/<topic_id>.md
entities/<entity_id>.md
timelines/<family-or-topic>.md
comparisons/<a>-vs-<b>.md
indexes/*.md
```

## Stage 8: Review

推荐 review gate：

```text
metadata objective fields:
  规则抽取 + 弱模型 + 强模型/人工核验

provision split:
  规则拆分 + spot check

topic/entity tags:
  候选可低成本生成，但 formal topic 页需审核

legal/regulatory conclusion:
  必须强模型或人工审核，并引用原文
```

冲突处理：

- 不静默覆盖；
- 写入 `_reviews/contradiction-checks/`；
- 关键问题同步 `_meta/unresolved-issues.md`；
- 降低 `confidence`。

## Stage 9: Index

Markdown 仓库是 canonical source，索引是可重建派生物。

推荐派生索引：

```text
SQLite FTS5:
  documents, provisions, topics, entities

Vector DB:
  provision chunks, topic summaries, question pages

Markdown indexes:
  indexes/documents-index.md
  indexes/topic-to-documents-index.md
  indexes/effective-dates-index.md
  indexes/replaced-documents-index.md
  indexes/cited-documents-index.md
```

## MVP CLI

后续工具建议提供以下命令：

```bash
kb ingest raw/standards/gb/gb-7258-2017.pdf
kb ingest-url https://example.gov.cn/notice.html
kb parse gb-7258-2017
kb review gb-7258-2017
kb index
kb search "电池安全 ECE GB"
kb ask "ECE R100 和 GB 38031 对电池安全有什么差异？"
```

## Acceptance Criteria for Ingestion

一个文档完成最小入库需要满足：

- [ ] 原始来源保存在 `raw/` 或记录了可信 URL；
- [ ] 生成 `sources/*.md` 或明确说明无法抽取；
- [ ] 创建 `documents/*.md`；
- [ ] frontmatter 包含 `document_id`、`document_type`、`source_path/source_url`、`confidence`、`review_status`；
- [ ] 不确定字段为 `unknown`，而不是模型猜测；
- [ ] 更新 `index.md` 和 `log.md`。
