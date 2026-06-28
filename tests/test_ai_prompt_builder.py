from services.ai_prompt_builder import AIPromptBuilder


def test_prompt_contains_contract():
    builder = AIPromptBuilder()

    prompt = builder.build_rule_extraction_prompt(
        document_name="chebanca.pdf",
        page_number=2,
        page_text="Testo della pagina",
    )

    assert "You are the AI Knowledge Extractor" in prompt
    assert "You must return only valid JSON" in prompt


def test_prompt_contains_document_information():
    builder = AIPromptBuilder()

    prompt = builder.build_rule_extraction_prompt(
        document_name="chebanca.pdf",
        page_number=2,
        page_text="Pagina di test",
    )

    assert "chebanca.pdf" in prompt
    assert "2" in prompt
    assert "Pagina di test" in prompt


def test_prompt_contains_required_schema():
    builder = AIPromptBuilder()

    prompt = builder.build_rule_extraction_prompt(
        document_name="test.pdf",
        page_number=1,
        page_text="Lorem ipsum",
    )

    assert '"rules"' in prompt
    assert '"type"' in prompt
    assert '"conditions"' in prompt
    assert '"effects"' in prompt
    assert '"confidence"' in prompt
