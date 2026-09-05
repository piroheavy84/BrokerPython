from services.structured_commercial_rules_parser import StructuredCommercialRulesParser


def test_discount_parser_separates_cca_white_label_addebito_and_green():
    parser = StructuredCommercialRulesParser()
    text = (
        "Riepilogo scontistiche ING. "
        "1) ScontoCCA (Conto Corrente Arancio): su tutti i prodotti -0,30%per tutta la durata dell'ammortamento. "
        "Requisiti: Accredito stipendio/pensione o entrata di almeno 1.000 Euro mensili entro 6 mesi dall'erogazione. "
        "Addebito rata su CCA. Mantenimento di quanto sopra per tutta la durata del mutuo. "
        "Specifiche: lo sconto va applicato solo sulla quota interessi, non quota capitale. "
        "2) Destinatari della promozione: Nuovi richiedenti mutuo White Label che abbiano un MRI (soglia di sussistenza) > 1.500 Euro "
        "Sconto su mutui tasso variabile, fisso, fisso rinegoziabile: -0,25% per tutta la durata dell'ammortamento. "
        "Lo sconto è cumulabile con lo sconto di 0,20% per addebito rate mutuo su Conto Corrente Arancio. "
        "3) Sconto green: in caso di mutuo acquisto, se l'immobile è di classe energetica B, A o superiore, è possibile ricevere automaticamente lo sconto di 20bps."
    )
    rules, warnings = parser._parse_discounts(text, 6)
    types = {r.get("discount_type") for r in rules}
    assert types == {"CCA_COMPLETO", "MRI_WHITE_LABEL", "CCA_ADDEBITO_RATA_020", "GREEN"}
    assert warnings == []

    cca = next(r for r in rules if r["discount_type"] == "CCA_COMPLETO")
    assert cca["percent"] == 0.30
    assert cca["application"] == "SCONTO_SU_QUOTA_INTERESSI_RATA_MENSILE"
    assert len(cca["requirements"]) == 3

    white = next(r for r in rules if r["discount_type"] == "MRI_WHITE_LABEL")
    assert white["percent"] == 0.25
    assert white["mri_min_exclusive"] == 1500.0
    assert "CCA_ADDEBITO_RATA_020" in white["cumulative_with"]

    debit = next(r for r in rules if r["discount_type"] == "CCA_ADDEBITO_RATA_020")
    assert debit["percent"] == 0.20
    assert debit["requirement"]["code"] == "ADDEBITO_RATA_CCA"

    green = next(r for r in rules if r["discount_type"] == "GREEN")
    assert green["basis_points"] == 20
    assert green["percent"] == 0.20


def test_white_label_is_not_created_without_white_label_context():
    parser = StructuredCommercialRulesParser()
    text = "MRI (soglia di sussistenza) > 1.500 Euro. Sconto su mutui tasso variabile, fisso, fisso rinegoziabile: -0,25% per tutta la durata dell'ammortamento."
    rules, _ = parser._parse_discounts(text, 6)
    assert not any(r.get("discount_type") == "MRI_WHITE_LABEL" for r in rules)


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
