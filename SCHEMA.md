# Standards LLM Wiki Schema

## Domain

国家标准、行业标准、法规公告、官方解释与实施规则，重点面向车辆安全、检测、认证、合规等场景。

## Conventions

- 文件名使用小写英文、数字和连字符，例如 `gb-7258-2017.md`。
- 标准号统一写法：正文中使用 `GB 7258-2017`，文件名使用 `gb-7258-2017`。
- 每个知识页必须有 YAML frontmatter。
- 重要事实必须保留来源路径，能追溯到 `raw/` 或 `sources/`。
- 使用 `[[wikilinks]]` 连接标准、主题、条款、时间线和对比页面。
- 不在 `raw/` 中修改原始文件；修正和解释写入知识页。
- 每次新增或更新页面后更新 `index.md` 和 `log.md`。

## Page Types

- `standard`：单个标准某一版本的主页面。
- `standard-family`：某个标准族的入口或版本总览，例如 GB 7258。
- `clause`：条款级知识页。
- `topic`：跨标准主题页，例如座椅、制动、灯光。
- `comparison`：版本对比或标准间对比。
- `timeline`：发布、实施、替代、过渡期时间线。
- `entity`：机构、车辆类型、术语等实体。
- `index`：AI 检索索引。
- `question`：高价值问答沉淀。

## Common Frontmatter

```yaml
---
title: 页面标题
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: standard | clause | topic | comparison | timeline | entity | index | question
tags: []
sources: []
confidence: high | medium | low
status: draft | reviewed | verified
---
```

## Standard Page Frontmatter

```yaml
---
title: GB 7258-2017 机动车运行安全技术条件
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: standard
standard_id: GB 7258-2017
standard_family: GB 7258
version_year: 2017
status: effective | replaced | draft | unknown
release_date: YYYY-MM-DD | unknown
effective_date: YYYY-MM-DD | unknown
transition_period: none | unknown | "说明"
replaces: []
replaced_by: []
source: raw/standards/gb-7258-2017.pdf
source_text: sources/standards/gb-7258-2017.md
tags: [national-standard, vehicle-safety]
confidence: medium
---
```

## Clause Page Frontmatter

```yaml
---
title: GB 7258-2017 第 11.6 条 座椅相关要求
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: clause
standard_id: GB 7258-2017
clause_id: "11.6"
topics: [seats]
source: standards/gb/gb-7258/gb-7258-2017.md
original_source: raw/standards/gb-7258-2017.pdf
tags: [clause, seats, vehicle-safety]
confidence: medium
---
```

## Topic Page Frontmatter

```yaml
---
title: 座椅相关标准
type: topic
topics: [seats]
tags: [seats, vehicle-safety, inspection]
sources: []
confidence: medium
---
```

## Recommended Tags

### 标准类别

- `national-standard`
- `recommended-national-standard`
- `industry-standard`
- `regulation`
- `official-interpretation`

### 车辆与合规主题

- `vehicle-safety`
- `vehicle-inspection`
- `certification`
- `registration`
- `compliance`

### 部件/系统

- `seats`
- `seat-belts`
- `braking`
- `lighting`
- `dimensions`
- `new-energy-vehicle`
- `school-bus`

### 元信息

- `effective-date`
- `transition-period`
- `replacement`
- `comparison`
- `faq`

## Page Creation Rules

- 标准文件入库时必须创建或更新 `standards/` 页面。
- 一个主题跨 2 个以上标准出现，或是用户高频查询对象，应创建 `topics/` 页面。
- 关键强制性条款、易误解条款、跨主题引用条款，应创建 `clauses/` 页面。
- 同一标准存在多个版本时，应创建 `changelog.md` 和必要的 `comparisons/` 页面。
- 有明确发布日期、实施日期、过渡期、替代关系时，应同步更新 `timelines/` 和 `indexes/`。

## Update Policy

遇到冲突信息时：

1. 优先使用官方发布文本、国家标准全文公开系统、主管部门公告；
2. 保留冲突事实，不直接覆盖；
3. 在页面中标注来源、日期和可信度；
4. 将待确认事项写入 `_meta/unresolved-issues.md`；
5. 必要时将 `confidence` 降为 `low`。
