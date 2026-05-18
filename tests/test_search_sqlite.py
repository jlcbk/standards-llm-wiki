"""Tests for standards_wiki.sqlite_search."""

import json

import yaml

from standards_wiki.candidates import write_jsonl
from standards_wiki.sqlite_export import export_sqlite
from standards_wiki.sqlite_search import search_sqlite

DOC_ID = "gb-test-2024"

# Provision text includes CJK short words for search stability testing:
# 制动 (braking), 座椅 (seat), 校车 (school bus), 机动车 (motor vehicle)
PROVISION_TEXT = (
    "本标准规定了机动车运行安全技术条件。"
    "制动系统应满足基本要求。"
    "座椅及其固定装置应牢固。"
    "校车应配备安全带。"
    "vehiclesafety ALLTEST"
)

REQUIREMENT_EVIDENCE = "机动车必须符合安全技术条件 ALLTEST 制动 座椅 校车"


def _build_db(tmp_path, doc_id=DOC_ID, include_topic_tags=True):
    """Create a test database via the P5-01 exporter."""
    cand = tmp_path / "_candidates"

    meta_dir = cand / "metadata"
    meta_dir.mkdir(parents=True)
    meta = {
        "title": "测试标准",
        "document_type": "national",
        "standard_id": "GB-TEST-2024",
        "publisher": "测试出版社",
        "source_text": "sources/test.md",
        "raw_path": "raw/test.pdf",
        "confidence": "low",
        "review_status": "draft",
    }
    (meta_dir / f"{doc_id}.yaml").write_text(
        yaml.dump(meta, allow_unicode=True), encoding="utf-8"
    )

    prov_dir = cand / "provisions"
    prov_dir.mkdir(parents=True)
    write_jsonl(
        [
            {
                "provision_id": f"{doc_id}-1",
                "document_id": doc_id,
                "label": "1",
                "kind": "section",
                "title": "总则",
                "text": PROVISION_TEXT,
                "locator": {"label": "1", "occurrence": 1},
                "confidence": "low",
                "review_status": "machine_extracted",
            }
        ],
        prov_dir / f"{doc_id}.jsonl",
    )

    req_dir = cand / "requirements"
    req_dir.mkdir(parents=True)
    write_jsonl(
        [
            {
                "requirement_id": f"{doc_id}-1-r1",
                "document_id": doc_id,
                "provision_id": f"{doc_id}-1",
                "modality": "must",
                "subject": "机动车",
                "action": "符合",
                "object": "安全技术条件",
                "evidence": {"quote": REQUIREMENT_EVIDENCE},
                "confidence": "low",
                "review_status": "machine_extracted",
            }
        ],
        req_dir / f"{doc_id}.jsonl",
    )

    if include_topic_tags:
        tt_dir = cand / "topic-tags"
        tt_dir.mkdir(parents=True)
        tt_data = {
            "document_id": doc_id,
            "provisions": [
                {
                    "id": f"{doc_id}-1",
                    "topics": ["braking", "seats"],
                    "entities": ["vehicle", "passenger"],
                }
            ],
            "requirements": [
                {
                    "id": f"{doc_id}-1-r1",
                    "topics": ["safety"],
                    "entities": ["vehicle"],
                }
            ],
        }
        (tt_dir / f"{doc_id}.json").write_text(
            json.dumps(tt_data, ensure_ascii=False), encoding="utf-8"
        )

    db_path = tmp_path / "kb.sqlite"
    export_sqlite(str(cand), str(db_path))
    return db_path


class TestSearchProvisions:
    def test_finds_known_keyword(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "vehiclesafety", mode="provisions")

        assert len(results) == 1
        r = results[0]
        assert r["type"] == "provision"
        assert r["id"] == f"{DOC_ID}-1"
        assert r["document_id"] == DOC_ID
        assert r["label"] == "1"
        assert r["title"] == "总则"
        assert "vehiclesafety" in r["snippet"]

    def test_finds_by_title(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "总则", mode="provisions")

        assert len(results) >= 1
        assert any(r["title"] == "总则" for r in results)


class TestSearchDocuments:
    def test_finds_by_title(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "测试标准", mode="documents")

        assert len(results) == 1
        r = results[0]
        assert r["type"] == "document"
        assert r["id"] == DOC_ID
        assert r["document_id"] == DOC_ID
        assert r["title"] == "测试标准"
        assert r["review_status"] == "draft"


class TestSearchRequirements:
    def test_finds_by_subject(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "机动车", mode="requirements")

        assert len(results) == 1
        r = results[0]
        assert r["type"] == "requirement"
        assert r["id"] == f"{DOC_ID}-1-r1"
        assert r["document_id"] == DOC_ID
        assert r["modality"] == "must"
        assert r["subject"] == "机动车"
        assert "机动车" in r["snippet"]

    def test_finds_by_evidence_quote(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "安全技术条件", mode="requirements")

        assert len(results) >= 1


