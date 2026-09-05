from engines.broker_engine.broker_engine import BrokerEngine


def _rule(listino, pagina):
    return {
        "banca": "BANCA TEST",
        "tipo_listino": listino,
        "finalita": ["ACQUISTO"],
        "tasso": {"tipo": "FISSO", "descrizione": "FISSO"},
        "durata_min": 10,
        "durata_max": 30,
        "ltv_max": 80,
        "spread": "2,00%",
        "pagina": pagina,
        "pdf": "test.pdf",
    }


def test_in_vigore_esclude_magazzino_per_stessa_banca():
    engine = BrokerEngine()
    rules = [_rule("IN VIGORE", 2), _rule("MAGAZZINO", 4)]
    selected = engine._filter_preferred_listino(rules)
    assert len(selected) == 1
    assert selected[0]["tipo_listino"] == "IN VIGORE"
    assert selected[0]["pagina"] == 2


def test_legacy_senza_classificazione_resta_invariato():
    engine = BrokerEngine()
    rules = [_rule("", 2), _rule("", 3)]
    selected = engine._filter_preferred_listino(rules)
    assert selected == rules


def test_precedenza_e_calcolata_per_banca():
    engine = BrokerEngine()
    active = _rule("IN VIGORE", 2)
    warehouse = _rule("MAGAZZINO", 4)
    other = _rule("MAGAZZINO", 7)
    other["banca"] = "ALTRA BANCA"
    selected = engine._filter_preferred_listino([active, warehouse, other])
    assert active in selected
    assert warehouse not in selected
    assert other in selected
