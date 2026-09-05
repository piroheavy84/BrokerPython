from services.bank_rule_builder import BankRuleBuilder
from models.rule_type import RuleType


def main():

    builder = BankRuleBuilder()

    page_2_text = """
    Mutuo con possibilità di finanziamento fino al 95% del prezzo di acquisto.
    Applicabile se il valore di perizia consente il rispetto dell'80%.
    Incremento spread pari a 40 bps.
    """

    ai_like_response = {
        "rules": [
            {
                "type": "LTC_EXCEPTION",
                "title": "Mutuo con deroga LTC",
                "description": page_2_text.strip(),
                "parameters": {
                    "purchase_ltv": 95,
                    "perizia_ltv": 80,
                    "spread_bps": 40,
                    "requires_appraisal_value": True,
                    "condition": "valore_perizia > prezzo_acquisto",
                    "applies_to_rate_types": [
                        "FISSO",
                        "VARIABILE"
                    ]
                },
                "source_page": 2,
                "confidence": 0.98
            }
        ]
    }

    rules = builder.build_from_ai(
        ai_like_response
    )

    for rule in rules:

        print("\n=== REGOLA ESTRATTA ===")
        print("Tipo:", rule.type)
        print("Titolo:", rule.title)
        print("Pagina:", rule.source_page)
        print("Confidenza:", rule.confidence)
        print("Parametri:", rule.parameters)

        assert rule.type == RuleType.LTC_EXCEPTION
        assert rule.parameters["purchase_ltv"] == 95
        assert rule.parameters["perizia_ltv"] == 80
        assert rule.parameters["spread_bps"] == 40
        assert "FISSO" in rule.parameters["applies_to_rate_types"]
        assert "VARIABILE" in rule.parameters["applies_to_rate_types"]

    print("\nTEST LTC OK")


if __name__ == "__main__":
    main()
