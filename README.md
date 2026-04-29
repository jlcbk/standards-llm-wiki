# Standards LLM Wiki

面向 AI 问答的标准法规知识库文件架构设计。整体思路参考 Karpathy / LLM Wiki：不是简单把 PDF 丢进向量库，而是将原始资料、转写文本、标准主档案、条款事实、跨标准主题、版本对比、时间线与检索索引组织成可追溯、可维护的 Markdown 知识库。

## 目标场景

该知识库供 AI 查阅并回答人类问题，例如：

- “涉及到座椅的都有哪些标准？”
- “GB 7258 最新版标准实施日期是什么时候，有没有过渡期？”
- “新版 GB 7258 相比于旧版，更新了哪些地方？”

核心原则：

> 每个答案都应该能从“主题 → 标准 → 条款 → 原文来源”完整追溯。

## 推荐文件结构

```text
standards-wiki/
├── README.md
├── SCHEMA.md
├── index.md
├── log.md
│
├── raw/                         # 原始文件，不修改
│   ├── standards/               # PDF、Word、扫描件等原始标准
│   ├── regulations/             # 法规、公告、通知、征求意见稿
│   ├── interpretations/         # 官方解读、问答、宣贯材料
│   └── web/                     # 网页抓取原文
│
├── sources/                     # 原始文件转写后的 Markdown/Text
│   ├── standards/
│   ├── regulations/
│   ├── interpretations/
│   └── web/
│
├── standards/                   # 单个标准的主知识页
│   ├── gb/
│   │   ├── gb-7258/
│   │   │   ├── gb-7258-2017.md
│   │   │   ├── gb-7258-202x.md
│   │   │   ├── current.md
│   │   │   └── changelog.md
│   │   └── gb-38900/
│   │       ├── gb-38900-2020.md
│   │       └── current.md
│   ├── gb-t/
│   ├── qc-t/
│   ├── jt-t/
│   └── local/
│
├── clauses/                     # 条款级知识页，适合精确问答
│   ├── gb-7258-2017/
│   │   ├── clause-4-1.md
│   │   ├── clause-7-2.md
│   │   └── clause-11-6-seat.md
│   └── gb-38900-2020/
│
├── topics/                      # 跨标准主题页
│   ├── seats.md
│   ├── seat-belts.md
│   ├── braking-system.md
│   ├── lighting-system.md
│   ├── vehicle-dimensions.md
│   ├── school-bus.md
│   ├── new-energy-vehicle.md
│   └── inspection-items.md
│
├── comparisons/                 # 标准对比、版本对比
│   ├── gb-7258-2012-vs-2017.md
│   ├── gb-7258-2017-vs-202x.md
│   ├── gb-7258-vs-gb-38900.md
│   └── seat-requirements-across-standards.md
│
├── timelines/                   # 时间线、实施日期、过渡期
│   ├── gb-7258.md
│   ├── gb-38900.md
│   └── vehicle-safety-standards.md
│
├── entities/                    # 实体、术语、对象
│   ├── organizations/
│   ├── vehicle-types/
│   └── terms/
│
├── questions/                   # 高价值问答沉淀
│   ├── standards-related-to-seats.md
│   ├── gb-7258-latest-effective-date.md
│   └── gb-7258-version-differences.md
│
├── indexes/                     # 给 AI 快速检索用的索引
│   ├── standards-index.md
│   ├── topics-index.md
│   ├── clauses-index.md
│   ├── effective-dates-index.md
│   ├── transition-periods-index.md
│   ├── replaced-standards-index.md
│   ├── cited-standards-index.md
│   └── topic-to-standards-index.md
│
└── _meta/
    ├── extraction-prompts.md
    ├── extraction-rules.md
    ├── naming-conventions.md
    ├── quality-checklist.md
    └── unresolved-issues.md
```

## 五层设计

### 1. 原始证据层：`raw/`

只存放原始资料，不修改。包括标准 PDF、法规公告、官方解读、网页存档等。

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
source_file: raw/standards/gb-7258-2017.pdf
standard_id: GB 7258-2017
title: 机动车运行安全技术条件
extracted_at: 2026-04-29
extractor: docling | marker | pdftotext | ocr
quality: high | medium | low
---
```

### 3. 标准主档案层：`standards/`

每个标准、每个版本都有独立 Markdown 主页面。

例如：

```text
standards/gb/gb-7258/
├── gb-7258-2017.md
├── gb-7258-202x.md
├── current.md
└── changelog.md
```

- `gb-7258-2017.md`：该版本标准结构化档案；
- `current.md`：当前有效版本入口；
- `changelog.md`：版本演进历史。

### 4. 知识组织层：`clauses/`、`topics/`、`comparisons/`、`timelines/`

- `clauses/`：条款级事实页，回答精确问题；
- `topics/`：跨标准主题页，回答“某个主题涉及哪些标准”；
- `comparisons/`：版本对比、标准对比；
- `timelines/`：发布日期、实施日期、替代关系、过渡期。

### 5. AI 检索层：`indexes/`、`questions/`

- `indexes/`：为 AI 快速定位事实准备的结构化索引；
- `questions/`：高价值复杂问答沉淀，避免重复推理。

## 三类典型问题的查询路径

### “涉及到座椅的都有哪些标准？”

```text
indexes/topic-to-standards-index.md
→ topics/seats.md
→ clauses/*seat*.md
→ standards/*/current.md
```

### “GB 7258 最新版标准实施日期是什么时候，有没有过渡期？”

```text
standards/gb/gb-7258/current.md
→ timelines/gb-7258.md
→ indexes/effective-dates-index.md
→ indexes/transition-periods-index.md
```

### “新版 GB 7258 相比旧版更新了哪些地方？”

```text
standards/gb/gb-7258/changelog.md
→ comparisons/gb-7258-2017-vs-202x.md
→ clauses/gb-7258-*/
```

## 第一阶段建议

先不要一次性导入大量文件。建议用 2-3 个代表性标准跑通流程：

1. GB 7258-2017；
2. GB 38900-2020；
3. 一个与座椅、制动或安全带相关的引用标准。

优先建设：

```text
standards/      单个标准主页面
topics/         跨标准主题页面
indexes/        面向 AI 检索的索引页面
```

第二阶段再补：

```text
clauses/        条款级页面
comparisons/    版本对比
timelines/      实施日期和过渡期
questions/      高频问答沉淀
```
