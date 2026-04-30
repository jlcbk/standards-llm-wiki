# Tooling

本文件列出项目运转所需的外部工具。原则：Markdown 仓库是 canonical source；外部数据库、向量索引、缓存都可以从仓库重建。

## PDF / Document Extraction

### Default Stack

| Input | Preferred Tool | Fallback | Notes |
|---|---|---|---|
| Text PDF | `PyMuPDF`, `pymupdf4llm` | `pdftotext` | 快、轻量，适合大多数文字型 PDF |
| Scanned PDF | `marker-pdf`, `docling` OCR | PaddleOCR / Tesseract | 用于扫描件、复杂版面 |
| Complex tables | `marker-pdf`, `docling` | Camelot / Tabula | 表格需要人工 spot check |
| DOCX | `python-docx` | LibreOffice headless | 不要 OCR Word，直接解析结构 |
| Webpage | `trafilatura`, readability, Firecrawl-like service | raw HTML + manual clean | 必须保存 source URL |
| Images | PaddleOCR / Tesseract | manual review | 低 confidence |

## Recommended Python Dependencies

MVP：

```text
pymupdf
pymupdf4llm
python-frontmatter
pyyaml
pydantic
rich
typer
sqlite-utils
```

增强：

```text
marker-pdf
docling
trafilatura
python-docx
beautifulsoup4
lancedb
qdrant-client
sentence-transformers
```

## Suggested Project Modules

```text
tools/
├── kb_cli.py                    # Typer CLI entry
├── extractors/
│   ├── base.py
│   ├── pdf_pymupdf.py
│   ├── pdf_marker.py
│   ├── webpage.py
│   └── docx.py
├── parsers/
│   ├── base.py
│   ├── gb_standard.py
│   ├── iso_standard.py
│   ├── ece_regulation.py
│   ├── cn_policy.py
│   └── fallback.py
├── generators/
│   ├── document_page.py
│   ├── provision_pages.py
│   ├── topic_candidates.py
│   └── indexes.py
├── indexers/
│   ├── sqlite_fts.py
│   └── vector.py
└── validators/
    ├── frontmatter.py
    ├── links.py
    └── source_traceability.py
```

## Minimal Runtime Architecture

```text
Markdown repo
  ↓
kb CLI
  ├─ extract raw → sources
  ├─ parse sources → candidates
  ├─ generate formal pages
  ├─ validate schema/source traceability
  └─ build derived indexes
       ├─ SQLite FTS5
       └─ LanceDB/Qdrant optional

FastAPI service optional later:
  /search
  /document/{id}
  /ask
```

## Database Choices

### SQLite FTS5

Use first. Good for:

- exact standard IDs;
- clause numbers;
- issuer names;
- Chinese/English keyword search;
- local development without services.

### LanceDB

Good local vector DB option. Use for:

- provision semantic search;
- topic similarity;
- local MVP without Docker service.

### Qdrant

Good server/service option. Use when:

- multiple agents/services need shared vector retrieval;
- scale exceeds local LanceDB comfort;
- you want hybrid search with payload filters.

## Parser Strategy

Use deterministic parsing first, LLM second.

```text
1. Regex/rules for IDs, dates, clause labels
2. Layout-aware extraction for tables/annexes
3. LLM for ambiguous classification and summaries
4. Review gate for legal/regulatory conclusions
```

Do not use LLM as the primary OCR/PDF parser if deterministic tools can extract text.

## Confidence Rules

| Condition | confidence |
|---|---|
| Official source + deterministic extraction + reviewed | high |
| Official source + extraction OK but not manually checked | medium |
| OCR-heavy / weak model output / source unclear | low |
| Conflicting dates/replacements | low until resolved |

## Security / Git Hygiene

Do not commit:

- API keys or tokens;
- paid/copyrighted documents if repository visibility is not appropriate;
- generated DB files under `db/` unless intentionally publishing samples;
- model cache directories;
- raw credentials or private source URLs with embedded tokens.

Recommended `.gitignore` entries:

```gitignore
db/*.sqlite
db/*.sqlite-*
db/vector/
.cache/
.env
*.secret.*
```

## Verification Commands

Once CLI exists, expected checks:

```bash
kb validate
kb index --dry-run
pytest tests/ -q
```

Before CLI exists, use basic checks:

```bash
python - <<'PY'
from pathlib import Path
for path in Path('.').rglob('*.md'):
    text = path.read_text(encoding='utf-8')
    assert not '\t' in text, path
print('markdown sanity ok')
PY
```
