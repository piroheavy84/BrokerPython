from services.ai_rule_extractor import AIRuleExtractor


def test_ai_rule_extractor_returns_collection():
    ai_response = {
        "rules": [
            {
                "type": "LTC_EXCEPTION",
                "title": "Deroga LTC",
                "conditions": [],
                "effects": [],
                "notes": [],
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

    extractor = AIRuleExtractor()
    collection = extractor.extract(ai_response)

    assert len(collection) == 1

    rule = list(collection)[0]

    assert rule.type == "LTC_EXCEPTION"
    assert rule.title == "Deroga LTC"
    assert rule.confidence.value == "HIGH"
    assert rule.source.document == "chebanca.pdf"
    assert rule.source.page == 2
