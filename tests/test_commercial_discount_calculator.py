from services.commercial_discount_calculator import (
    calculate_commercial_discounts,
    has_cca_discount_policy,
)


RULES = [
    {"rule_type": "DISCOUNT", "discount_type": "CCA_COMPLETO", "percent": 0.30, "page": 6},
    {"rule_type": "DISCOUNT", "discount_type": "CCA_ADDEBITO_RATA_020", "percent": 0.20, "page": 6},
    {"rule_type": "DISCOUNT", "discount_type": "MRI_WHITE_LABEL", "percent": 0.25, "page": 6},
    {"rule_type": "DISCOUNT", "discount_type": "GREEN", "percent": 0.20, "page": 6},
]


def test_all_discounts_are_cumulative_when_conditions_match():
    result = calculate_commercial_discounts(
        1.55,
        RULES,
        classe_energetica="A3",
        reddito_residuo=1800,
        finalita="ACQUISTO",
    )
    assert result["sconto_totale_percentuale"] == 0.95
    assert result["spread_finale"] == 0.60
    assert [x["percentuale"] for x in result["sconti_applicati"]] == [0.30, 0.20, 0.25, 0.20]


def test_mri_is_not_applied_at_or_below_1500_and_green_requires_a_or_b():
    result = calculate_commercial_discounts(
        1.55,
        RULES,
        classe_energetica="C",
        reddito_residuo=1500,
        finalita="ACQUISTO",
    )
    assert result["sconto_totale_percentuale"] == 0.50
    assert result["spread_finale"] == 1.05
    assert len(result["sconti_applicati"]) == 2


def test_green_b_is_20_bps_and_only_on_acquisto():
    result = calculate_commercial_discounts(
        1.55,
        RULES,
        classe_energetica="B",
        reddito_residuo=1200,
        finalita="ACQUISTO",
    )
    assert result["sconto_totale_percentuale"] == 0.70
    assert result["spread_finale"] == 0.85

    non_acquisto = calculate_commercial_discounts(
        1.55,
        RULES,
        classe_energetica="B",
        reddito_residuo=1200,
        finalita="SURROGA",
    )
    assert non_acquisto["sconto_totale_percentuale"] == 0.50
    assert non_acquisto["spread_finale"] == 1.05


def test_policy_is_not_invented_without_cca_rule():
    other_bank_rules = [
        {"rule_type": "DISCOUNT", "discount_type": "GREEN", "percent": 0.30},
    ]
    assert has_cca_discount_policy(RULES) is True
    assert has_cca_discount_policy(other_bank_rules) is False

    result = calculate_commercial_discounts(
        1.55,
        other_bank_rules,
        classe_energetica="C",
        reddito_residuo=1800,
        finalita="ACQUISTO",
    )
    assert result["sconto_totale_percentuale"] == 0
    assert result["spread_finale"] == 1.55
