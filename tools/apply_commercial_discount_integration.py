from pathlib import Path


PATH = Path("api.py")
text = PATH.read_text(encoding="utf-8")

import_anchor = "from services.bank_eligibility_service import BankEligibilityService\n"
import_line = (
    "from services.commercial_discount_calculator import (\n"
    "    calculate_commercial_discounts,\n"
    "    has_cca_discount_policy,\n"
    ")\n"
)
if import_line not in text:
    if import_anchor not in text:
        raise SystemExit("Import anchor non trovato")
    text = text.replace(import_anchor, import_anchor + import_line, 1)

helper = '''\n\ndef _collect_commercial_discount_rules(banca):\n    rules = []\n    for page in load_bank_knowledge(banca):\n        if not isinstance(page, dict):\n            continue\n        page_number = page.get("page", page.get("pagina"))\n        commercial_rows = (\n            page.get("commercial_rules")\n            or page.get("regole_commerciali")\n            or []\n        )\n        for row in commercial_rows:\n            if not isinstance(row, dict):\n                continue\n            if str(row.get("rule_type") or "").upper() != "DISCOUNT":\n                continue\n            item = dict(row)\n            item.setdefault("page", page_number)\n            rules.append(item)\n    return rules\n\n\ndef _commercial_summary(detail):\n    rows = []\n    for item in detail.get("sconti_applicati", []) or []:\n        try:\n            pct = float(item.get("percentuale") or 0.0)\n        except Exception:\n            pct = 0.0\n        if pct <= 0:\n            continue\n        rows.append(f"{item.get('label') or 'Sconto'} -{pct:.2f}%")\n    if not rows:\n        return ""\n    return "Sconti applicati: " + "; ".join(rows)\n\n'''

function_marker = "def prodotto_to_json(\n"
if helper.strip() not in text:
    pos = text.find(function_marker)
    if pos < 0:
        raise SystemExit("prodotto_to_json non trovato")
    text = text[:pos] + helper + text[pos:]

fn_pos = text.find(function_marker)
body_start = text.find("    spread = spread_to_float(\n", fn_pos)
body_end = text.find("    if is_surroga_finalita", body_start)
if body_start < 0 or body_end < 0:
    raise SystemExit("Blocco iniziale prodotto_to_json non trovato")

