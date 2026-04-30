# Parser Strategy

异构文档不能依赖一个统一的 GB 标准解析器。本项目采用 parser hints + fallback parser 的策略。

## Parser Hints

```text
parser_hint:
  - gb_standard
  - iso_standard
  - ece_regulation
  - cn_policy
  - generic_policy
  - certification_rule
  - fallback
```

## Common Parser Contract

每个 parser 尽量输出以下对象，缺失字段写 `unknown`：

```yaml
document:
  document_id: string
  title: string
  document_type: string
  jurisdiction: string
  issuer: string
  language: string
  family: string | unknown
  version: string | unknown
  release_date: YYYY-MM-DD | unknown
  effective_date: YYYY-MM-DD | unknown
  source_path: string
  source_text: string

provisions:
  - provision_id: string
    label: string
    kind: clause | article | paragraph | section | annex | table | requirement | item | unknown
    title: string | unknown
    text: string
    locator: {}

topics: []
entities: []
cited_documents: []
warnings: []
```

## GB Standard Parser

Typical signals:

- `GB`, `GB/T`, `QC/T`, `JT/T` identifiers;
- Chinese chapter labels: `范围`、`规范性引用文件`、`术语和定义`；
- clause labels like `4.1`, `11.6.1`;
- release/effective dates often near title page.

Focus:

- 标准号、发布日期、实施日期、替代关系；
- 规范性引用文件；
- 条款、表格、附录；
- 强制性要求的适用对象、约束动作、例外条件。

## ISO Standard Parser

Typical signals:

- `ISO 26262:2018` or similar;
- English structure: Scope, Normative references, Terms and definitions;
- Part-based family: `ISO 26262-1`, `ISO 26262-2`;
- Annex labels.

Focus:

- standard family and part;
- normative references;
- terms/definitions;
- annexes and requirement wording.

## ECE Regulation Parser

Typical signals:

- `UN Regulation No. 100`, `ECE R100`, `Revision`, `Supplement`;
- paragraphs and annexes;
- approval / type approval language;
- amendment/revision metadata.

Focus:

- regulation number, revision, supplement;
- paragraph labels;
- annexes;
- approval scope;
- relationship to vehicle categories and component systems.

## CN Policy Parser

Typical signals:

- 发文机关、文号、发布日期；
- `通知`、`公告`、`意见`、`办法`、`实施细则`；
- 条、款、项，或 unnumbered sections;
- attachments.

Focus:

- issuer, document number, release date;
- applicable subjects;
- implementation timing;
- obligations, deadlines, reporting requirements;
- linked standards/regulations.

## Fallback Parser

Fallback parser is mandatory.

Minimum output:

- document title candidate;
- source path/source URL;
- language candidate;
- rough sections by headings or page breaks;
- low confidence document page;
- unresolved issues.

Fallback parser must never block ingestion just because the document format is strange.

## Provision Splitting Rules

Prefer stable labels from source:

- Chinese laws/policies: `第一条`、`第二款`、`附件1`；
- GB/ISO: `4.1`, `4.1.1`, `Annex A`；
- ECE: `5.1.1`, `Annex 8`, `Appendix 1`；
- Tables: `Table 1`, `表 1`.

If no stable label exists, use generated paragraph IDs but mark `kind: unknown` and `confidence: low`.

## LLM Use

Allowed:

- classify ambiguous document type;
- suggest topics/entities;
- summarize provisions;
- compare versions;
- review contradictions.

Not allowed without review:

- inventing effective dates;
- inventing replacement relationships;
- making final compliance conclusions;
- silently normalizing conflicting source text.
