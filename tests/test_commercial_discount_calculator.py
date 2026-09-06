from services.commercial_discount_calculator import calculate_commercial_discounts


RULES = [
    {"rule_type": "DISCOUNT", "discount_type": "CCA_COMPLETO", "percent": 0.30, "page": 6},
    {"rule_type": "DISCOUNT", "discount_type": "CCA_ADDEBITO_RATA_020", "percent": 0.20, "page": 6},
    {"rule_type": "DISCOUNT", "discount_type": "MRI_WHITE_LABEL", "percent": 0.25, "page": 6},
    {"rule_type": "DISCOUNT", "discount_type": "GREEN", "percent": 0.25, "page": 6},
]


def test_all_discounts_are_cumulative_when_conditions_match():
    result = calculate_commercial_discounts(
        1.55,
        RULES,
        classe_energetica="A3",
        reddito_residuo=1800,
    )
    assert result["sconto_totale_percentuale"] == 1.00
    assert result["spread_finale"] == 0.55
    assert [x["percentuale"] for x in result["sconti_applicati"]] == [0.30, 0.20, 0.25, 0.25]


def test_mri_is_not_applied_at_or_below_1500_and_green_requires_a_or_b():
    result = calculate_commercial_discounts(
        1.55,
        RULES,
        classe_energetica="C",
        reddito_residuo=1500,
    )
    assert result["sconto_totale_percentuale"] == 0.50
    assert result["spread_finale"] == 1.05
    assert len(result["sconti_applicati"]) == 2


def test_green_b_is_applied():
    result = calculate_commercial_discounts(1.55, RULES, classe_energetica="B", reddito_residuo=1200)
    assert result["sconto_totale_percentuale"] == 0.75
    assert result["spread_finale"] == 0.80
