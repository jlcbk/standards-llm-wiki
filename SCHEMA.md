# Heterogeneous Standards & Regulations Wiki Schema

## Domain

本仓库不是单一 GB 标准解析器，而是面向 AI 问答的异构标准/法规/政策/规则知识库。覆盖对象包括：

- 中国 GB、GB/T、行业标准、地方标准；
- ISO、IEC、SAE 等国际/组织标准；
- UNECE / ECE regulations、EU regulations/directives 等法规性技术规则；
- 政策通知、公告、部门规章、实施细则、认证规则、官方解读、征求意见稿；
- 网页、PDF、Word、扫描件等多种来源格式。

核心原则：**每个答案都应该能从“主题/实体 → 文档 → provision → 原文来源”完整追溯。**

## Conceptual Model

```text
SourceFile / SourceURL
  → SourceText
  → Document
  → Provision
  → Topic / Entity / Timeline / Comparison / Question
```

### SourceFile / SourceURL

原始证据，不修改。可以是 PDF、DOCX、HTML、扫描件、图片或网页快照。

### SourceText

从原始证据抽取出的 Markdown/Text，尽量贴近原文，不做解释性改写。

### Document

任意正式或候选文件的结构化主页面。GB 标准、ISO 标准、ECE 法规、政策通知、认证规则都属于 `document`。

### Provision

文档中可引用的最小稳定单元。不同文档体系中可能叫：clause、article、paragraph、section、annex、table、requirement、item。

### Topic

跨文档主题，例如座椅、安全带、制动、电池安全、OTA、数据安全、准入认证。

### Entity

机构、术语、车辆类型、技术对象、法规概念。例如 ISO、UNECE、工信部、M1、N1、动力电池、型式认证。

## Directory Semantics

| Directory | Meaning |
|---|---|
| `raw/` | 原始资料，不修改 |
| `sources/` | 抽取后的原文 Markdown/Text |
| `documents/` | 所有异构文档主页面，推荐新内容使用 |
| `standards/` | 标准类文档的兼容/专题视图，可保留 GB/ISO 等标准族入口 |
| `provisions/` | 通用条款/段落/附件/表格页，推荐替代新增 `clauses/` |
| `clauses/` | 旧版条款目录，保留兼容 GB 类标准；新内容优先写入 `provisions/` |
| `topics/` | 跨文档主题页 |
| `entities/` | 机构、车辆类型、术语、技术对象 |
| `timelines/` | 发布时间、实施时间、替代关系、过渡期 |
| `comparisons/` | 版本对比、跨体系对比 |
| `questions/` | 高频问答沉淀 |
| `indexes/` | 面向 AI 与程序检索的结构化索引 |
| `_candidates/` | 机器抽取候选结果，未审核 |
| `_drafts/` | LLM 草稿，未审核 |
| `_reviews/` | 交叉检查、人工/强模型审核记录 |
| `_jobs/` | 批处理任务状态 |
| `_meta/` | 规则、prompt、质量清单、工具方案 |

## Naming Conventions

- 文件名使用小写英文、数字和连字符：`gb-7258-2017.md`、`ece-r100-rev3.md`。
- 正文保留官方写法：`GB 7258-2017`、`UN ECE R100 Rev.3`、`ISO 26262:2018`。
- `document_id` 应稳定、可读、可用于路径。
- 对文档族使用 family 目录：`documents/ece/ece-r100/ece-r100-rev3.md`。
- 对无法规范命名的政策文件，使用机构 + 日期 + 关键词：`cn-miit-2024-xx-ota-notice.md`。

## Page Types

```text
type:
  - document
  - document-family
  - provision
  - topic
  - entity
  - timeline
  - comparison
  - index
  - question
  - source
```

## Document Types

```text
document_type:
  - standard
  - regulation
  - law
  - administrative_rule
  - policy_notice
  - implementation_rule
  - interpretation
  - guideline
  - test_procedure
  - certification_rule
  - draft
  - amendment
  - webpage
  - unknown
```

## Review Status

```text
review_status:
  - raw_imported          # 原始资料已保存
  - extracted             # 已抽取 source text
  - machine_extracted     # 机器抽取 metadata/provisions/topics
  - draft                 # LLM 草稿
  - reviewed              # 强模型或人工审核过
  - verified              # 对照官方来源核验过关键事实
  - deprecated            # 已废弃或被新页面替代
```

## Confidence

```text
confidence:
  - high      # 关键事实来自官方文本且已核验
  - medium    # 来源明确，但仍可能有解析/解释误差
  - low       # OCR/模型候选/格式异常/来源不完整
```

## Common Frontmatter

```yaml
---
title: 页面标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: document | provision | topic | entity | timeline | comparison | index | question | source
tags: []
sources: []
confidence: high | medium | low
review_status: raw_imported | extracted | machine_extracted | draft | reviewed | verified | deprecated
---
```

## Document Frontmatter

```yaml
---
title: GB 7258-2017 机动车运行安全技术条件
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: document
document_id: gb-7258-2017
document_type: standard
jurisdiction: CN
issuer: SAC
language: zh
family: GB 7258
version: "2017"
status: effective | replaced | draft | unknown
release_date: YYYY-MM-DD | unknown
effective_date: YYYY-MM-DD | unknown
transition_period: none | unknown | "说明"
replaces: []
replaced_by: []
source_type: pdf | webpage | docx | scan | image | unknown
source_path: raw/standards/gb-7258-2017.pdf
source_url: unknown
source_text: sources/standards/gb-7258-2017.md
topics: []
entities: []
related_documents: []
tags: [standard, vehicle-safety]
confidence: medium
review_status: machine_extracted
---
```

