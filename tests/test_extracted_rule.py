from domain.extracted_rule import (
    ExtractedRule,
    ExtractedRuleConfidence,
    ExtractedRuleSource,
)

from domain.extracted_rule_validator import ExtractedRuleValidator


def test_extracted_rule_is_valid():
    rule = ExtractedRule(
        type="LTC_EXCEPTION",
        title="Deroga LTC con perizia superiore al prezzo",
        confidence=ExtractedRuleConfidence.HIGH,
        source=ExtractedRuleSource(
            document="chebanca.pdf",
            page=2,
            original_text="Valore perizia superiore al prezzo di acquisto",
        ),
    )

    assert rule.is_valid() is True
    assert ExtractedRuleValidator.is_valid(rule) is True


def test_extracted_rule_missing_source_is_invalid():
    rule = ExtractedRule(
        type="LTC_EXCEPTION",
        title="Deroga LTC",
        confidence=ExtractedRuleConfidence.HIGH,
        source=None,
    )

    errors = ExtractedRuleValidator.validate(rule)

    assert "Missing source" in errors
    assert ExtractedRuleValidator.is_valid(rule) is False
