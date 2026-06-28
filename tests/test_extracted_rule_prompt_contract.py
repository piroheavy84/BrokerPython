from domain.extracted_rule_prompt_contract import EXTRACTED_RULE_PROMPT_CONTRACT


def test_prompt_contract_contains_required_schema_fields():
    assert "rules" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "type" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "title" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "conditions" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "effects" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "confidence" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "source" in EXTRACTED_RULE_PROMPT_CONTRACT


def test_prompt_contract_contains_allowed_confidence_values():
    assert "HIGH" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "MEDIUM" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "LOW" in EXTRACTED_RULE_PROMPT_CONTRACT


def test_prompt_contract_contains_allowed_rule_types():
    assert "LTV" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "LTC_EXCEPTION" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "SPREAD" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "RATE" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "AGE" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "PURPOSE" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "PROPERTY" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "GREEN" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "CONSAP" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "GUARANTEE" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "DEROGATION" in EXTRACTED_RULE_PROMPT_CONTRACT
    assert "NOTE" in EXTRACTED_RULE_PROMPT_CONTRACT
