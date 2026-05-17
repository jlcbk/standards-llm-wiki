# Standards & Regulations LLM Wiki

面向 AI 问答的异构标准、法规、政策、规则知识库文件架构。整体思路参考 LLM Wiki：**不是简单把 PDF 丢进向量库**，而是把原始资料、转写文本、文档主档案、provision 事实页、跨文档主题、实体、时间线、版本对比和检索索引组织成可追溯、可维护的 Markdown 知识库。

## Project Positioning

本项目定位为：

> **Regulatory Knowledge Compiler** — 标准法规知识编译器。

它不是传统 RAG chatbot。传统弱 RAG 通常是：

```text
PDF → arbitrary chunks → embedding top_k → answer
```

本项目目标是：

```text
heterogeneous raw sources
→ extracted source text
→ reviewed Markdown knowledge layer
→ deterministic indexes / graph / vector artifacts
→ citation-grounded answers
```

多层模型资源主要按能力与稳定性分工：推理能力强且稳定的即时模型用于关键判断与最终审核，稳定的中等能力即时模型用于结构化初抽，不稳定但高能力的后台模型用于异步草稿、交叉检查和评测生成；这些资源主要用于 **build-time 编译、审查、对比和评测生成**，而不是每次 query-time 重新把大量原文塞进上下文。

详细原则见 [`_meta/architecture-principles.md`](_meta/architecture-principles.md)。

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
├── provisions/                  # 通用条款/段落/章节/附件/表格页
├── topics/                      # 跨文档主题页
├── entities/                    # 机构、车辆类型、术语、技术对象、法规概念
├── comparisons/                 # 版本对比、跨体系对比
├── timelines/                   # 发布时间、实施日期、替代关系、过渡期
├── questions/                   # 高频问答沉淀
├── indexes/                     # 给 AI 和程序快速检索用的索引
│
├── eval/                        # QA benchmark and golden answers
├── tools/                       # 后续放 CLI/ingestion/indexing 工具
├── db/                          # 本地派生索引，默认不提交生成物
│
├── src/standards_wiki/          # 第一阶段导入流水线程序包
├── tests/                       # 自动化测试
├── docs/plans/                  # 实施计划
│
├── _drafts/                     # 后台模型生成的草稿，未审核
├── _candidates/                 # 候选元数据、候选文档、候选条款、候选主题、候选引用
├── _reviews/                    # 多模型交叉检查结果、审核记录
├── _jobs/                       # 异步任务描述和运行结果
└── _meta/                       # 规则、prompt、质量清单、工具方案
```

详细字段定义见 [`SCHEMA.md`](SCHEMA.md)。

## 五层设计

### 1. 原始证据层：`raw/`

只存放原始资料，不修改。包括标准 PDF、法规公告、政策网页、官方解读、网页存档等。

### 2. 原文转写层：`sources/`

存放从 PDF/OCR/网页抽取出来的 Markdown 或文本，尽量贴近原文，不做解释性改写。

### 3. 文档主档案层：`documents/`

每个 GB、ISO、ECE、政策、规则、解读都至少有一个 `document` 页面。不要要求所有文档都有统一字段；允许 `unknown` 和稀疏 metadata。

### 4. 知识组织层：`provisions/`、`topics/`、`entities/`、`comparisons/`、`timelines/`

- `provisions/`：可引用的条款/段落/章节/附件/表格；
- `topics/`：跨文档主题页；
- `entities/`：组织、监管机构、车型、术语、技术对象、法规概念；
- `comparisons/`：版本对比、跨体系对比；
- `timelines/`：发布日期、实施日期、替代关系、过渡期。

### 5. AI 检索层：`indexes/`、`questions/`、`eval/`、派生数据库

- `indexes/`：Markdown 结构化索引，适合 AI 直接读；
- `questions/`：高价值复杂问答沉淀，避免重复推理；
- `eval/`：FactQ / RelationQ / ComparisonQ / InferenceQ benchmark；
- `db/`：SQLite FTS5、JSON、graph、vector 等派生索引，不作为 canonical source。

## 推荐外部工具

最小可行工具链：

```text
PDF 文本型：PyMuPDF + pymupdf4llm
PDF 扫描/复杂版式：marker-pdf 或 docling
网页：trafilatura/readability + 手动保存官方 URL
DOCX：python-docx
全文检索：SQLite FTS5
向量检索：LanceDB 或 Qdrant
图谱探索：JSONL graph / Neo4j CSV optional
服务层：FastAPI
任务层：先用 CLI，后续再加 RQ/Celery/Dramatiq
```

## Key Design Documents

- [`_meta/architecture-principles.md`](_meta/architecture-principles.md) — compiler-first 架构原则。
- [`_meta/ingestion-pipeline.md`](_meta/ingestion-pipeline.md) — 入库流水线。
- [`_meta/tooling.md`](_meta/tooling.md) — 外部工具选型。
- [`_meta/parser-strategy.md`](_meta/parser-strategy.md) — GB/ISO/ECE/政策 parser 策略。
- [`_meta/requirement-obligation-schema.md`](_meta/requirement-obligation-schema.md) — requirement / obligation 抽取 schema。
- [`_meta/graph-model.md`](_meta/graph-model.md) — 派生图谱模型。
- [`_meta/evaluation-benchmark.md`](_meta/evaluation-benchmark.md) — 评测集设计。
- [`_meta/source-inventory.md`](_meta/source-inventory.md) — 来源、授权、构建溯源。
- [`_meta/export-formats.md`](_meta/export-formats.md) — SQLite/JSON/graph/RDF 导出方案。
- [`_meta/roadmap.md`](_meta/roadmap.md) — 实施路线图。

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
  能提取主题、实体、引用关系、实施日期、替代关系、适用对象、requirement/obligation。
```