new_body = '''    spread_originale = spread_to_float(\n        p.spread\n    )\n\n    commercial_rules = _collect_commercial_discount_rules(p.banca)\n    commercial_policy = has_cca_discount_policy(commercial_rules)\n\n    # Il BrokerEngine può avere già applicato il solo Green commerciale.\n    # Per una policy CCA cumulativa ripartiamo dallo spread precedente al Green,\n    # così ogni sconto viene applicato una sola volta.\n    commercial_base_spread = spread_originale\n    if commercial_policy and getattr(p, "green_sconto", None):\n        old_base = getattr(p, "spread_base", None)\n        if old_base not in (None, ""):\n            commercial_base_spread = spread_to_float(old_base)\n\n    tasso_esplicito = getattr(\n        p,\n        "tasso_esplicito",\n        False\n    )\n\n    tasso_finito_pdf = getattr(\n        p,\n        "tasso_finito_pdf",\n        None\n    )\n\n    indice_riferimento = getattr(\n        p,\n        "indice_riferimento",\n        None\n    )\n\n    if tasso_esplicito:\n        indice = 0\n        base_tasso_esplicito = percent_to_float(tasso_finito_pdf)\n        spread = spread_originale\n        tasso_finito = base_tasso_esplicito\n    else:\n        indice = calcola_indice_automatico(\n            p,\n            request\n        )\n\n        if indice == 0 and request.indice_mercato > 0:\n            indice = request.indice_mercato\n\n        spread = commercial_base_spread if commercial_policy else spread_originale\n        tasso_finito = indice + spread\n        indice_riferimento = get_indice_riferimento(p)\n\n    commercial_discount_detail = {\n        "spread_base": spread,\n        "sconti_applicati": [],\n        "sconto_totale_percentuale": 0.0,\n        "spread_finale": spread,\n        "reddito_residuo": None,\n        "soglia_reddito_residuo": 1500.0,\n    }\n\n    if commercial_policy:\n        # Prima passata: applica gli sconti non dipendenti dal residuo.\n        stage_one = calculate_commercial_discounts(\n            commercial_base_spread,\n            commercial_rules,\n            classe_energetica=request.classe_energetica,\n            reddito_residuo=None,\n            finalita=request.finalita,\n        )\n\n        if tasso_esplicito:\n            tasso_finito = max(\n                0.0,\n                base_tasso_esplicito - stage_one.get("sconto_totale_percentuale", 0.0)\n            )\n            spread = max(\n                0.0,\n                spread_originale - stage_one.get("sconto_totale_percentuale", 0.0)\n            )\n        else:\n            spread = stage_one.get("spread_finale", commercial_base_spread)\n            tasso_finito = indice + spread\n\n        rata_stage_one = calcola_rata(\n            request.importo,\n            request.durata,\n            tasso_finito\n        )\n        verifica_stage_one = _verifica_parametri_manual_banca(\n            p.banca,\n            request,\n            rata_stage_one\n        )\n        reddito_residuo = (\n            verifica_stage_one\n            .get("dettagli", {})\n            .get("sussistenza", {})\n            .get("reddito_residuo")\n        )\n\n        # Seconda passata: se dopo gli sconti base il residuo supera 1.500 euro,\n        # entra anche la White Label/MRI -0,25.\n        commercial_discount_detail = calculate_commercial_discounts(\n            commercial_base_spread,\n            commercial_rules,\n            classe_energetica=request.classe_energetica,\n            reddito_residuo=reddito_residuo,\n            finalita=request.finalita,\n        )\n\n        if tasso_esplicito:\n            total_discount = commercial_discount_detail.get(\n                "sconto_totale_percentuale",\n                0.0\n            )\n            tasso_finito = max(0.0, base_tasso_esplicito - total_discount)\n            spread = max(0.0, spread_originale - total_discount)\n        else:\n            spread = commercial_discount_detail.get(\n                "spread_finale",\n                commercial_base_spread\n            )\n            tasso_finito = indice + spread\n\n    rata = calcola_rata(\n        request.importo,\n        request.durata,\n        tasso_finito\n    )\n\n    commercial_summary = _commercial_summary(commercial_discount_detail)\n\n'''
text = text[:body_start] + new_body + text[body_end:]

old = '        "spread_label": p.spread,\n'
new = '''        "spread_label": f"{spread:.2f}%",\n        "sconti_applicati": commercial_discount_detail.get("sconti_applicati", []),\n        "sconto_totale_percentuale": commercial_discount_detail.get("sconto_totale_percentuale", 0.0),\n        "spread_base_commerciale": commercial_discount_detail.get("spread_base") if commercial_policy else None,\n        "spread_finale": spread,\n        "reddito_residuo_sconti": commercial_discount_detail.get("reddito_residuo"),\n        "soglia_reddito_residuo_sconti": commercial_discount_detail.get("soglia_reddito_residuo", 1500.0),\n'''
if old not in text:
    raise SystemExit("spread_label anchor non trovato")
text = text.replace(old, new, 1)

old = '        "prodotto_speciale": getattr(p, "prodotto_speciale", False),\n'
new = '        "prodotto_speciale": bool(commercial_policy) or getattr(p, "prodotto_speciale", False),\n'
if old not in text:
    raise SystemExit("prodotto_speciale anchor non trovato")
text = text.replace(old, new, 1)

old = '        "spread_base": getattr(p, "spread_base", None),\n        "spread_delta": getattr(p, "spread_delta", None),\n        "motivo_prodotto_speciale": getattr(p, "motivo_prodotto_speciale", None),\n'
new = '''        "spread_base": (\n            commercial_discount_detail.get("spread_base")\n            if commercial_policy\n            else getattr(p, "spread_base", None)\n        ),\n        "spread_delta": (\n            -float(commercial_discount_detail.get("sconto_totale_percentuale", 0.0) or 0.0)\n            if commercial_policy\n            else getattr(p, "spread_delta", None)\n        ),\n        "motivo_prodotto_speciale": (\n            commercial_summary\n            if commercial_policy and commercial_summary\n            else getattr(p, "motivo_prodotto_speciale", None)\n        ),\n'''
if old not in text:
    raise SystemExit("spread_base/spread_delta anchor non trovato")
text = text.replace(old, new, 1)

PATH.write_text(text, encoding="utf-8")
print("api.py aggiornato con sconti commerciali cumulativi")
