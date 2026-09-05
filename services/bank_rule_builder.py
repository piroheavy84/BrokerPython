from models.bank_rule import BankRule
from models.rule_type import RuleType


class BankRuleBuilder:

    def build(
        self,
        page_number: int,
        title: str,
        description: str,
        parameters: dict,
        rule_type: RuleType,
        confidence: float = 1.0,
    ) -> BankRule:

        return BankRule(
            type=rule_type,
            title=title,
            description=description,
            parameters=parameters,
            source_page=page_number,
            confidence=confidence,
        )

    def build_from_ai(
        self,
        ai_response: dict,
    ) -> list[BankRule]:

        rules = []

        for item in ai_response.get("rules", []):

            try:

                rule = BankRule(
                    type=RuleType(item.get("type")),
                    title=item.get("title", ""),
                    description=item.get("description", ""),
                    parameters=item.get("parameters", {}),
                    source_page=item.get("source_page", 0),
                    confidence=item.get("confidence", 1.0),
                )

                rules.append(rule)

            except Exception as e:

                print(f"Errore nella conversione della regola AI: {e}")

        return rules


if __name__ == "__main__":

    builder = BankRuleBuilder()

    rule = builder.build(
        page_number=2,
        title="LTC CheBanca",
        description="Mutuo LTC con deroga fino al 95%",
        rule_type=RuleType.LTC_EXCEPTION,
        parameters={
            "purchase_ltv": 95,
            "perizia_ltv": 80,
            "spread_bps": 40,
        },
    )

    print("\n=== TEST BUILD MANUALE ===")
    print(rule)

    ai_json = {
        "rules": [
            {
                "type": "LTC_EXCEPTION",
                "title": "LTC CheBanca",
                "description": "Mutuo LTC",
                "parameters": {
                    "purchase_ltv": 95,
                    "perizia_ltv": 80,
                    "spread_bps": 40,
                },
                "source_page": 2,
                "confidence": 0.98,
            }
        ]
    }

    rules = builder.build_from_ai(ai_json)

    print("\n=== TEST BUILD DA AI ===")

    for r in rules:
        print(r)
