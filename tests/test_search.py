"""Tests for deterministic search."""

import sqlite3

import yaml

from standards_wiki.candidates import write_jsonl
from standards_wiki.search import search, format_results, SearchResult
from standards_wiki.sqlite_export import export_sqlite
from standards_wiki.indexer import collect_records


def _write_fixtures(tmp_path, doc_id="gb-test-2024"):
    """Create candidate fixtures for search testing."""
    cand = tmp_path / "_candidates"
    drafts = tmp_path / "documents" / "drafts"

    meta_dir = cand / "metadata"
    meta_dir.mkdir(parents=True)
    meta = {
        "title": "机动车运行安全技术条件",
        "document_type": "standard",
        "standard_id": "GB-TEST-2024",
        "review_status": "draft",
    }
    (meta_dir / f"{doc_id}.yaml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8"
    )

    drafts.mkdir(parents=True)
    fm_yaml = yaml.dump(
        {"document_id": doc_id, "title": "机动车运行安全技术条件", "review_status": "draft"},
        default_flow_style=False,
        allow_unicode=True,
    )
    (drafts / f"{doc_id}.md").write_text(
        f"---\n{fm_yaml}---\n\n正文", encoding="utf-8"
    )

    prov_dir = cand / "provisions"
    prov_dir.mkdir(parents=True)
    write_jsonl(
        [
            {
                "provision_id": f"{doc_id}-3-1",
                "document_id": doc_id,
                "label": "3.1",
                "kind": "clause",
                "title": "术语",
                "text": "机动车应由动力装置驱动",
                "confidence": "low",
                "review_status": "machine_extracted",
                "evidence": {"quote": "机动车应由动力装置驱动"},
            },
            {
                "provision_id": f"{doc_id}-4-1",
                "document_id": doc_id,
                "label": "4.1",
                "kind": "clause",
                "title": "要求",
                "text": "座椅应符合安全要求",
                "confidence": "low",
                "review_status": "machine_extracted",
                "evidence": {"quote": "座椅应符合安全要求"},
            },
        ],
        prov_dir / f"{doc_id}.jsonl",
    )

    req_dir = cand / "requirements"
    req_dir.mkdir(parents=True)
    write_jsonl(
        [
            {
                "requirement_id": f"{doc_id}-3-1-r1",
                "document_id": doc_id,
                "provision_id": f"{doc_id}-3-1",
                "modality": "must",
                "confidence": "low",
                "review_status": "machine_extracted",
                "evidence": {
                    "quote": "机动车应由动力装置驱动",
                },
            },
        ],
        req_dir / f"{doc_id}.jsonl",
    )

    return cand, drafts


class TestSearch:
    def test_search_by_document_title(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("机动车", candidates_dir=str(cand), drafts_dir=str(drafts))
        doc_hits = [h for h in hits if h.record_type == "document"]
        assert len(doc_hits) >= 1
        assert doc_hits[0].record_id == "gb-test-2024"

    def test_search_by_document_id(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("gb-test", candidates_dir=str(cand), drafts_dir=str(drafts))
        doc_hits = [h for h in hits if h.record_type == "document"]
        assert len(doc_hits) == 1

    def test_search_by_standard_id(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("GB-TEST", candidates_dir=str(cand), drafts_dir=str(drafts))
        doc_hits = [h for h in hits if h.record_type == "document"]
        assert len(doc_hits) == 1

    def test_search_by_provision_label(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("3.1", candidates_dir=str(cand), drafts_dir=str(drafts))
        prov_hits = [h for h in hits if h.record_type == "provision"]
        assert len(prov_hits) >= 1

    def test_search_by_provision_text(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("座椅", candidates_dir=str(cand), drafts_dir=str(drafts))
        prov_hits = [h for h in hits if h.record_type == "provision"]
        assert len(prov_hits) >= 1
        assert any("座椅" in h.matched_text for h in prov_hits)

    def test_search_by_requirement_quote(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("动力装置", candidates_dir=str(cand), drafts_dir=str(drafts))
        req_hits = [h for h in hits if h.record_type == "requirement"]
        assert len(req_hits) >= 1

    def test_search_limit(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("机动车", candidates_dir=str(cand), drafts_dir=str(drafts), limit=1)
        assert len(hits) <= 1

    def test_search_no_results(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("不存在的查询词xyz", candidates_dir=str(cand), drafts_dir=str(drafts))
        assert hits == []

    def test_search_case_insensitive(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits_upper = search("GB-TEST", candidates_dir=str(cand), drafts_dir=str(drafts))
        hits_lower = search("gb-test", candidates_dir=str(cand), drafts_dir=str(drafts))
        assert len(hits_upper) == len(hits_lower)

    def test_search_results_sorted_by_type_then_id(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        hits = search("机动车", candidates_dir=str(cand), drafts_dir=str(drafts))
        if len(hits) >= 2:
            type_order = {"document": 0, "provision": 1, "requirement": 2}
            for i in range(len(hits) - 1):
                a = type_order.get(hits[i].record_type, 99)
                b = type_order.get(hits[i + 1].record_type, 99)
                assert (a, hits[i].record_id) <= (b, hits[i + 1].record_id)


class TestFormatResults:
    def test_format_hit(self):
        hit = SearchResult(
            record_type="document",
            record_id="gb-1",
            title="测试",
            review_status="draft",
            source="meta/gb-1.yaml",
            matched_field="title",
            matched_text="测试",
        )
        output = format_results([hit])
        assert "[document] gb-1" in output

    def test_format_empty(self):
        output = format_results([])
        assert "No results found" in output


class TestSearchSQLite:
    def _build_db(self, tmp_path):
        cand, drafts = _write_fixtures(tmp_path)
        result = collect_records(candidates_dir=cand, drafts_dir=drafts)
        db_path = tmp_path / "test.sqlite"
        export_sqlite(result, db_path)
        return db_path

    def test_search_via_sqlite(self, tmp_path):
        db_path = self._build_db(tmp_path)
        hits = search("机动车", db_path=str(db_path))
        assert len(hits) >= 1

    def test_sqlite_search_short_query(self, tmp_path):
        db_path = self._build_db(tmp_path)
        hits = search("座椅", db_path=str(db_path))
        prov_hits = [h for h in hits if h.record_type == "provision"]
        assert len(prov_hits) >= 1

    def test_sqlite_fallback_no_db(self, tmp_path):
        hits = search("机动车", db_path=str(tmp_path / "nonexistent.sqlite"))
        assert hits == []

    def test_sqlite_no_results(self, tmp_path):
        db_path = self._build_db(tmp_path)
        hits = search("不存在的查询词xyz", db_path=str(db_path))
        assert hits == []
