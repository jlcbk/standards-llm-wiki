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


def _build_db(tmp_path, doc_id=DOC_ID):
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
