from dataclasses import dataclass, field

from domain.extracted_rule import ExtractedRule


@dataclass
class ExtractedRuleCollection:
    rules: list[ExtractedRule] = field(default_factory=list)

    def add(self, rule: ExtractedRule) -> None:
        if rule.is_valid():
            self.rules.append(rule)

    def extend(self, rules: list[ExtractedRule]) -> None:
        for rule in rules:
            self.add(rule)

    def __iter__(self):
        return iter(self.rules)

    def __len__(self):
        return len(self.rules)

    def is_empty(self) -> bool:
        return len(self.rules) == 0

    def to_dict(self) -> dict:
        return {
            "rules": [rule.to_dict() for rule in self.rules]
        }