class TestCJKShortWordSearch:
    """Phase 5.5-03: Validate CJK short-word / substring search stability."""

    def test_provision_short_word_braking(self, tmp_path):
        """制动 (2-char CJK word) must match provision text."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "制动", mode="provisions")
        assert len(results) >= 1
        assert any("制动" in r["snippet"] for r in results)

    def test_provision_short_word_seat(self, tmp_path):
        """座椅 (2-char CJK word) must match provision text."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "座椅", mode="provisions")
        assert len(results) >= 1
        assert any("座椅" in r["snippet"] for r in results)

    def test_provision_short_word_school_bus(self, tmp_path):
        """校车 (2-char CJK word) must match provision text."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "校车", mode="provisions")
        assert len(results) >= 1
        assert any("校车" in r["snippet"] for r in results)

    def test_provision_three_char_word(self, tmp_path):
        """机动车 (3-char CJK word) must match provision text."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "机动车", mode="provisions")
        assert len(results) >= 1
        assert any("机动车" in r["snippet"] for r in results)

    def test_requirement_short_word_braking(self, tmp_path):
        """制动 must also match in requirement evidence_quote."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "制动", mode="requirements")
        assert len(results) >= 1

    def test_requirement_three_char_word(self, tmp_path):
        """机动车 must match requirement subject."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "机动车", mode="requirements")
        assert len(results) >= 1

    def test_english_token_vehiclesafety(self, tmp_path):
        """ASCII compound token must still match."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "vehiclesafety", mode="provisions")
        assert len(results) >= 1

    def test_english_token_alltest(self, tmp_path):
        """ASCII token ALLTEST must still match across modes."""
        db = _build_db(tmp_path)
        results = search_sqlite(db, "ALLTEST", mode="all")
        types = {r["type"] for r in results}
        assert "provision" in types
        assert "requirement" in types


class TestDocumentIdFilter:
    def test_filters_by_document_id(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", document_id=DOC_ID
        )
        assert len(results) == 1

    def test_no_match_for_wrong_document_id(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", document_id="nonexistent"
        )
        assert len(results) == 0


class TestReviewStatusFilter:
    def test_filters_provisions_by_review_status(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db,
            "vehiclesafety",
            mode="provisions",
            review_status="machine_extracted",
        )
        assert len(results) == 1

    def test_excludes_wrong_status(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db,
            "vehiclesafety",
            mode="provisions",
            review_status="human_verified",
        )
        assert len(results) == 0

    def test_ignored_for_requirements(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db,
            "机动车",
            mode="requirements",
            review_status="machine_extracted",
        )
        # requirements table has no review_status — filter silently ignored
        assert len(results) == 1


class TestModeAll:
    def test_merges_all_types(self, tmp_path):
        db = _build_db(tmp_path)
        # "ALLTEST" is an ASCII token present in both provision text and
        # requirement evidence_quote, so FTS5 reliably matches both types.
        results = search_sqlite(db, "ALLTEST", mode="all")

        types = {r["type"] for r in results}
        assert "provision" in types
        assert "requirement" in types

    def test_respects_limit(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "ALLTEST", mode="all", limit=1)
        assert len(results) == 1


class TestLimit:
    def test_limit_restricts_results(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "vehiclesafety", mode="provisions", limit=0)
        assert len(results) == 0


class TestMissingDatabase:
    def test_raises_file_not_found(self, tmp_path):
        missing = tmp_path / "nope.sqlite"
        try:
            search_sqlite(missing, "anything")
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "export_sqlite.py" in str(e)


class TestInvalidMode:
    def test_raises_value_error(self, tmp_path):
        db = _build_db(tmp_path)
        try:
            search_sqlite(db, "anything", mode="bogus")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "bogus" in str(e)


class TestJsonSerializable:
    def test_results_are_json_serializable(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "vehiclesafety", mode="provisions")
        serialized = json.dumps(results, ensure_ascii=False)
        assert isinstance(serialized, str)
        parsed = json.loads(serialized)
        assert parsed == results


# ---------------------------------------------------------------------------
# Phase 5.5-04: Topic / Entity filter tests
# ---------------------------------------------------------------------------


class TestTopicFilterProvisions:
    """Provisions + --topic hit / miss."""

    def test_topic_hit(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", topic="braking"
        )
        assert len(results) == 1
        assert results[0]["type"] == "provision"

    def test_topic_miss(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", topic="nonexistent-topic"
        )
        assert len(results) == 0


class TestEntityFilterProvisions:
    """Provisions + --entity hit / miss."""

    def test_entity_hit(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", entity="vehicle"
        )
        assert len(results) == 1

    def test_entity_miss(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", entity="nonexistent-entity"
        )
        assert len(results) == 0


class TestTopicEntityFilterRequirements:
    """Requirements + topic/entity hit."""

    def test_topic_hit(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "机动车", mode="requirements", topic="safety"
        )
        assert len(results) == 1
        assert results[0]["type"] == "requirement"

    def test_entity_hit(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "机动车", mode="requirements", entity="vehicle"
        )
        assert len(results) == 1

    def test_topic_miss(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "机动车", mode="requirements", topic="nonexistent"
        )
        assert len(results) == 0


class TestTopicEntityFilterDocuments:
    """Documents mode returns [] when topic/entity specified."""

    def test_topic_returns_empty(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "测试标准", mode="documents", topic="braking"
        )
        assert results == []

    def test_entity_returns_empty(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "测试标准", mode="documents", entity="vehicle"
        )
        assert results == []


class TestModeAllWithTopicFilter:
    """mode=all + topic should not return document type."""

    def test_no_documents_with_topic(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "ALLTEST", mode="all", topic="braking")
        types = {r["type"] for r in results}
        assert "document" not in types

    def test_provisions_still_filtered_by_topic(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "ALLTEST", mode="all", topic="braking")
        # provision gb-test-2024-1 has topic "braking"
        assert any(r["type"] == "provision" for r in results)

    def test_requirements_miss_topic(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(db, "ALLTEST", mode="all", topic="nonexistent")
        # No provision/requirement has this topic
        assert len(results) == 0


class TestTopicAndEntityCombined:
    """topic + entity combined filter."""

    def test_both_match(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions",
            topic="braking", entity="vehicle",
        )
        assert len(results) == 1

    def test_one_mismatch_excludes(self, tmp_path):
        db = _build_db(tmp_path)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions",
            topic="braking", entity="nonexistent",
        )
        assert len(results) == 0


class TestOldSchemaGracefulDegradation:
    """When junction tables are missing, filters return []."""

    def test_empty_junction_topic_returns_empty(self, tmp_path):
        """Junction tables exist but empty — EXISTS returns no matches."""
        db = _build_db(tmp_path, include_topic_tags=False)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", topic="braking"
        )
        assert results == []

    def test_empty_junction_entity_returns_empty(self, tmp_path):
        db = _build_db(tmp_path, include_topic_tags=False)
        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", entity="vehicle"
        )
        assert results == []

    def test_empty_junction_no_filter_still_works(self, tmp_path):
        db = _build_db(tmp_path, include_topic_tags=False)
        results = search_sqlite(db, "vehiclesafety", mode="provisions")
        assert len(results) == 1

    def test_no_junction_tables_graceful(self, tmp_path):
        """Simulate a truly old schema by dropping junction tables."""
        import sqlite3

        db = _build_db(tmp_path, include_topic_tags=False)
        conn = sqlite3.connect(str(db))
        for t in ["provision_topics", "provision_entities",
                   "requirement_topics", "requirement_entities"]:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()
        conn.close()

        results = search_sqlite(
            db, "vehiclesafety", mode="provisions", topic="braking"
        )
        assert results == []

    def test_no_junction_tables_no_filter_works(self, tmp_path):
        import sqlite3

        db = _build_db(tmp_path, include_topic_tags=False)
        conn = sqlite3.connect(str(db))
        for t in ["provision_topics", "provision_entities",
                   "requirement_topics", "requirement_entities"]:
            conn.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()
        conn.close()

        results = search_sqlite(db, "vehiclesafety", mode="provisions")
        assert len(results) == 1


class TestCLITopicEntityArgs:
    """CLI argument parsing and output."""

    def test_cli_topic_filter(self, tmp_path):
        from tools.search_sqlite import main as cli_main
        import io
        from contextlib import redirect_stdout

        db = _build_db(tmp_path)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_main([
                "vehiclesafety", "--db", str(db),
                "--mode", "provisions", "--topic", "braking",
            ])
        output = json.loads(buf.getvalue())
        assert len(output) == 1
        assert output[0]["type"] == "provision"

    def test_cli_entity_filter(self, tmp_path):
        from tools.search_sqlite import main as cli_main
        import io
        from contextlib import redirect_stdout

        db = _build_db(tmp_path)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_main([
                "vehiclesafety", "--db", str(db),
                "--mode", "provisions", "--entity", "vehicle",
            ])
        output = json.loads(buf.getvalue())
        assert len(output) == 1

    def test_cli_no_filter_default(self, tmp_path):
        from tools.search_sqlite import main as cli_main
        import io
        from contextlib import redirect_stdout

        db = _build_db(tmp_path)
        buf = io.StringIO()
        with redirect_stdout(buf):
            cli_main([
                "vehiclesafety", "--db", str(db),
                "--mode", "provisions",
            ])
        output = json.loads(buf.getvalue())
        assert len(output) == 1
