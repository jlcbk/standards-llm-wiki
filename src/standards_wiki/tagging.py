"""Rule-based topic and entity tagging for provision records."""

from __future__ import annotations

TOPIC_RULES: dict[str, list[str]] = {
    "seats": ["座椅", "座垫", "靠背", "头枕", "安全带"],
    "braking-system": ["制动", "刹车", "制动液", "制动盘", "abs"],
    "lighting-system": ["灯光", "前照灯", "尾灯", "转向灯", "倒车灯", "牌照灯", "示廓灯"],
    "vehicle-dimensions": ["长", "宽", "高", "尺寸", "轴距", "轮距", "外廓"],
    "school-bus": ["校车", "学生客车", "学童"],
}

_ENTITY_KEYWORDS: dict[str, list[str]] = {
    "vehicle": ["机动车", "汽车", "车辆", "客车", "货车", "拖拉机", "摩托车"],
    "component": ["座椅", "制动", "灯光", "轮胎", "发动机", "方向盘", "安全带"],
    "passenger": ["乘员", "乘客", "驾驶员", "驾驶人", "儿童"],
}

_TOPIC_ENTRIES = [
    (topic, kw) for topic, kws in TOPIC_RULES.items() for kw in kws
]

_ENTITY_ENTRIES = [
    (entity, kw) for entity, kws in _ENTITY_KEYWORDS.items() for kw in kws
]


def _collect_text(record: dict) -> str:
    """Merge all available text fields for keyword matching."""
    parts: list[str] = [
        record.get("text", ""),
        record.get("title", ""),
        record.get("source_text", ""),
    ]
    evidence = record.get("evidence")
    if isinstance(evidence, dict):
        parts.append(evidence.get("quote", ""))
    elif isinstance(evidence, list):
        for e in evidence:
            if isinstance(e, dict):
                parts.append(e.get("quote", ""))
    return " ".join(p for p in parts if p).lower()


def tag_record(record: dict) -> dict:
    """Tag a single provision record with topics and entities.

    Merges text, title, source_text, and evidence.quote for matching.
    Returns document_id, id (from provision_id or requirement_id),
    sorted topics, sorted entities, and matched_keywords (dict with
    'topics' and 'entities' sub-dicts mapping category to sorted
    matched keyword lists). Returns empty structures when nothing matches.
    """
    text = _collect_text(record)

    topic_kw: dict[str, set[str]] = {}
    for topic, kw in _TOPIC_ENTRIES:
        if kw in text:
            topic_kw.setdefault(topic, set()).add(kw)

    entity_kw: dict[str, set[str]] = {}
    for entity, kw in _ENTITY_ENTRIES:
        if kw in text:
            entity_kw.setdefault(entity, set()).add(kw)

    topics = sorted(topic_kw)
    entities = sorted(entity_kw)

    matched_keywords = {
        "topics": {t: sorted(topic_kw[t]) for t in topics},
        "entities": {e: sorted(entity_kw[e]) for e in entities},
    }

    return {
        "document_id": record.get("document_id", ""),
        "id": record.get("provision_id") or record.get("requirement_id", ""),
        "topics": topics,
        "entities": entities,
        "matched_keywords": matched_keywords,
    }


def tag_records(records: list[dict]) -> list[dict]:
    """Tag multiple provision records."""
    return [tag_record(r) for r in records]
