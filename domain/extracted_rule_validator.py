from domain.extracted_rule import ExtractedRule


class ExtractedRuleValidator:

    @staticmethod
    def validate(rule: ExtractedRule) -> list[str]:
        errors: list[str] = []

        if not rule.type:
            errors.append("Missing rule type")

        if not rule.title:
            errors.append("Missing title")

        if rule.source is None:
            errors.append("Missing source")

        if rule.confidence is None:
            errors.append("Missing confidence")

        return errors

    @staticmethod
    def is_valid(rule: ExtractedRule) -> bool:
        return len(ExtractedRuleValidator.validate(rule)) == 0
