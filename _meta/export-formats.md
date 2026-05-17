# Export Formats

This project should expose multiple derived formats from the canonical Markdown wiki. This mirrors mature regulatory KG projects that emit RDF, SQLite and search indexes from one model.

## Principle

```text
Markdown canonical source
  → derived artifacts
```

Generated artifacts must be reproducible. Do not manually edit generated DB/index files.

## Recommended Derived Outputs

| Output | Purpose | Priority |
|---|---|---|
| SQLite FTS5 | local deterministic full-text search | P0 |
| JSON index | easy API/static/frontend consumption | P0 |
| JSONL graph | simple graph interchange | P1 |
| Neo4j CSV | graph exploration / GraphRAG | P1 |
| Vector index | semantic recall expansion | P1 |
| RDF/TTL | standards/semantic-web interoperability | P2 |
| SOLR/OpenSearch JSON | production search service | P2 |

## SQLite FTS5

Suggested tables:

```sql
CREATE TABLE documents (
  document_id TEXT PRIMARY KEY,
  title TEXT,
  document_type TEXT,
  jurisdiction TEXT,
  issuer TEXT,
  family TEXT,
  version TEXT,
  status TEXT,
  source_path TEXT,
  source_url TEXT,
  source_text TEXT,
  confidence TEXT,
  review_status TEXT,
  path TEXT NOT NULL
);

CREATE TABLE provisions (
  provision_id TEXT PRIMARY KEY,
  document_id TEXT,
  label TEXT,
  kind TEXT,
  title TEXT,
  text TEXT,
  source_locator TEXT,
  confidence TEXT,
  review_status TEXT,
  path TEXT NOT NULL
);

CREATE VIRTUAL TABLE provisions_fts USING fts5(
  provision_id UNINDEXED,
  document_id UNINDEXED,
  title,
  text,
  tokenize='unicode61'
);
```

## JSON Index

Recommended generated files:

```text
db/json/documents.json
db/json/provisions.json
db/json/topics.json
db/json/entities.json
db/json/citations.json
db/json/requirements.json
```

These are useful for static web apps and debugging.

## JSONL Graph

Recommended schema:

```json
{"id":"gb-7258-2017","type":"Document","props":{}}
{"id":"gb-7258-2017-11-6","type":"Provision","props":{}}
```

Edges:

```json
{"source":"gb-7258-2017","target":"gb-7258-2017-11-6","type":"HAS_PROVISION","props":{}}
```

## Vector Index

Vector chunks should be provision-aware, not arbitrary token chunks.

Preferred embedding units:

1. provision exact text;
2. provision summary + structured requirement fields;
3. topic pages;
4. question pages.

Each vector record must include:

```yaml
id: provision_id or page path
document_id: ...
provision_id: ...
source_path: ...
review_status: ...
confidence: ...
```

## RDF/TTL

RDF is optional but useful for external interoperability. If implemented, map:

```text
Document → regulatory:Document
Provision → regulatory:Provision
Requirement → regulatory:Requirement
Topic → skos:Concept
Entity → schema:Thing / org:Organization / custom class
Citation → prov:Entity / prov:wasDerivedFrom
```

Do not start with RDF if it slows MVP. SQLite + JSON + Markdown are enough for first usable system.

## Export CLI

Target commands:

```bash
.venv/bin/python tools/export_sqlite.py --candidates-dir _candidates --out db/kb.sqlite
.venv/bin/python tools/export_json.py --candidates-dir _candidates --output-dir db/json
.venv/bin/python tools/export_graph.py --candidates-dir _candidates --out db/graph
```

Future export targets may add Neo4j CSV or RDF/TTL, but Phase 5 keeps the
implemented layer to SQLite FTS5 and Graph JSONL.

## Validation Before Export

Export should fail or warn on:

- duplicate IDs;
- missing source path/source URL;
- invalid frontmatter;
- formal pages with `confidence: low` but no unresolved issue;
- requirements without evidence quote;
- replacement/effective-date facts without citation.
