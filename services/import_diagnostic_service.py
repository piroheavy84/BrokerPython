import json
import os
from collections import Counter, defaultdict


class ImportDiagnosticService:
    """Riepilogo semantico compatto delle regole importate per una banca."""

    def _slug(self, value):
        return str(value or "").lower().replace(" ", "_")

    def _load_rules(self, banca):
        path = os.path.join("output", f"{self._slug(banca)}_index.json")
        if not os.path.exists(path):
            return [], path
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, list) else [], path

    def _sort_values(self, values):
        def key(value):
            try:
                return (0, float(value))
            except Exception:
                return (1, str(value))
        return sorted(values, key=key)

    def build(self, banca):
        rules, path = self._load_rules(banca)
        by_page = defaultdict(list)
        finalita = Counter()
        tassi = Counter()
        ltv = Counter()
        anomalie = []

        for rule in rules:
            page = rule.get("pagina")
            by_page[page].append(rule)
            finalita[str(rule.get("finalita") or "MANCANTE")] += 1
            tassi[str(rule.get("tasso") or "MANCANTE")] += 1
            ltv[str(rule.get("ltv_max") if rule.get("ltv_max") is not None else "MANCANTE")] += 1

            if not rule.get("finalita"):
                anomalie.append({"tipo": "FINALITA_MANCANTE", "pagina": page, "id": rule.get("id")})
            if not rule.get("tasso"):
                anomalie.append({"tipo": "TASSO_MANCANTE", "pagina": page, "id": rule.get("id")})
            if rule.get("ltv_max") is None:
                anomalie.append({"tipo": "LTV_MANCANTE", "pagina": page, "id": rule.get("id")})
            if rule.get("durata_min") is None or rule.get("durata_max") is None:
                anomalie.append({"tipo": "DURATA_MANCANTE", "pagina": page, "id": rule.get("id")})
            if not rule.get("spread"):
                anomalie.append({"tipo": "SPREAD_MANCANTE", "pagina": page, "id": rule.get("id")})

        pages = []
        for page in self._sort_values(by_page.keys()):
            page_rules = by_page[page]
            page_finalita = Counter(str(r.get("finalita") or "MANCANTE") for r in page_rules)
            page_tassi = Counter(str(r.get("tasso") or "MANCANTE") for r in page_rules)
            durations = sorted({
                (r.get("durata_min"), r.get("durata_max"))
                for r in page_rules
                if r.get("durata_min") is not None and r.get("durata_max") is not None
            })
            page_ltv = self._sort_values({
                r.get("ltv_max") for r in page_rules if r.get("ltv_max") is not None
            })
            pages.append({
                "pagina": page,
                "numero_regole": len(page_rules),
                "finalita": dict(page_finalita),
                "tassi": dict(page_tassi),
                "durate": [
                    {"da": minimum, "a": maximum}
                    for minimum, maximum in durations
                ],
                "ltv_ltc": page_ltv,
                "spread_distinti": self._sort_values({
                    str(r.get("spread")) for r in page_rules if r.get("spread")
                }),
            })

        # Le pagine senza regole sono importanti quanto quelle con regole:
        # evidenziano note/sconti/retrocessioni che non devono diventare prodotti.
        return {
            "database": path,
            "numero_regole": len(rules),
            "pagine_con_regole": [row["pagina"] for row in pages],
            "finalita": dict(finalita),
            "tassi": dict(tassi),
            "ltv_ltc": dict(ltv),
            "per_pagina": pages,
            "anomalie": anomalie[:200],
            "numero_anomalie": len(anomalie),
        }
