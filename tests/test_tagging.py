"""Tests for rule-based topic and entity tagging."""

from standards_wiki.tagging import tag_record, tag_records


def _provision(**overrides) -> dict:
    base = {
        "document_id": "gb-7258-2017",
        "provision_id": "gb-7258-2017-4.1.1",
        "text": "",
        "title": "",
        "source_text": "",
    }
    base.update(overrides)
    return base


class TestChineseKeywordMatching:
    def test_seats_topic(self):
        result = tag_record(_provision(text="汽车座椅应具备足够强度"))
        assert "seats" in result["topics"]

    def test_braking_system_topic(self):
        result = tag_record(_provision(text="制动系统应保持完好"))
        assert "braking-system" in result["topics"]

    def test_lighting_system_topic(self):
        result = tag_record(_provision(text="前照灯的发光强度应符合要求"))
        assert "lighting-system" in result["topics"]

    def test_vehicle_entity(self):
        result = tag_record(_provision(text="机动车应定期检验"))
        assert "vehicle" in result["entities"]

    def test_component_entity(self):
        result = tag_record(_provision(text="轮胎花纹深度应合格"))
        assert "component" in result["entities"]

    def test_passenger_entity(self):
        result = tag_record(_provision(text="乘员应系安全带"))
        assert "passenger" in result["entities"]


class TestMultiTopic:
    def test_multiple_topics(self):
        result = tag_record(_provision(text="校车的座椅及制动系统应符合要求"))
        assert "seats" in result["topics"]
        assert "braking-system" in result["topics"]
        assert "school-bus" in result["topics"]

    def test_topics_sorted_stable(self):
        result = tag_record(_provision(text="校车的座椅及制动系统灯光均应合格"))
        assert result["topics"] == sorted(result["topics"])

    def test_entities_sorted_stable(self):
        result = tag_record(_provision(text="机动车座椅制动灯光安全带均应合格"))
        assert result["entities"] == sorted(result["entities"])


class TestRequirementId:
    def test_uses_requirement_id(self):
        rec = _provision()
        rec.pop("provision_id")
        rec["requirement_id"] = "gb-7258-2017-r1"
        result = tag_record(rec)
        assert result["id"] == "gb-7258-2017-r1"

    def test_provision_id_takes_priority(self):
        result = tag_record(_provision(
            provision_id="gb-7258-2017-4.1.1",
            requirement_id="gb-7258-2017-r1",
        ))
        assert result["id"] == "gb-7258-2017-4.1.1"


class TestTextFieldMerge:
    def test_title_only(self):
        result = tag_record(_provision(title="座椅要求"))
        assert "seats" in result["topics"]

    def test_source_text_only(self):
        result = tag_record(_provision(source_text="制动性能检测标准"))
        assert "braking-system" in result["topics"]

    def test_evidence_quote(self):
        rec = _provision(evidence={"quote": "前照灯亮度应达标"})
        result = tag_record(rec)
        assert "lighting-system" in result["topics"]

    def test_evidence_list_quotes(self):
        rec = _provision(evidence=[
            {"quote": "校车座椅"},
            {"quote": "安全带"},
        ])
        result = tag_record(rec)
        assert "seats" in result["topics"]
        assert "school-bus" in result["topics"]

    def test_merge_all_fields(self):
        result = tag_record(_provision(
            text="座椅",
            title="制动",
            source_text="校车",
        ))
        assert "seats" in result["topics"]
        assert "braking-system" in result["topics"]
        assert "school-bus" in result["topics"]


class TestDocumentId:
    def test_document_id_preserved(self):
        result = tag_record(_provision(document_id="gb-7258-2017"))
        assert result["document_id"] == "gb-7258-2017"

    def test_document_id_default_empty(self):
        result = tag_record({})
        assert result["document_id"] == ""


class TestMatchedKeywords:
    def test_topics_keywords_structure(self):
        result = tag_record(_provision(text="汽车座椅应具备足够强度"))
        mk = result["matched_keywords"]
        assert "topics" in mk
        assert "entities" in mk
        assert mk["topics"]["seats"] == ["座椅"]

    def test_entities_keywords_structure(self):
        result = tag_record(_provision(text="机动车应定期检验"))
        mk = result["matched_keywords"]
        assert mk["entities"]["vehicle"] == ["机动车"]

    def test_multiple_keywords_per_topic(self):
        result = tag_record(_provision(text="座椅头枕靠背均应合格"))
        mk = result["matched_keywords"]
        assert mk["topics"]["seats"] == ["头枕", "座椅", "靠背"]

    def test_multiple_keywords_per_entity(self):
        result = tag_record(_provision(text="机动车汽车车辆均需检验"))
        mk = result["matched_keywords"]
        assert mk["entities"]["vehicle"] == ["机动车", "汽车", "车辆"]

    def test_keywords_sorted(self):
        result = tag_record(_provision(text="靠背座椅头枕座垫安全带"))
        mk = result["matched_keywords"]
        assert mk["topics"]["seats"] == sorted(mk["topics"]["seats"])

    def test_dedup_keyword(self):
        result = tag_record(_provision(text="座椅座椅座椅"))
        mk = result["matched_keywords"]
        assert mk["topics"]["seats"] == ["座椅"]

    def test_no_match_empty_dicts(self):
        result = tag_record(_provision(text="这条规定不包含任何关键词"))
        mk = result["matched_keywords"]
        assert mk["topics"] == {}
        assert mk["entities"] == {}

    def test_cross_topic_entity(self):
        result = tag_record(_provision(text="校车座椅制动系统"))
        mk = result["matched_keywords"]
        assert "seats" in mk["topics"]
        assert "braking-system" in mk["topics"]
        assert "school-bus" in mk["topics"]
        assert "component" in mk["entities"]


class TestNoMatch:
    def test_no_match(self):
        result = tag_record(_provision(text="这条规定不包含任何关键词"))
        assert result["topics"] == []
        assert result["entities"] == []

    def test_empty_record(self):
        result = tag_record({})
        assert result["topics"] == []
        assert result["entities"] == []


class TestTagRecords:
    def test_batch(self):
        records = [
            _provision(text="座椅"),
            _provision(text="制动"),
        ]
        results = tag_records(records)
        assert len(results) == 2
        assert "seats" in results[0]["topics"]
        assert "braking-system" in results[1]["topics"]
