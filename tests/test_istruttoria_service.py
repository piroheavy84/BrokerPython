from services.istruttoria_service import calculate_manual_istruttoria, normalize_istruttoria_memory


def test_fixed_istruttoria_is_not_perizia_or_percentage():
    result = calculate_manual_istruttoria({
        "istruttoria_tipo": "FISSA",
        "istruttoria_fissa_euro": 1500,
        "istruttoria_percentuale": 9,
        "istruttoria_minimo": 100,
        "istruttoria_massimo": 9999,
    }, 250000)
    assert result["importo"] == 1500
    assert result["tipo"] == "FISSA"
    assert result["percentuale"] == 0


def test_legacy_bank_stays_percentage():
    cfg = normalize_istruttoria_memory({
        "istruttoria_percentuale": 0.6,
        "istruttoria_minimo": 500,
        "istruttoria_massimo": 2500,
    })
    assert cfg["tipo"] == "PERCENTUALE"
    assert calculate_manual_istruttoria({
        "istruttoria_percentuale": 0.6,
        "istruttoria_minimo": 500,
        "istruttoria_massimo": 2500,
    }, 200000)["importo"] == 1200
