from domain.extracted_rule import (
    ExtractedRule,
    ExtractedRuleConfidence,
    ExtractedRuleSource,
)
from domain.extracted_rule_collection import ExtractedRuleCollection


class ExtractedRuleMapper:

    @staticmethod
    def from_ai_json(data: dict) -> ExtractedRuleCollection:
        collection = ExtractedRuleCollection()

        for item in data.get("rules", []):
            source_data = item.get("source", {})

            source = ExtractedRuleSource(
                document=source_data.get("document", ""),
                page=source_data.get("page"),
                section=source_data.get("section"),
                original_text=source_data.get("original_text"),
            )

            rule = ExtractedRule(
                type=item.get("type", ""),
                title=item.get("title", ""),
                conditions=item.get("conditions", []),
                effects=item.get("effects", []),
                notes=item.get("notes", []),
                confidence=ExtractedRuleConfidence(
                    item.get("confidence", "LOW")
                ),
                source=source,
            )

            collection.add(rule)

        return collection
