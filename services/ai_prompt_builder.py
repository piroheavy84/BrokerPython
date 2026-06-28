from domain.extracted_rule_prompt_contract import EXTRACTED_RULE_PROMPT_CONTRACT


class AIPromptBuilder:

    def build_rule_extraction_prompt(
        self,
        document_name: str,
        page_number: int,
        page_text: str,
    ) -> str:

        return f"""
{EXTRACTED_RULE_PROMPT_CONTRACT}

Document name:
{document_name}

Page number:
{page_number}

PDF text:
{page_text}
""".strip()
