class BlockClassifier:

    HEADER_PATTERNS = [
        "LISTINO IN CORSO",
        "OFFERTA CHEBANCA",
        "CANALIZZAZIONI",
        "STIPULE ENTRO",
    ]

    PRODUCT_PATTERNS = [
        "FINALITA",
        "FINALITÀ",
        "LTV",
        "SPREAD",
    ]

    INFO_PATTERNS = [
        "RETROCESS",
        "PROVVIG",
        "ISTRUTTORIA",
        "PERIZIA",
    ]

    def classify(self, blocco):

        testo = self._normalize(blocco)

        # Le pagine di retrocessioni possono contenere parole come
        # "Finalità" e "prodotti per dismissioni Enasarco", ma non sono
        # tabelle prodotto. Devono restare INFO, altrimenti il RuleBuilder
        # crea falsi prodotti da pagina 13.
        if "RETROCESS" in testo or "PROVVIG" in testo:
            return "INFO"

        # Pagina/listino Enasarco reale: anche se inizia con "LISTINO IN CORSO"
        # deve essere trattata come prodotto, non come semplice header.
        is_real_enasarco_product = (
            "PRODOTTI PER DISMISSIONI ENASARCO" in testo
            and ("TF ENASARCO" in testo or "TV ENASARCO" in testo)
            and (
                "PREZZO DI AGGIUDICAZIONE" in testo
                or "PERIZIA ZERO" in testo
            )
        )

        if is_real_enasarco_product:
            return "PRODOTTO"

        if self._matches(testo, self.HEADER_PATTERNS):
            return "HEADER"

        if self._matches(testo, self.PRODUCT_PATTERNS):
            return "PRODOTTO"

        if self._matches(testo, self.INFO_PATTERNS):
            return "INFO"

        return "UNKNOWN"

    def _normalize(self, blocco):

        if isinstance(blocco, list):
            text = " ".join(str(item) for item in blocco)
        else:
            text = str(blocco)

        return text.upper().strip()

    def _matches(self, text, patterns):

        for pattern in patterns:
            if pattern in text:
                return True

        return False
