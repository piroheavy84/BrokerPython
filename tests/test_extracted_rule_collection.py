from domain.extracted_rule import (
    ExtractedRule,
    ExtractedRuleConfidence,
    ExtractedRuleSource,
)
from domain.extracted_rule_collection import ExtractedRuleCollection


def test_collection_adds_valid_rule():
    collection = ExtractedRuleCollection()

    rule = ExtractedRule(
        type="LTC_EXCEPTION",
        title="Deroga LTC",
        confidence=ExtractedRuleConfidence.HIGH,
        source=ExtractedRuleSource(
            document="chebanca.pdf",
            page=2,
            original_text="Testo originale",
        ),
    )

    collection.add(rule)

    assert len(collection) == 1
    assert collection.is_empty() is False


def test_collection_ignores_invalid_rule():
    collection = ExtractedRuleCollection()

    rule = ExtractedRule(
        type="",
        title="",
        confidence=ExtractedRuleConfidence.LOW,
        source=None,
    )

    collection.add(rule)

    assert len(collection) == 0
    assert collection.is_empty() is True


def test_collection_to_dict():
    collection = ExtractedRuleCollection()

    rule = ExtractedRule(
        type="LTC_EXCEPTION",
        title="Deroga LTC",
        confidence=ExtractedRuleConfidence.HIGH,
        source=ExtractedRuleSource(
            document="chebanca.pdf",
            page=2,
            original_text="Testo originale",
        ),
    )

    collection.add(rule)

    data = collection.to_dict()

    assert "rules" in data
    assert len(data["rules"]) == 1
    assert data["rules"][0]["type"] == "LTC_EXCEPTION"
