from domain.extracted_rule_collection import ExtractedRuleCollection
from services.extracted_rule_mapper import ExtractedRuleMapper


class AIRuleExtractor:

    def extract(self, ai_response: dict) -> ExtractedRuleCollection:
        return ExtractedRuleMapper.from_ai_json(ai_response)


if __name__ == "__main__":

    ai_response = {
        "rules": [
            {
                "type": "LTC_EXCEPTION",
                "title": "Deroga LTC con perizia superiore al prezzo",
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
                    },
                    {
                        "type": "spread_adjustment",
                        "value": 40,
                        "unit": "bps",
                    },
                ],
                "notes": [
                    "LTV su perizia entro 80%"
                ],
                "confidence": "HIGH",
                "source": {
                    "document": "chebanca.pdf",
                    "page": 2,
                    "section": None,
                    "original_text": "Valore perizia superiore al prezzo di acquisto",
                },
            }
        ]
    }

    extractor = AIRuleExtractor()
    extracted_rules = extractor.extract(ai_response)

    print(extracted_rules.to_dict())