### ISO Example

```yaml
---
title: ISO 26262:2018 Road vehicles — Functional safety
type: document
document_id: iso-26262-2018
document_type: standard
jurisdiction: international
issuer: ISO
language: en
family: ISO 26262
version: "2018"
status: effective
source_type: pdf
source_path: raw/standards/iso/iso-26262-2018.pdf
source_text: sources/standards/iso/iso-26262-2018.md
topics: [functional-safety, road-vehicles]
entities: [ISO]
confidence: medium
review_status: machine_extracted
---
```

### ECE Example

```yaml
---
title: UN ECE R100 Rev.3 Electric power train requirements
type: document
document_id: ece-r100-rev3
document_type: regulation
jurisdiction: UNECE
issuer: UNECE
language: en
family: ECE R100
version: Rev.3
status: effective
source_type: pdf
source_path: raw/regulations/ece/ece-r100-rev3.pdf
source_text: sources/regulations/ece/ece-r100-rev3.md
topics: [electric-power-train, battery-safety]
entities: [UNECE]
confidence: medium
review_status: machine_extracted
---
```

### Policy Notice Example

```yaml
---
title: 工业和信息化部关于某事项的通知
type: document
document_id: cn-miit-2024-example-notice
document_type: policy_notice
jurisdiction: CN
issuer: MIIT
language: zh
family: unknown
version: unknown
status: unknown
release_date: 2024-XX-XX
effective_date: unknown
source_type: webpage
source_url: https://example.gov.cn/notice
source_path: raw/web/cn-miit-2024-example-notice.html
source_text: sources/web/cn-miit-2024-example-notice.md
topics: []
entities: [MIIT]
confidence: medium
review_status: extracted
---
```

## Provision Frontmatter

```yaml
---
title: ECE R100 Rev.3 Paragraph 5.1.1
type: provision
provision_id: ece-r100-rev3-5-1-1
document_id: ece-r100-rev3
label: "5.1.1"
kind: clause | article | paragraph | section | annex | table | requirement | item | unknown
language: en
topics: [battery-safety]
entities: []
source_document: documents/ece/ece-r100/ece-r100-rev3.md
source_text: sources/regulations/ece/ece-r100-rev3.md
original_source: raw/regulations/ece/ece-r100-rev3.pdf
source_locator:
  page: unknown
  section: "5.1.1"
exact_quote: true
tags: [provision, battery-safety]
confidence: medium
review_status: machine_extracted
---
```

## Topic Frontmatter

```yaml
---
title: 电池安全相关标准法规
type: topic
topic_id: battery-safety
topics: [battery-safety]
related_topics: [electric-power-train, thermal-runaway]
related_documents: []
related_provisions: []
tags: [battery-safety, vehicle-safety]
sources: []
confidence: medium
review_status: draft
---
```

## Entity Frontmatter

```yaml
---
title: UNECE
type: entity
entity_id: unece
entity_type: organization | regulator | standards_body | vehicle_type | term | technical_object | legal_concept
aliases: [United Nations Economic Commission for Europe, UN ECE]
jurisdiction: international
related_documents: []
tags: [organization, regulation]
sources: []
confidence: medium
review_status: draft
---
```

## Timeline Event Schema

用于 `timelines/` 和 `indexes/effective-dates-index.md` 等索引。

```yaml
- event_id: gb-7258-2017-effective
  date: 2018-01-01
  event_type: released | effective | replaced | amended | transition_start | transition_end | unknown
  document_id: gb-7258-2017
  description: "GB 7258-2017 实施"
  source: documents/gb/gb-7258/gb-7258-2017.md
  confidence: high
```

## Citation Schema

任何关键事实建议使用最小引用块：

```yaml
citation:
  source_path: sources/standards/gb/gb-7258-2017.md
  original_source: raw/standards/gb/gb-7258-2017.pdf
  locator:
    page: 12
    label: "4.1"
  quote: "保留原文关键句"
```

## Page Creation Rules

- 每个入库文档至少创建一个 `documents/` 页面。
- 能稳定拆分的条款、段落、附件、表格，创建 `provisions/` 页面或候选页。
- `clauses/` 只作为历史兼容目录；新异构内容优先使用 `provisions/`。
- 一个主题跨 2 个以上文档出现，或是用户高频查询对象，应创建 `topics/` 页面。
- 有明确发布时间、实施日期、替代关系、过渡期时，同步更新 `timelines/` 和 `indexes/`。
- 机器/弱模型输出不得直接进入正式结论；先进入 `_candidates/`、`_drafts/` 或 `_reviews/`。
- 冲突信息不静默合并，写入 `_meta/unresolved-issues.md` 并降低 `confidence`。

## Update Policy

遇到冲突信息时：

1. 优先使用官方发布文本、主管部门公告、标准组织页面；
2. 保留冲突事实，不直接覆盖；
3. 在页面中标注来源、日期、locator 和可信度；
4. 将待确认事项写入 `_meta/unresolved-issues.md`；
5. 必要时将 `confidence` 降为 `low`，`review_status` 降为 `draft` 或 `machine_extracted`。
