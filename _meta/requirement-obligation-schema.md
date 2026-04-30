# Requirement & Obligation Schema

Regulatory answers often depend on obligations, permissions, prohibitions and exceptions. This file defines a structured schema for extracting machine-usable requirements from provisions.

Inspired by Regulation-as-Code projects such as OpenRegs / ADGM, but adapted for heterogeneous standards, technical regulations, policies and certification rules.

## Why This Matters

Naive RAG can retrieve a relevant paragraph but still miss:

- who the requirement applies to;
- whether it is mandatory or recommended;
- the condition under which it applies;
- exceptions and exclusions;
- deadlines and transition periods;
- evidence needed for compliance.

Requirement extraction makes these fields explicit.

## Requirement Object

```yaml
requirement_id: gb-7258-2017-11-6-r1
source_provision: provisions/gb-7258-2017/gb-7258-2017-11-6.md
document_id: gb-7258-2017
provision_id: gb-7258-2017-11-6

modality: must | must_not | should | may | define | unknown
subject:
  - entity_id: vehicle-passenger-car
    text: 乘用车
action: install | meet | prohibit | submit | report | test | define | unknown
object:
  - entity_id: seat
    text: 座椅
condition: unknown
exception: unknown
deadline: unknown
transition: unknown
compliance_risk: unknown
evidence:
  quote: "原文关键句"
  source_text: sources/standards/gb/gb-7258-2017.md
  original_source: raw/standards/gb/gb-7258-2017.pdf
  locator:
    page: unknown
    label: "11.6"
confidence: medium
review_status: machine_extracted
```

## Modality Vocabulary

| Modality | Meaning | Chinese Signals | English Signals |
|---|---|---|---|
| `must` | mandatory obligation | 必须、应、应当、须 | shall, must, is required to |
| `must_not` | prohibition | 不得、禁止、不应 | shall not, must not, prohibited |
| `should` | recommendation | 宜、建议 | should, recommended |
| `may` | permission | 可、可以 | may, can, permitted |
| `define` | definition | 是指、定义为 | means, refers to, is defined as |
| `unknown` | unclear | - | - |

For Chinese standards, `应` is often normative and should usually map to `must`, but mark uncertain cases for review.

## Requirement Types

```text
requirement_type:
  - technical_requirement
  - procedural_requirement
  - documentation_requirement
  - reporting_requirement
  - testing_requirement
  - certification_requirement
  - prohibition
  - definition
  - scope_rule
  - exception_rule
  - transition_rule
  - unknown
```

## Extraction Steps

1. Read the full provision, not an arbitrary chunk.
2. Identify modality signals.
3. Identify subject: who/what must comply.
4. Identify action and object.
5. Identify condition: when the requirement applies.
6. Identify exception: when it does not apply.
7. Identify deadline or transition period if present.
8. Attach exact quote and locator.
9. Mark confidence and review status.

## Examples

### Mandatory Technical Requirement

```yaml
modality: must
requirement_type: technical_requirement
subject: [{text: "机动车"}]
action: meet
object: [{text: "运行安全技术条件"}]
condition: "在道路上行驶时"
exception: unknown
```

### Prohibition

```yaml
modality: must_not
requirement_type: prohibition
subject: [{text: "车辆制造商"}]
action: provide
object: [{text: "虚假认证材料"}]
condition: "申请认证时"
exception: unknown
```

### Policy Deadline

```yaml
modality: must
requirement_type: reporting_requirement
subject: [{text: "相关企业"}]
action: submit
object: [{text: "整改报告"}]
deadline: "2026-06-30"
condition: "被纳入专项检查范围"
```

## Candidate Storage

Machine-extracted requirements should first go to:

```text
_candidates/requirements/<document_id>.jsonl
```

Formal reviewed requirement blocks can then be embedded in provision pages or exported to derived indexes.

## Quality Rules

- Never infer a mandatory obligation from a descriptive sentence.
- Never drop exceptions such as “除……外” or “不适用于……”.
- Do not normalize `应`, `宜`, `可` into the same modality.
- Do not answer compliance questions from `unknown` modality without review.
- Every requirement must include an evidence quote and source locator.
- If a requirement spans multiple provisions, record all supporting provisions.

## Suggested Provision Page Section

```markdown
## Structured Requirements

```yaml
- requirement_id: ...
  modality: must
  subject: []
  action: unknown
  object: unknown
  condition: unknown
  exception: unknown
  evidence:
    quote: "..."
```
```
