# Standards & Regulations LLM Wiki

面向 AI 问答的异构标准、法规、政策、规则知识库文件架构。整体思路参考 LLM Wiki：**不是简单把 PDF 丢进向量库**，而是把原始资料、转写文本、文档主档案、provision 事实页、跨文档主题、实体、时间线、版本对比和检索索引组织成可追溯、可维护的 Markdown 知识库。

## 目标场景

该知识库供 AI 查阅并回答人类问题，例如：

- “涉及到座椅的都有哪些 GB / ISO / ECE 标准？”
- “GB 7258 最新版实施日期是什么时候，有没有过渡期？”
- “ECE R100 和 GB 38031 对电池安全的要求有什么差异？”
- “某个工信部政策通知什么时候发布、适用对象是什么？”
- “哪些规则涉及 OTA、软件升级、数据安全？”

核心原则：

> 每个答案都应该能从“主题/实体 → 文档 → provision → 原文来源”完整追溯。

## 知识库不是 GB 专用解析器

本项目需要同时容纳：

- 中国 GB、GB/T、行业标准、地方标准；
- ISO、IEC、SAE 等国际/组织标准；
- UNECE / ECE regulations、EU regulations/directives；
- 政策通知、公告、部门规章、实施细则、认证规则、官方解读、征求意见稿；
- PDF、Word、网页、扫描件、图片等多种来源。

因此核心抽象从“standard + clause”升级为：

```text
SourceFile / SourceURL
  → SourceText
  → Document
  → Provision
  → Topic / Entity / Timeline / Comparison / Question
```

## 推荐文件结构

```text
standards-llm-wiki/
├── README.md
├── SCHEMA.md
├── index.md
├── log.md
│
├── raw/                         # 原始文件，不修改
│   ├── standards/               # GB/ISO/IEC/SAE 等标准原件
│   ├── regulations/             # ECE/EU/法规性技术规则
│   ├── policies/                # 政策通知、公告、部门文件
│   ├── rules/                   # 实施细则、认证规则、测试规程
│   ├── interpretations/         # 官方解读、问答、宣贯材料
│   └── web/                     # 网页抓取原文或快照
│
├── sources/                     # 原始文件转写后的 Markdown/Text
│   ├── standards/
│   ├── regulations/
│   ├── policies/
│   ├── rules/
│   ├── interpretations/
│   └── web/
│
├── documents/                   # 所有正式文档主页面，推荐新内容使用
│   ├── gb/
│   ├── gb-t/
│   ├── iso/
│   ├── iec/
│   ├── sae/
│   ├── ece/
│   ├── eu/
│   ├── cn-policy/
│   ├── certification/
│   └── unknown/
│
├── standards/                   # 标准类文档兼容/专题视图，可保留 GB family 结构
├── provisions/                  # 通用条款/段落/章节/附件/表格页
├── clauses/                     # 旧版 GB clause 兼容目录；新增异构内容优先 provisions/
├── topics/                      # 跨文档主题页
├── entities/                    # 机构、车辆类型、术语、技术对象、法规概念
├── comparisons/                 # 版本对比、跨体系对比
├── timelines/                   # 发布时间、实施日期、替代关系、过渡期
├── questions/                   # 高频问答沉淀
├── indexes/                     # 给 AI 和程序快速检索用的索引
│
├── tools/                       # 后续放 CLI/ingestion/indexing 工具
├── db/                          # 本地派生索引，默认不提交
│
├── _drafts/                     # 弱模型/慢模型生成的草稿，未审核
├── _candidates/                 # 候选条款、候选主题、候选引用、候选元数据
├── _reviews/                    # 多模型交叉检查结果、审核记录
├── _jobs/                       # 异步任务描述和运行结果
└── _meta/                       # 规则、prompt、质量清单、工具方案
```

详细字段定义见 [`SCHEMA.md`](SCHEMA.md)。

## 五层设计

### 1. 原始证据层：`raw/`

只存放原始资料，不修改。包括标准 PDF、法规公告、政策网页、官方解读、网页存档等。

用途：

- 事实追溯；
- 重新抽取；
- 人工核验；
- 避免 LLM 摘要错误后无源可查。

