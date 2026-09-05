"""Calcolo dell'istruttoria banca con supporto nativo a importo fisso.

La funzione e' volutamente indipendente da FastAPI per essere testabile e per
mantenere compatibilita' con le memorie banca precedenti.
"""


def _float(value, default=0.0):
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", "."))
    except (TypeError, ValueError):
        return default


def normalize_istruttoria_memory(memory):
    memory = dict(memory or {})
    tipo = str(memory.get("istruttoria_tipo") or "").strip().upper()
    fixed_present = memory.get("istruttoria_fissa_euro") not in (None, "")

    # Retrocompatibilita': le banche gia' configurate restano percentuali.
    if tipo not in {"FISSA", "PERCENTUALE"}:
        tipo = "FISSA" if fixed_present else "PERCENTUALE"

    return {
        "tipo": tipo,
        "fissa_euro": _float(memory.get("istruttoria_fissa_euro")),
        "percentuale": _float(memory.get("istruttoria_percentuale")),
        "minimo": _float(memory.get("istruttoria_minimo")),
        "massimo": _float(memory.get("istruttoria_massimo")),
    }


def calculate_manual_istruttoria(memory, importo):
    cfg = normalize_istruttoria_memory(memory)
    if cfg["tipo"] == "FISSA":
        return {
            "importo": max(0.0, cfg["fissa_euro"]),
            "tipo": "FISSA",
            "fissa_euro": max(0.0, cfg["fissa_euro"]),
            "percentuale": 0.0,
            "minimo": 0.0,
            "massimo": 0.0,
            "pagina": None,
            "source_text": "Parametro manuale Memoria Banca - importo fisso",
        }

    percentuale = max(0.0, cfg["percentuale"])
    minimo = max(0.0, cfg["minimo"])
    massimo = max(0.0, cfg["massimo"])
    value = max(0.0, _float(importo)) * percentuale / 100.0
    if minimo > 0 and value < minimo:
        value = minimo
    if massimo > 0 and value > massimo:
        value = massimo
    return {
        "importo": value,
        "tipo": "PERCENTUALE",
        "fissa_euro": 0.0,
        "percentuale": percentuale,
        "minimo": minimo,
        "massimo": massimo,
        "pagina": None,
        "source_text": "Parametro manuale Memoria Banca",
    }
