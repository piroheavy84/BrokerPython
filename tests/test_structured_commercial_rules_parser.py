from services.structured_commercial_rules_parser import StructuredCommercialRulesParser


def test_discount_parser_preserves_conflict_without_overwriting():
    parser = StructuredCommercialRulesParser()
    text = (
        "Riepilogo scontistiche. "
        "Sconto CCA (Conto Corrente Arancio): su tutti i prodotti -0,30% per tutta la durata dell'ammortamento. "
        "Ogni mese viene applicato lo sconto sulla rata dello 0,20%. "
        "Destinatari promozione: MRI (soglia di sussistenza) > 1.500 Euro. "
        "Sconto su mutui tasso variabile, fisso, fisso rinegoziabile: -0,25% per tutta la durata dell'ammortamento. "
        "Sconto green: in caso di mutuo acquisto, se l'immobile è di classe energetica B, A o superiore, sconto di 20 bps."
    )
    rules, warnings = parser._parse_discounts(text, 6)
    types = {r.get("discount_type") for r in rules}
    assert "CONTO_CORRENTE" in types
    assert "MRI_WHITE_LABEL" in types
    assert "GREEN" in types
    cca = next(r for r in rules if r.get("discount_type") == "CONTO_CORRENTE")
    assert cca["percent"] == 0.30
    assert warnings
    assert warnings[0]["type"] == "DISCOUNT_PERCENT_CONFLICT"


def test_retrocession_table_parses_tiers_and_fixed_columns():
    parser = StructuredCommercialRulesParser()
    table = [
        ["Soglie di erogato", "Retrocessioni per tutte le finalità (No Surroga)", "Retrocessioni Surroga", "Retrocessioni Liquidità"],
        ["Fino a 80.000.000", "1,50% Da applicare su caricato da 01/01/2026", "0,80%", "1,60%"],
        ["Da 80.000.001 a 130.000.000", "1,55% Da applicare su erogato da 01/03/2026", None, None],
        ["Da 450.000.001", "1,80%", None, None],
    ]
    rules = parser._parse_retrocession_tables([table], "RETE - Retrocessioni ING 2026", 7)
    tiers = [r for r in rules if r["rule_type"] == "RETROCESSION_TIER"]
    fixed = [r for r in rules if r["rule_type"] == "RETROCESSION_FIXED"]
    assert len(tiers) == 3
    assert tiers[0]["erogato_max"] == 80000000.0
    assert tiers[0]["effective_basis"] == "CARICATO"
    assert tiers[1]["effective_basis"] == "EROGATO"
    assert any(r.get("finalita") == "SURROGA" and r.get("percent") == 0.80 for r in fixed)
    assert any(r.get("finalita") == "LIQUIDITA" and r.get("percent") == 1.60 for r in fixed)


def test_fee_ranges_are_not_product_rules():
    parser = StructuredCommercialRulesParser()
    table = [
        ["Finalità", "Spese Istruttoria", "Retrocessioni Spese Istruttoria"],
        ["Acquisto (no surroga)", "minimo 1.250€ massimo 2.250€", "Spese istruttoria applicata – minimo"],
        ["Altre finalità (no surroga)", "minimo 1.500€ massimo 2.500€", None],
    ]
    rules = parser._parse_fee_rules([table], 7)
    assert len(rules) == 2
    assert rules[0]["minimum_euro"] == 1250.0
    assert rules[0]["maximum_euro"] == 2250.0
    assert all(r["rule_type"] == "ISTRUTTORIA_RANGE" for r in rules)