### 2. 原文转写层：`sources/`

存放从 PDF/OCR/网页抽取出来的 Markdown 或文本，尽量贴近原文，不做解释性改写。

推荐 frontmatter：

```yaml
---
source_file: raw/standards/gb/gb-7258-2017.pdf
source_url: unknown
document_id: gb-7258-2017
title: 机动车运行安全技术条件
extracted_at: 2026-04-30
extractor: pymupdf | pymupdf4llm | marker-pdf | docling | trafilatura | python-docx | manual
quality: high | medium | low
---
```

### 3. 文档主档案层：`documents/`

每个 GB、ISO、ECE、政策、规则、解读都至少有一个 `document` 页面。不要要求所有文档都有统一字段；允许 `unknown` 和稀疏 metadata。

### 4. 知识组织层：`provisions/`、`topics/`、`entities/`、`comparisons/`、`timelines/`

- `provisions/`：可引用的条款/段落/章节/附件/表格；
- `topics/`：跨文档主题页；
- `entities/`：组织、监管机构、车型、术语、技术对象、法规概念；
- `comparisons/`：版本对比、跨体系对比；
- `timelines/`：发布日期、实施日期、替代关系、过渡期。

### 5. AI 检索层：`indexes/`、`questions/`、派生数据库

- `indexes/`：Markdown 结构化索引，适合 AI 直接读；
- `questions/`：高价值复杂问答沉淀，避免重复推理；
- `db/`：SQLite FTS5、LanceDB/Qdrant 等派生索引，不作为 canonical source。

## 推荐外部工具

最小可行工具链：

```text
PDF 文本型：PyMuPDF + pymupdf4llm
PDF 扫描/复杂版式：marker-pdf 或 docling
网页：trafilatura/readability + 手动保存官方 URL
DOCX：python-docx
全文检索：SQLite FTS5
向量检索：LanceDB 或 Qdrant
服务层：FastAPI
任务层：先用 CLI，后续再加 RQ/Celery/Dramatiq
```

详细流水线见 [`_meta/ingestion-pipeline.md`](_meta/ingestion-pipeline.md) 和 [`_meta/tooling.md`](_meta/tooling.md)。

## 三类典型问题的查询路径

### “涉及到座椅的都有哪些标准/法规？”

```text
indexes/topic-to-documents-index.md
→ topics/seats.md
→ provisions/*seat*.md
→ documents/*/current 或 document page
→ raw/sources 原文
```

### “某文档最新版实施日期是什么时候，有没有过渡期？”

```text
documents/<family>/current.md
→ timelines/<family>.md
→ indexes/effective-dates-index.md
→ indexes/transition-periods-index.md
→ source quote
```

### “ECE R100 和 GB 38031 有什么差异？”

```text
comparisons/ece-r100-vs-gb-38031.md
→ topics/battery-safety.md
→ provisions/ece-r100-*/ + provisions/gb-38031-*/
→ documents/ece/... + documents/gb/...
```

## 入库成熟度分级

```text
Level 1: Document page
  只保存原文、抽取文本、基本 metadata。

Level 2: Provision split
  能拆章节/条款/段落/附件，并保留 locator。

Level 3: Semantic enrichment
  能提取主题、实体、引用关系、实施日期、替代关系、适用对象。
```

奇怪格式文档至少应做到 Level 1，不要因无法精准拆条款而阻塞入库。

## 第一阶段建议

先用 3–5 个异构样本跑通流程：

1. 一个 GB 标准，例如 GB 7258 或 GB 38031；
2. 一个 ISO 标准，例如 ISO 26262；
3. 一个 ECE regulation，例如 ECE R100；
4. 一个政策通知/公告网页；
5. 一个认证规则或实施细则。

优先建设：

```text
SCHEMA.md
_meta/ingestion-pipeline.md
_meta/tooling.md
documents/
provisions/
indexes/topic-to-documents-index.md
```

第二阶段再补：

```text
FastAPI QA service
SQLite FTS5 indexer
LanceDB/Qdrant vector indexer
批处理任务队列
多模型审核工作流
```
