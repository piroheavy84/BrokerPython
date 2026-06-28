from domain.extracted_rule_collection import ExtractedRuleCollection
from services.ai_prompt_builder import AIPromptBuilder
from services.ai_rule_extractor import AIRuleExtractor


class BankMemoryAIService:

    def __init__(self):
        self.prompt_builder = AIPromptBuilder()
        self.rule_extractor = AIRuleExtractor()

    def build_rule_prompt(
        self,
        document_name: str,
        page_number: int,
        page_text: str,
    ) -> str:
        return self.prompt_builder.build_rule_extraction_prompt(
            document_name=document_name,
            page_number=page_number,
            page_text=page_text,
        )

    def extract_rules_from_ai_response(
        self,
        ai_response: dict,
    ) -> ExtractedRuleCollection:
        return self.rule_extractor.extract(
            ai_response
        )

    def compare_memory(
        self,
        memory,
        detected
    ):

        changes = []

        fields = [
            "eta_massima",
            "ltv_massimo",
            "prima_casa",
            "seconda_casa",
            "surroga",
            "liquidita",
            "consolidamento",
            "green"
        ]

        for field in fields:

            old_value = memory.get(
                field
            )

            new_value = detected.get(
                field
            )

            if new_value is None:
                continue

            if old_value is None:
                continue

            if old_value != new_value:

                changes.append(
                    {
                        "field": field,
                        "old": old_value,
                        "new": new_value
                    }
                )

        return changes

    def find_new_phrases(
        self,
        memory,
        detected
    ):

        known = set(
            memory.get(
                "frasi_confermate",
                []
            )
        )

        new_phrases = []

        for phrase in detected.get(
            "phrases",
            []
        ):

            if phrase not in known:

                new_phrases.append(
                    phrase
                )

        return new_phrases
