# Standards & Regulations Wiki Index

> 面向 AI 问答的异构标准、法规、政策、规则知识库目录。
> Last updated: 2026-04-30 | Total pages: 0

## Core Design Documents

- [SCHEMA.md](SCHEMA.md) - Document / Provision / Topic / Entity / Requirement 等核心 schema。
- [_meta/architecture-principles.md](_meta/architecture-principles.md) - compiler-first 架构原则，避免 naive RAG。
- [_meta/ingestion-pipeline.md](_meta/ingestion-pipeline.md) - 原始文件到知识页的入库流水线。
- [_meta/tooling.md](_meta/tooling.md) - PDF、OCR、检索、服务层工具选型。
- [_meta/parser-strategy.md](_meta/parser-strategy.md) - GB、ISO、ECE、政策等异构 parser 策略。
- [_meta/requirement-obligation-schema.md](_meta/requirement-obligation-schema.md) - obligation / requirement 抽取模型。
- [_meta/graph-model.md](_meta/graph-model.md) - 派生图谱节点、边和查询模式。
- [_meta/evaluation-benchmark.md](_meta/evaluation-benchmark.md) - FactQ / RelationQ / ComparisonQ / InferenceQ benchmark 设计。
- [_meta/source-inventory.md](_meta/source-inventory.md) - 来源、授权、构建溯源规范。
- [_meta/export-formats.md](_meta/export-formats.md) - SQLite、JSON、graph、RDF 等导出格式。
- [_meta/roadmap.md](_meta/roadmap.md) - 分阶段实施路线图。
- [_meta/model-strategy.md](_meta/model-strategy.md) - 多模型分层与审核策略。

## Documents

暂无正式文档页。所有新入库文档优先进入 `documents/`。

## Standards Compatibility Views

暂无。`standards/` 保留给标准族视图和历史兼容结构。

## Provisions

暂无。新增条款/段落/附件/表格页优先进入 `provisions/`。

## Clauses

暂无。`clauses/` 保留给旧版 GB 条款结构。

## Requirements

暂无。机器抽取结果先进入 `_candidates/requirements/`，审核后写入 provision 页或导出索引。

## Topics

暂无。

## Entities

暂无。

## Comparisons

暂无。

## Timelines

暂无。

## Questions

暂无。

## Evaluation

- [Evaluation Rubric](eval/rubric.md)
- [Golden Answers](eval/golden/README.md)

## Indexes

- [Documents Index](indexes/documents-index.md)
- [Provisions Index](indexes/provisions-index.md)
- [Topic to Documents Index](indexes/topic-to-documents-index.md)
- [Cited Documents Index](indexes/cited-documents-index.md)
- [Standards Index](indexes/standards-index.md)
- [Effective Dates Index](indexes/effective-dates-index.md)
- [Transition Periods Index](indexes/transition-periods-index.md)
- [Replaced Standards Index](indexes/replaced-standards-index.md)
