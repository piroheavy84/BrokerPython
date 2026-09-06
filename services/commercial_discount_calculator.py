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


def calculate_commercial_discounts(
    spread_base,
    rules,
    classe_energetica=None,
    reddito_residuo=None,
    *,
    always_cca=True,
    always_addebito_rata=True,
    residual_threshold=1500.0,
):
    """Restituisce spread finale e dettaglio degli sconti cumulativi.

    Policy richiesta per ING:
    - CCA completo: -0,30 sempre;
    - addebito rata su conto: -0,20 sempre;
    - White Label/MRI: -0,25 solo con reddito residuo > 1.500 euro;
    - Green: -0,25 per classi energetiche A o B.

    I valori vengono prima letti dalle regole del PDF; i fallback servono solo
    per la policy esplicitamente configurata e sono visibili nel dettaglio.
    """
    base = _num(spread_base)
    applied = []

    cca = _find_rule(rules, "CCA_COMPLETO")
    if always_cca:
        applied.append(_detail(cca, 0.30, "Conto Corrente Arancio", "Sconto CCA applicato sempre"))

    addebito = _find_rule(rules, "CCA_ADDEBITO_RATA_020", "CCA_ADDEBITO_RATA")
    if always_addebito_rata:
        applied.append(_detail(addebito, 0.20, "Addebito rata su conto", "Addebito rata su conto applicato sempre"))

    mri = _find_rule(rules, "MRI_WHITE_LABEL", "WHITE_LABEL")
    residual = None if reddito_residuo is None else _num(reddito_residuo)
    if residual is not None and residual > float(residual_threshold):
        applied.append(_detail(
            mri,
            0.25,
            "White Label / residuo reddituale",
            f"Reddito residuo {residual:.2f} euro > {float(residual_threshold):.2f} euro",
        ))

    green = _find_rule(rules, "GREEN")
    energy = _energy(classe_energetica)
    if energy.startswith("A") or energy == "B":
        applied.append(_detail(green, 0.25, "Green classe A/B", f"Classe energetica {energy}"))

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
