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

        testo = self._normalize(
            blocco
        )

        if self._matches(
            testo,
            self.HEADER_PATTERNS
        ):
            return "HEADER"

        if self._matches(
            testo,
            self.PRODUCT_PATTERNS
        ):
            return "PRODOTTO"

        if self._matches(
            testo,
            self.INFO_PATTERNS
        ):
            return "INFO"

        return "UNKNOWN"

    def _normalize(
        self,
        blocco
    ):

        if isinstance(blocco, list):
            text = " ".join(
                str(item)
                for item in blocco
            )
        else:
            text = str(blocco)

        return text.upper().strip()

    def _matches(
        self,
        text,
        patterns
    ):

        for pattern in patterns:

            if pattern in text:
                return True

        return False
