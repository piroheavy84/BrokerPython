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

    def _finality_values(self, rule):
        value = rule.get("finalita")
        if isinstance(value, list):
            return [str(item) for item in value if item]
        if value:
            return [str(value)]
        return ["MANCANTE"]

    def _rate_label(self, rule):
        value = rule.get("tasso")
        if isinstance(value, dict):
            return str(value.get("descrizione") or value.get("tipo") or "MANCANTE")
        return str(value or "MANCANTE")

    def _listino_label(self, rule):
        return str(rule.get("tipo_listino") or "NON_CLASSIFICATO").upper()

    def _ratio_label(self, rule):
        condition = rule.get("condition") or {}
        ratio_type = str(condition.get("type") or "LTV").upper()
        maximum = condition.get("max_percent")
        if maximum is None:
            maximum = rule.get("ltv_max")
        return f"{ratio_type} <= {maximum}%" if maximum is not None else f"{ratio_type} MANCANTE"

    def build(self, banca):
        rules, path = self._load_rules(banca)
        by_page = defaultdict(list)
        finalita = Counter()
        tassi = Counter()
        ratios = Counter()
        listini = Counter()
        anomalie = []

        for rule in rules:
            page = rule.get("pagina")
            by_page[page].append(rule)
            for finalita_value in self._finality_values(rule):
                finalita[finalita_value] += 1
            tassi[self._rate_label(rule)] += 1
            ratios[self._ratio_label(rule)] += 1
            listini[self._listino_label(rule)] += 1

            if not rule.get("finalita"):
                anomalie.append({"tipo": "FINALITA_MANCANTE", "pagina": page, "id": rule.get("id")})
            if not rule.get("tasso"):
                anomalie.append({"tipo": "TASSO_MANCANTE", "pagina": page, "id": rule.get("id")})
            if rule.get("ltv_max") is None:
                anomalie.append({"tipo": "RAPPORTO_MANCANTE", "pagina": page, "id": rule.get("id")})
            if rule.get("durata_min") is None or rule.get("durata_max") is None:
                anomalie.append({"tipo": "DURATA_MANCANTE", "pagina": page, "id": rule.get("id")})
            if not rule.get("spread"):
                anomalie.append({"tipo": "SPREAD_MANCANTE", "pagina": page, "id": rule.get("id")})

        pages = []
        for page in self._sort_values(by_page.keys()):
            page_rules = by_page[page]
            page_finalita = Counter()
            for rule in page_rules:
                for value in self._finality_values(rule):
                    page_finalita[value] += 1
            page_tassi = Counter(self._rate_label(r) for r in page_rules)
            page_ratios = Counter(self._ratio_label(r) for r in page_rules)
            page_listini = Counter(self._listino_label(r) for r in page_rules)
            durations = sorted({
                (r.get("durata_min"), r.get("durata_max"))
                for r in page_rules
                if r.get("durata_min") is not None and r.get("durata_max") is not None
            })
            pages.append({
                "pagina": page,
                "numero_regole": len(page_rules),
                "tipo_listino": dict(page_listini),
                "finalita": dict(page_finalita),
                "tassi": dict(page_tassi),
                "durate": [{"da": a, "a": b} for a, b in durations],
                "rapporti": dict(page_ratios),
                "spread_distinti": self._sort_values({
                    str(r.get("spread")) for r in page_rules if r.get("spread")
                }),
            })

        return {
            "database": path,
            "numero_regole": len(rules),
            "pagine_con_regole": [row["pagina"] for row in pages],
            "tipo_listino": dict(listini),
            "finalita": dict(finalita),
            "tassi": dict(tassi),
            "rapporti": dict(ratios),
            "per_pagina": pages,
            "anomalie": anomalie[:200],
            "numero_anomalie": len(anomalie),
        }
