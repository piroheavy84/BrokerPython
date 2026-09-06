from pathlib import Path

api = Path('api.py')
text = api.read_text(encoding='utf-8')

needle = '''    verifica_manual_banca = _verifica_parametri_manual_banca(\n        p.banca,\n        request,\n        rata\n    )\n'''
replacement = '''    # Verifica definitiva: rapporto rata/reddito e sussistenza devono usare\n    # la rata FINALE, dopo tutte le scontistiche commerciali.\n    verifica_manual_banca = _verifica_parametri_manual_banca(\n        p.banca,\n        request,\n        rata\n    )\n\n    final_residual = (\n        verifica_manual_banca\n        .get("dettagli", {})\n        .get("sussistenza", {})\n        .get("reddito_residuo")\n    )\n    if commercial_policy and final_residual is not None:\n        commercial_discount_detail["reddito_residuo"] = final_residual\n'''
if needle not in text:
    raise SystemExit('Blocco verifica finale non trovato')
text = text.replace(needle, replacement, 1)
api.write_text(text, encoding='utf-8')

engine = Path('engines/broker_engine/broker_engine.py')
text = engine.read_text(encoding='utf-8')
old = '''    def _get_tipo_tasso(self, rule):\n        if isinstance(rule["tasso"], dict):\n            return rule["tasso"].get("tipo", "")\n        return rule["tasso"]\n'''
new = '''    def _get_tipo_tasso(self, rule):\n        tasso = rule.get("tasso", "")\n        if isinstance(tasso, dict):\n            tipo = str(tasso.get("tipo") or "").strip()\n            descrizione = str(tasso.get("descrizione") or "").strip()\n            descrizione_upper = descrizione.upper()\n            if descrizione and (\n                "RINEGOZIABILE" in descrizione_upper\n                or descrizione_upper.startswith("FISSO 5")\n                or descrizione_upper.startswith("FISSO 10")\n            ):\n                return descrizione\n            return tipo or descrizione\n        return tasso\n'''
if old not in text:
    raise SystemExit('Metodo _get_tipo_tasso non trovato')
text = text.replace(old, new, 1)
engine.write_text(text, encoding='utf-8')

# trigger-v3