奇怪格式文档至少应做到 Level 1，不要因无法精准拆条款而阻塞入库。

## 第一阶段开发状态

当前最新开发方向是先补“导入流水线”，让项目可以接收 PDF 和网页链接，并产生可追溯的候选资料。

第一阶段目标：

```text
PDF / URL
→ raw/ 原始归档
→ sources/ 正文提取
→ _candidates/ 元数据和候选文档
→ _jobs/ 任务状态记录
```

计划模块：

```text
src/standards_wiki/ingest.py
src/standards_wiki/archive.py
src/standards_wiki/extractors/pdf.py
src/standards_wiki/extractors/html.py
src/standards_wiki/classifier.py
src/standards_wiki/metadata.py
src/standards_wiki/jobs.py
src/standards_wiki/writers/
tools/ingest_pdf.py
tools/ingest_url.py
```

详细说明见：

- [`_meta/ingestion-pipeline.md`](_meta/ingestion-pipeline.md)
- [`_meta/phase-1-development-scope.md`](_meta/phase-1-development-scope.md)
- [`docs/plans/2026-05-05-phase-1-ingestion.md`](docs/plans/2026-05-05-phase-1-ingestion.md)

## 第一阶段样本建议

先用 3–5 个异构样本跑通流程：

1. 一个 GB 标准，例如 GB 7258 或 GB 38031；
2. 一个 ISO 标准，例如 ISO 26262；
3. 一个 ECE regulation，例如 ECE R100；
4. 一个政策通知/公告网页；
5. 一个认证规则或实施细则。

优先建设：

```text
kb ingest-file / ingest-url
kb compile-document
kb validate
kb export sqlite/json
kb search
```

## 第一阶段使用指南

### 安装依赖

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### PDF 入库

```bash
.venv/bin/python tools/ingest_pdf.py ./raw/standards/example.pdf
```

输出：
- `raw/standards/{slug}.pdf` — 原始 PDF 归档
- `sources/standards/{slug}.md` — 提取的 Markdown 文本
- `_candidates/metadata/{slug}.yaml` — 候选元数据
- `_candidates/documents/{slug}.md` — 候选文档页面
- `_jobs/completed/{job_id}.json` — 任务完成记录

### PDF 转 Markdown 引擎

默认 `auto` 策略会对页数较多的文本型标准 PDF 优先尝试 `marker-pdf` 的 `marker_single`，以获得更好的版面、表格和图片保留效果；如果 `marker` 不可用或转换失败，会自动回退到 `pymupdf4llm`。小 PDF、测试样例和疑似扫描件不会默认触发重型 `marker`，避免本地 CPU 长时间运行。

可以用环境变量强制选择：

```bash
STANDARDS_WIKI_PDF_ENGINE=pymupdf4llm .venv/bin/python tools/ingest_pdf.py ./raw/standards/example.pdf
STANDARDS_WIKI_PDF_ENGINE=marker .venv/bin/python tools/ingest_pdf.py ./raw/standards/example.pdf
```

`marker` 输出中的图片会复制到 `sources/standards/{slug}_assets/`，Markdown 图片链接会同步改写。

### 网页入库

```bash
.venv/bin/python tools/ingest_url.py "https://example.gov.cn/notice.html"
```

输出目录同上，`sources/` 下放入 `web/` 子目录。

### OCR 限制

Phase 1 仅支持**文本型 PDF**（可直接提取文字）。如果 PDF 是扫描件或图片型，提取的文字量会很少，系统会自动标记 `ocr_required: true` 并在输出中发出警告。OCR / 高质量 PDF 转 Markdown 后续单独开发。

## 第二阶段使用指南

Phase 2 将 Phase 1 的候选文档继续编译成可审核的 document、provision 和 requirement 候选结果。未审核内容默认保持在 `documents/drafts/` 或 `_candidates/` 下，不会直接进入正式 `provisions/` / `clauses/` 页面。

### 编译候选文档

```bash
.venv/bin/python tools/compile_document.py <document_id>
```

输出：
- `documents/drafts/{document_id}.md` — draft document page

### 拆分候选条款

```bash
.venv/bin/python tools/split_provisions.py <document_id>
```

输出：
- `_candidates/provisions/{document_id}.jsonl` — machine-extracted provision candidates

### 抽取结构化要求

```bash
.venv/bin/python tools/extract_requirements.py <document_id>
```

输出：
- `_candidates/requirements/{document_id}.jsonl` — machine-extracted requirement candidates

### 生成候选条款页

```bash
.venv/bin/python tools/generate_provision_pages.py <document_id>
```

输出：
- `_candidates/provision-pages/{document_id}/*.md` — review-safe candidate provision pages

### 校验候选链路

```bash
.venv/bin/python tools/validate.py --document-id <document_id>
```

校验范围包括 metadata、candidate document、provision JSONL、requirement JSONL、locator 和 evidence quote。

### 验证

```bash
.venv/bin/python -m pytest -q
```

---

后续阶段再补：

```text
Graph export / Neo4j CSV
Vector index
FastAPI QA service
Benchmark eval runner
批处理任务队列
多模型审核工作流
```
