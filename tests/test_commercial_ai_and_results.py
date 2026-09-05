from engines.broker_engine.broker_engine import BrokerEngine
from services.commercial_ai_fallback import CommercialAiFallback
from services.structured_commercial_rules_parser import StructuredCommercialRulesParser


class Request:
    finalita = "ACQUISTO"
    classe_energetica = "B"


def test_real_pdf_spacing_extracts_white_label():
    parser = StructuredCommercialRulesParser()
    text = (
        "2) Destinatari della promozione: Nuovi richiedenti mutuo White Label "
        "che abbiano un MRI (soglia di sussistenza) > 1.500 Euro "
        "Scontosu mutui tasso variabile, fisso, fisso rinegoziabile: "
        "-0,25%per tutta la durata dell'ammortamento "
        "È cumulabile con lo sconto di 0,20% per addebito rate mutuo su Conto Corrente Arancio."
    )
    rules, _ = parser._parse_discounts(text, 6)
    white = [r for r in rules if r.get("discount_type") == "MRI_WHITE_LABEL"]
    assert len(white) == 1
    assert white[0]["percent"] == 0.25
    assert white[0]["mri_min_exclusive"] == 1500.0


def test_ai_fallback_detects_only_uncovered_discount_values():
    fallback = CommercialAiFallback()
    text = (
        "Sconto CCA: -0,30% per tutta la durata\n"
        "Scontosu mutui White Label: -0,25%per tutta la durata\n"
        "Tasso di esempio 3,17%\n"
        "Sconto green 20bps"
    )
    existing = [
        {"rule_type": "DISCOUNT", "percent": 0.30},
        {"rule_type": "DISCOUNT", "percent": 0.20},
    ]
    assert fallback._missing_discount_values(text, existing) == {0.25}


def test_commercial_green_is_applied_only_to_same_bank():
    engine = BrokerEngine()
    rules = [{
        "banca": "ING",
        "spread": "1,50%",
        "tasso_esplicito": False,
        "promozione": None,
    }]
    knowledge = [
        {
            "banca": "ING",
            "page": 6,
            "commercial_rules": [
                {
                    "rule_type": "DISCOUNT",
                    "discount_type": "GREEN",
                    "name": "Sconto Green",
                    "percent": 0.20,
                    "basis_points": 20,
                    "automatic": True,
                    "finalita": ["ACQUISTO"],
                    "classi_energetiche": ["A_SUPERIORE", "A", "B"],
                },
                {
                    "rule_type": "DISCOUNT",
                    "discount_type": "MRI_WHITE_LABEL",
                    "name": "White Label",
                    "percent": 0.25,
                },
            ],
        },
        {
            "banca": "ALTRA BANCA",
            "page": 2,
            "commercial_rules": [
                {"rule_type": "DISCOUNT", "discount_type": "GREEN", "name": "Altro", "percent": 0.90, "automatic": True}
            ],
        },
    ]
    result = engine._decorate_commercial_promotions(rules, Request(), knowledge)[0]
    assert result["spread"] == "1,30%"
    assert result["green_sconto"] == 0.20
    assert result["promozione"] == "GREEN"
    assert "White Label -0.25% da verificare" in result["motivo_prodotto_speciale"]
    assert "0.90" not in result["motivo_prodotto_speciale"]
