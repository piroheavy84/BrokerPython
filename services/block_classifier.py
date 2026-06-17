class BlockClassifier:

    def classify(self, blocco):

        testo = " ".join(blocco).upper()

        # -----------------------------
        # HEADER
        # -----------------------------

        if "LISTINO IN CORSO" in testo:
            return "HEADER"

        if "OFFERTA CHEBANCA" in testo:
            return "HEADER"

        if "CANALIZZAZIONI" in testo:
            return "HEADER"

        if "STIPULE ENTRO" in testo:
            return "HEADER"

        # -----------------------------
        # PRODOTTO
        # -----------------------------

        if "FINALITA" in testo:
            return "PRODOTTO"

        if "LTV" in testo:
            return "PRODOTTO"

        if "SPREAD" in testo:
            return "PRODOTTO"

        # -----------------------------
        # INFO
        # -----------------------------

        if "RETROCESS" in testo:
            return "INFO"

        if "PROVVIG" in testo:
            return "INFO"

        if "ISTRUTTORIA" in testo:
            return "INFO"

        if "PERIZIA" in testo:
            return "INFO"

        # -----------------------------

        return "UNKNOWN"