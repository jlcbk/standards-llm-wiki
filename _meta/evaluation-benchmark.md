# Evaluation Benchmark

This project should include a benchmark from the beginning. The goal is not only to retrieve plausible text, but to answer regulatory questions with correct source-backed reasoning.

Inspired by NeuReg and medical benchmark projects that separate factual, relational, comparative and inferential questions.

## Phase 4 MVP Scope

**Phase 4 MVP is deterministic checks, not answer-engine grading.**

The MVP layer validates that the pipeline's structural outputs (documents, provisions, requirements, metadata, topic tags) are correct and complete. It does not score natural-language answers.

Deterministic checks are defined in [`eval/qa/schema.md`](../eval/qa/schema.md), which specifies:

- a JSONL wire format with common fields (`id`, `type`, `category`, `severity`, `expected`, `notes`);
- seven check types covering document existence, provision labels, keyword search, requirement modalities, evidence quotes, metadata fields, and topic tags;
- three severity levels: `info`, `warn`, `error`;
- eight failure categories covering structural and semantic gaps.

Answer-engine grading (rubric scoring over natural-language answers) remains a future milestone, likely aligned with Phase 6.

## Question Types

```text
FactQ          direct factual questions
RelationQ      relation and applicability questions
ComparisonQ    cross-document or version comparison questions
InferenceQ     multi-hop reasoning questions
ExceptionQ     questions involving exclusions or exceptions
DateQ          release/effective/transition/deadline questions
CitationQ      questions requiring exact source citation
```

## Dataset Format

Recommended JSONL format:

```json
{
  "id": "factq-gb-7258-release-date-001",
  "type": "FactQ",
  "question": "GB 7258-2017 的发布日期是什么？",
  "expected_answer": "...",
  "expected_documents": ["gb-7258-2017"],
  "expected_provisions": [],
  "required_citations": [
    {
      "source_text": "sources/standards/gb/gb-7258-2017.md",
      "locator": {"page": "unknown", "label": "title-page"}
    }
  ],
  "must_not_include": [],
  "notes": "Answer must not confuse release date with effective date."
}
```

## Recommended Files

```text
eval/qa/schema.md                          ← deterministic check schema (Phase 4 MVP)
eval/qa/phase3_5_smoke.jsonl               ← Phase 3.5 smoke checks
eval/qa/phase4_smoke.jsonl                 ← Phase 4 extended checks (planned)
eval/qa/gb-7258-2017_factq.jsonl           ← deterministic FactQ-style checks
eval/qa/gb-7258-2017_dateq.jsonl           ← deterministic DateQ-style checks
eval/qa/gb-7258-2017_citationq.jsonl       ← deterministic CitationQ-style checks
eval/rubric.md
eval/golden/README.md
```

## Scoring Dimensions

| Dimension | Description |
|---|---|
| retrieval_recall | Did the system retrieve the required document/provision? |
| citation_accuracy | Are cited document/provision/source locators correct? |
| answer_correctness | Is the final answer substantively correct? |
| version_safety | Does it avoid mixing versions/drafts/replaced documents? |
| exception_handling | Does it preserve exclusions and conditions? |
| uncertainty_handling | Does it say unknown when source support is insufficient? |
| concision | Is the answer appropriately concise? |

## Minimal Rubric

```text
0 = wrong or hallucinated
1 = partially correct but missing key source/condition
2 = correct answer with weak citation or minor omission
3 = correct, cited, version-safe, condition/exception-safe
```

## Seed Questions to Add After First Ingestion

### FactQ

- What is the title of the document?
- What is the release date?
- What is the effective date?
- Which organization issued it?

### RelationQ

- Which provisions apply to vehicle type X?
- Which provisions mention topic Y?
- Which documents cite document Z?

### ComparisonQ

- How does ECE R100 differ from GB 38031 on battery safety?
- What changed between two versions of the same family?

### InferenceQ

- Given vehicle type X and condition Y, which requirements probably apply?
- If a document is replaced by a later version, which source should be cited?

### ExceptionQ

- Which cases are excluded from a requirement?
- Does the requirement apply when condition X is absent?

### DateQ

- Does this rule have a transition period?
- Which deadline applies to a specific obligation?

## Evaluation Workflow

```text
1. Build or update wiki pages.
2. Generate candidate benchmark questions from reviewed sources.
3. Human/strong-model review benchmark items.
4. Run retrieval and answer engine.
5. Score answers with rubric.
6. Write failures to _reviews/eval-failures/ and improve schema/parser/indexes.
```

## Failure Categories

```text
- missed_document
- missed_provision
- missed_requirement
- wrong_version
- unsupported_answer
- citation_missing
- citation_wrong
- exception_dropped
- condition_dropped
- date_confusion
- metadata_mismatch
- topic_mismatch
- overconfident_unknown
```

## Why This Matters

A regulatory knowledge compiler must improve through measurable failures. The benchmark should become the feedback loop that decides which parser, index or review stage needs work.
