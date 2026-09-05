from services.structured_mortgage_table_parser import StructuredMortgageTableParser


def test_structured_table_builds_finalities_and_carries_merged_spreads():
    parser = StructuredMortgageTableParser()

    table = [
        ["", "", "ACQUISTO", None, "SURROGA - SOSTITUZIONE", None],
        [
            "Tipo tasso",
            "Durata",
            "LTV <= 50%",
            "50%< LTV <= 70%",
            "LTV <= 50%",
            "50%< LTV <= 70%",
        ],
        ["Variabile Euribor 3m (no floor)", "10", "1,45%", "1,50%", "1,95%", "2,00%"],
        [None, "11 - 15", None, None, None, None],
        ["Tasso Fisso", "20", "1,90%", "1,95%", "2,50%", "2,55%"],
    ]

    rules = parser._parse_table(
        table=table,
        page_number=2,
        header_info={
            "tipo_listino": "IN VIGORE",
            "canalizzazione_da": "23/03/2026",
            "canalizzazione_a": "",
            "stipula_entro": "10/06/2026",
        },
        start_id=1,
    )

    # ACQUISTO: 2 colonne. SURROGA e SOSTITUZIONE: 2 colonne x 2 finalità.
    # Tre righe durata => 18 regole.
    assert len(rules) == 18

    inherited = [
        r for r in rules
        if r["finalita"] == "ACQUISTO"
        and r["durata_min"] == 11
        and r["durata_max"] == 15
        and r["ltv_max"] == 50
    ]
    assert len(inherited) == 1
    assert inherited[0]["spread"] == "1,45%"
    assert inherited[0]["tasso"] == "VARIABILE EURIBOR 3M NO FLOOR"

    surroga = [
        r for r in rules
        if r["finalita"] == "SURROGA"
        and r["durata_min"] == 20
        and r["ltv_max"] == 70
    ]
    assert len(surroga) == 1
    assert surroga[0]["spread"] == "2,55%"
    assert surroga[0]["tasso"] == "FISSO"


def test_structured_table_rejects_non_product_tables():
    parser = StructuredMortgageTableParser()

    retrocessioni = [
        ["Soglie di erogato", "Retrocessioni"],
        ["Fino a 80.000.000", "1,50%"],
    ]

    assert parser._parse_table(
        table=retrocessioni,
        page_number=7,
        header_info={},
        start_id=1,
    ) == []
