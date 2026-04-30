# Graph Model

This file defines the optional graph layer derived from Markdown pages. It is inspired by regulatory knowledge graph projects such as OpenRegs, DORA/FFIEC GraphRAG and legal GraphRAG systems.

The graph is **derived**, not canonical. The canonical source remains Markdown.

## Node Types

```text
Source
Document
Provision
Requirement
Topic
Entity
TimelineEvent
Citation
Question
Comparison
```

## Core Edges

```text
(Source)-[:EXTRACTED_TO]->(Document)
(Document)-[:HAS_PROVISION]->(Provision)
(Provision)-[:SUBSECTION_OF]->(Provision)
(Provision)-[:NEXT]->(Provision)
(Provision)-[:PREVIOUS]->(Provision)
(Provision)-[:CITES]->(Document|Provision)
(Provision)-[:ABOUT]->(Topic)
(Provision)-[:MENTIONS]->(Entity)
(Provision)-[:APPLIES_TO]->(Entity)
(Provision)-[:HAS_REQUIREMENT]->(Requirement)
(Requirement)-[:HAS_EVIDENCE]->(Citation)
(Document)-[:HAS_TIMELINE_EVENT]->(TimelineEvent)
(Document)-[:REPLACES]->(Document)
(Document)-[:REPLACED_BY]->(Document)
(Comparison)-[:COMPARES]->(Document|Provision|Topic)
(Question)-[:ANSWERED_BY]->(Document|Provision|Topic|Comparison)
```

## Minimal Property Model

### Document

```yaml
document_id: gb-7258-2017
title: GB 7258-2017 机动车运行安全技术条件
document_type: standard
jurisdiction: CN
issuer: SAC
family: GB 7258
version: "2017"
status: effective | replaced | draft | unknown
release_date: YYYY-MM-DD | unknown
effective_date: YYYY-MM-DD | unknown
source_path: raw/standards/gb/gb-7258-2017.pdf
source_text: sources/standards/gb/gb-7258-2017.md
review_status: reviewed | verified | machine_extracted | draft
confidence: high | medium | low
```

### Provision

```yaml
provision_id: gb-7258-2017-11-6
document_id: gb-7258-2017
label: "11.6"
kind: clause | article | paragraph | section | annex | table | requirement | item | unknown
text_hash: sha256-of-exact-text
source_locator:
  page: 42
  label: "11.6"
review_status: reviewed
confidence: medium
```

### Requirement

```yaml
requirement_id: gb-7258-2017-11-6-r1
modality: must | must_not | should | may | unknown
subject: []
action: unknown
object: unknown
condition: unknown
exception: unknown
deadline: unknown
```

## Document Tree Pattern

Use a document backbone similar to DORA/FFIEC GraphRAG:

```text
Document
  └── Chapter / Section Provision
        └── Subsection Provision
              └── Paragraph / Clause Provision
```

Required edges:

- `HAS_PROVISION`: from document to top-level provisions;
- `SUBSECTION_OF`: child provision to parent provision;
- `NEXT`: sequential provision order within the same parent.

This preserves context better than flat chunks.

## Query Patterns

### Topic to Requirements

```cypher
MATCH (t:Topic {topic_id: $topic})<-[:ABOUT]-(p:Provision)-[:HAS_REQUIREMENT]->(r:Requirement)
RETURN p, r
```

### Applicability Lookup

```cypher
MATCH (e:Entity {entity_id: $vehicle_type})<-[:APPLIES_TO]-(p:Provision)-[:HAS_REQUIREMENT]->(r:Requirement)
RETURN p, r
```

### Version Replacement Chain

```cypher
MATCH path = (old:Document {document_id: $document_id})-[:REPLACED_BY*0..]->(new:Document)
RETURN path
```

### Citation Expansion

```cypher
MATCH (p:Provision {provision_id: $provision_id})-[:CITES]->(x)
RETURN x
```

## Export Targets

Start simple:

1. JSONL nodes and edges;
2. SQLite relational tables;
3. optional Neo4j CSV;
4. optional RDF/TTL later.

Recommended files:

```text
db/graph/nodes.jsonl
db/graph/edges.jsonl
db/graph/neo4j_nodes.csv
db/graph/neo4j_edges.csv
```

Do not commit generated graph files unless they are small examples.

## Graph Quality Rules

- No edge may exist without source evidence or derivation rule.
- `REPLACES`, `REPLACED_BY`, `EFFECTIVE_ON` require official source evidence.
- Weak model-suggested edges go to `_candidates/` first.
- Contradictory edges must be recorded in `_reviews/contradiction-checks/`.
- Use stable IDs from Markdown frontmatter.
