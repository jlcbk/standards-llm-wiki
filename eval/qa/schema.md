# Deterministic Check JSONL Schema

Version: 1

This document defines the JSONL wire format for deterministic benchmark checks used by the eval runner (`src/standards_wiki/eval.py`).

## Common Fields

Every check line is a JSON object with these required fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique check identifier. Convention: `{type_snake}-{document_id}-{sequence}` |
| `type` | string | Check type. One of the seven types listed below |
| `category` | string | Failure category when check fails. One of the values listed below |
| `severity` | string | `info`, `warn`, or `error` |
| `expected` | any | Expected value. Type and shape depend on `type` |
| `notes` | string | Human-readable explanation of what this check validates |

Optional fields:

| Field | Type | Description |
|-------|------|-------------|
| `document_id` | string | Document scope for this check. Inferred from `expected` when absent |

### Severity Levels

| Level | Meaning |
|-------|---------|
| `info` | Nice-to-have. Failure is informational, does not block promotion |
| `warn` | Quality concern. Should be reviewed before promotion |
| `error` | Must fix. Failure blocks promotion or indicates data loss |

### Failure Categories

| Category | Semantics |
|----------|-----------|
| `missed_document` | Expected document not found in index |
| `missed_provision` | Expected provision label not found in document |
| `missed_requirement` | Expected requirement not found |
| `citation_missing` | Expected source quote or locator absent |
| `metadata_mismatch` | Metadata field value differs from expected |
| `date_confusion` | Release/effective/transition date incorrectly extracted |
| `topic_mismatch` | Expected topic tag missing or incorrect |
| `unsupported_answer` | Extracted data does not support expected answer (future use) |

## Check Types

### 1. `document_id_exists`

Verifies that a document with the given ID exists in the compiled document index.

**`expected`**: `string` — the document ID.

```jsonl
{"id": "document-exists-gb-7258-2017-001", "type": "document_id_exists", "category": "missed_document", "severity": "error", "expected": "gb-7258-2017", "notes": "GB 7258-2017 must be present after ingestion"}
```

**Pass**: document ID found in `documents.json` or document index.
**Fail**: document ID absent.

### 2. `provision_label_exists`

Verifies that a specific provision label exists within a document's candidate provisions.

**`expected`**: `object` with `document_id` (string) and `label` (string).

```jsonl
{"id": "provision-exists-gb-7258-2017-001", "type": "provision_label_exists", "category": "missed_provision", "severity": "warn", "expected": {"document_id": "gb-7258-2017", "label": "4"}, "notes": "Section 4 is a major top-level clause in GB 7258-2017"}
```

**Pass**: at least one provision with matching `document_id` and `label` found in `provisions.jsonl`.
**Fail**: no matching provision.

### 3. `keyword_search`

Verifies that a keyword or phrase returns at least `min_count` results from the search index.

**`expected`**: `object` with `keyword` (string) and `min_count` (integer).

```jsonl
{"id": "keyword-brake-gb-7258-2017-001", "type": "keyword_search", "category": "missed_provision", "severity": "warn", "expected": {"keyword": "制动", "min_count": 1}, "document_id": "gb-7258-2017", "notes": "Braking-related provisions must be searchable"}
```

**Pass**: `search(keyword)` returns at least `min_count` results within the optional `document_id` scope.
**Fail**: fewer than `min_count` results.

### 4. `requirement_modality_exists`

Verifies that at least one extracted requirement within a document has the specified modality value.

**`expected`**: `object` with `document_id` (string) and `modality` (string).

```jsonl
{"id": "req-modality-gb-7258-2017-001", "type": "requirement_modality_exists", "category": "missed_requirement", "severity": "warn", "expected": {"document_id": "gb-7258-2017", "modality": "shall"}, "notes": "GB standards use 'shall' (应) as the primary obligation modality"}
```

**Pass**: at least one requirement in `requirements.jsonl` has `modality` matching the expected value.
**Fail**: no requirement with that modality.

### 5. `evidence_quote_exists`

Verifies that a provision or requirement contains an `evidence` or `quote` field whose text includes a given substring.

**`expected`**: `object` with `document_id` (string), `label` (string), and `quote_substring` (string).

```jsonl
{"id": "evidence-quote-gb-7258-2017-001", "type": "evidence_quote_exists", "category": "citation_missing", "severity": "warn", "expected": {"document_id": "gb-7258-2017", "label": "4.1", "quote_substring": "机动车"}, "notes": "Provision 4.1 should contain evidence mentioning motor vehicles"}
```

**Pass**: matching provision/requirement has an evidence or quote field containing `quote_substring`.
**Fail**: no matching evidence text.

### 6. `metadata_field_equals`

Verifies that a document's metadata field equals an expected value.

**`expected`**: `object` with `document_id` (string), `field` (string), and `value` (any).

```jsonl
{"id": "metadata-title-gb-7258-2017-001", "type": "metadata_field_equals", "category": "metadata_mismatch", "severity": "error", "expected": {"document_id": "gb-7258-2017", "field": "title", "value": "机动车运行安全技术条件"}, "notes": "Document title must match the standard's official Chinese title"}
```

**Pass**: `documents.json[document_id].metadata[field]` equals `value`.
**Fail**: field missing or value differs.

### 7. `topic_tag_exists`

Verifies that a specific topic tag is present in the document's topic-tags output.

**`expected`**: `object` with `document_id` (string) and `topic` (string).

```jsonl
{"id": "topic-braking-gb-7258-2017-001", "type": "topic_tag_exists", "category": "topic_mismatch", "severity": "info", "expected": {"document_id": "gb-7258-2017", "topic": "braking-system"}, "notes": "Braking system should be a tagged topic in GB 7258-2017"}
```

**Pass**: `topic-tags/<document_id>.json` contains the expected topic.
**Fail**: topic absent.

## Backward Compatibility

The Phase 3.5 smoke checks (`eval/qa/phase3_5_smoke.jsonl`) use a simpler format with only `id`, `type`, and `expected`. The eval runner must continue to accept this format, treating missing `category`, `severity`, and `notes` fields as:

- `category`: inferred from check type (e.g. `document_id_exists` → `missed_document`)
- `severity`: `error`
- `notes`: empty string
