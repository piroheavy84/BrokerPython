"""Calcolo cumulativo delle scontistiche commerciali applicabili a un prodotto.

Il servizio e' separato dal parser: riceve regole gia' estratte dal PDF e dati
reali della pratica. Non inventa sconti e mantiene il dettaglio di ogni voce.
"""


def _num(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace("%", "").replace(",", ".").strip())
    except (TypeError, ValueError):
        return default


def _energy(value):
    return str(value or "").strip().upper().replace(" ", "")


def _discount_type(rule):
    return str(rule.get("discount_type") or rule.get("name") or "").strip().upper()


def _find_rule(rules, *names):
    wanted = {str(name).upper() for name in names}
    for rule in rules or []:
        if _discount_type(rule) in wanted:
            return rule
    return None


def _detail(rule, fallback_percent, label, reason):
    percent = _num((rule or {}).get("percent"), fallback_percent)
    return {
        "codice": _discount_type(rule or {}) or label.upper().replace(" ", "_"),
        "label": label,
        "percentuale": percent,
        "delta_spread": -percent,
        "applicato": True,
        "motivo": reason,
        "pagina": (rule or {}).get("page"),
        "source_text": (rule or {}).get("source_text", ""),
    }


def _is_acquisto(finalita):
    text = str(finalita or "").upper().replace("MORTGAGEPURPOSE.", "")
    return "ACQUISTO" in text


def has_cca_discount_policy(rules):
    """Attiva la policy cumulativa solo quando il PDF ha davvero una regola CCA.

    Questo evita di applicare fallback ING ad altre banche.
    """
    return _find_rule(rules, "CCA_COMPLETO") is not None


def calculate_commercial_discounts(
    spread_base,
    rules,
    classe_energetica=None,
    reddito_residuo=None,
    finalita=None,
    *,
    always_cca=True,
    always_addebito_rata=True,
    residual_threshold=1500.0,
):
    """Restituisce spread finale e dettaglio degli sconti cumulativi.

    Regole verificate sul riepilogo scontistiche ING:
    - CCA completo: -0,30;
    - addebito rata su conto: -0,20;
    - White Label/MRI: -0,25 con residuo > 1.500 euro;
    - Green: -0,20 (20 bps) solo per acquisto di immobili B, A o superiori.

    La funzione usa i valori estratti dal PDF quando presenti. I fallback sono
    usati solo per una voce gia' riconosciuta dal parser, mai per inventare una
    promozione su una banca che non la contiene.
    """
    base = _num(spread_base)
    applied = []

    cca = _find_rule(rules, "CCA_COMPLETO")
    if always_cca and cca is not None:
        applied.append(_detail(cca, 0.30, "Sconto CCA", "Sconto CCA applicato"))

    addebito = _find_rule(rules, "CCA_ADDEBITO_RATA_020", "CCA_ADDEBITO_RATA")
    if always_addebito_rata and addebito is not None:
        applied.append(_detail(addebito, 0.20, "Addebito rata CCA", "Addebito rata su Conto Corrente Arancio applicato"))

    mri = _find_rule(rules, "MRI_WHITE_LABEL", "WHITE_LABEL")
    residual = None if reddito_residuo is None else _num(reddito_residuo)
    if mri is not None and residual is not None and residual > float(residual_threshold):
        applied.append(_detail(
            mri,
            0.25,
            "White Label / MRI > 1.500 euro",
            f"Reddito residuo {residual:.2f} euro > {float(residual_threshold):.2f} euro",
        ))

    green = _find_rule(rules, "GREEN")
    energy = _energy(classe_energetica)
    if green is not None and _is_acquisto(finalita) and (energy.startswith("A") or energy == "B"):
        applied.append(_detail(
            green,
            0.20,
            "Green classe A/B",
            f"Acquisto immobile in classe energetica {energy}",
        ))

    total = round(sum(_num(row.get("percentuale")) for row in applied), 4)
    final = max(0.0, round(base - total, 4))

    return {
        "spread_base": base,
        "sconti_applicati": applied,
        "sconto_totale_percentuale": total,
        "spread_finale": final,
        "reddito_residuo": residual,
        "soglia_reddito_residuo": float(residual_threshold),
    }
