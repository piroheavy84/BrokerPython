class RuleValidator:

    def validate(self, rule):

        errori = []

        if not rule.get("banca"):
            errori.append("banca")

        if not rule.get("pdf"):
            errori.append("pdf")

        if not rule.get("pagina"):
            errori.append("pagina")

        if not rule.get("finalita"):
            errori.append("finalita")

        if not rule.get("tasso"):
            errori.append("tasso")

        if rule.get("durata_min") is None:
            errori.append("durata_min")

        if rule.get("durata_max") is None:
            errori.append("durata_max")

        if rule.get("ltv_max") is None:
            errori.append("ltv_max")

        if not rule.get("spread"):
            errori.append("spread")

        return errori