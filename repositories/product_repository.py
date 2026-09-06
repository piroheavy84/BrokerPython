class ProductRepository:

    def __init__(
        self,
        database
    ):
        self.database = database

    def _preserve_specific_rate_type(self, rule):
        """Non perdere la descrizione specifica del prodotto tasso.

        Alcuni import/normalizzatori legacy rappresentano il tasso come
        {"tipo": "FISSO", "descrizione": "FISSO 5 RINEGOZIABILE"}.
        Il motore deve ricevere la variante specifica, altrimenti Fisso 5 e
        Fisso 10 collassano entrambi nel generico FISSO.
        """
        if not isinstance(rule, dict):
            return rule

        tasso = rule.get("tasso")
        if not isinstance(tasso, dict):
            return rule

        tipo = str(tasso.get("tipo") or "").strip()
        descrizione = str(tasso.get("descrizione") or "").strip()
        if not descrizione:
            return rule

        tipo_upper = tipo.upper()
        descrizione_upper = descrizione.upper()
        specifica = (
            "RINEGOZIABILE" in descrizione_upper
            or descrizione_upper.startswith("FISSO 5")
            or descrizione_upper.startswith("FISSO 10")
        )
        if specifica and descrizione_upper != tipo_upper:
            normalized = dict(rule)
            normalized_tasso = dict(tasso)
            normalized_tasso["tipo"] = descrizione
            normalized["tasso"] = normalized_tasso
            return normalized

        return rule

    def all(self):
        return [
            self._preserve_specific_rate_type(rule)
            for rule in self.database.get_all()
        ]

    def by_bank(
        self,
        banca
    ):
        risultati = []

        for r in self.all():
            if r["banca"] == banca:
                risultati.append(r)

        return risultati

    def count(self):
        return len(
            self.database.get_all()
        )
