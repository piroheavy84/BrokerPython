from services.extracted_rule_mapper import ExtractedRuleMapper


def test_extracted_rule_mapper_from_ai_json():
    ai_json = {
        "rules": [
            {
                "type": "LTC_EXCEPTION",
                "title": "Deroga LTC",
                "conditions": [
                    {
                        "field": "appraisal_value",
                        "operator": ">",
                        "value_field": "purchase_price",
                    }
                ],
                "effects": [
                    {
                        "type": "max_ltc",
                        "value": 95,
                        "unit": "percent",
                    }
                ],
                "notes": ["LTV su perizia massimo 80%"],
                "confidence": "HIGH",
                "source": {
                    "document": "chebanca.pdf",
                    "page": 2,
                    "section": None,
                    "original_text": "Testo originale",
                },
            }
        ]
    }

    collection = ExtractedRuleMapper.from_ai_json(ai_json)

    assert len(collection) == 1

    rule = list(collection)[0]

    assert rule.type == "LTC_EXCEPTION"
    assert rule.title == "Deroga LTC"
    assert rule.conditions[0]["field"] == "appraisal_value"
    assert rule.effects[0]["type"] == "max_ltc"
    assert rule.notes[0] == "LTV su perizia massimo 80%"
    assert rule.confidence.value == "HIGH"
    assert rule.source.document == "chebanca.pdf"
    assert rule.source.page == 2
