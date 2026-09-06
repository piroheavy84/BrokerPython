import re


class BlockClassifier:

    HEADER_PATTERNS = [
        "LISTINO IN CORSO",
        "STIPULE ENTRO",
        "VALIDITA OFFERTA",
        "DECORRENZA",
    ]

    INFO_PATTERNS = [
        "RETROCESS",
        "PROVVIG",
        "ISTRUTTORIA",
        "PERIZIA",
        "IMPOSTA SOSTITUTIVA",
        "ASSICURAZ",
        "POLIZZ",
    ]

    # Segnali strutturali generici di una tabella/prodotto mutuo.
    # Non contengono nomi banca e servono per evitare classifier hardcoded.
    PRODUCT_SIGNALS = [
        "FINALITA",
        "FINALITÀ",
        "LTV",
        "LTC",
        "SPREAD",
        "TASSO",
        "TAN",
        "TAEG",
        "DURATA",
        "FISSO",
        "VARIABILE",
        "EURIBOR",
        "IRS",
        "PARAMETRO",
        "IMPORTO",
        "MUTUO",
    ]

    def classify(self, blocco):

        testo = self._normalize(blocco)

        # Retrocessioni e provvigioni hanno precedenza assoluta: spesso
        # contengono parole come finalita/prodotto/tasso ma non sono listini.
        if "RETROCESS" in testo or "PROVVIG" in testo:
            return "INFO"

        # Eccezione documentale già esistente: una sezione Enasarco reale è
        # comunque un prodotto. Il criterio resta basato sul contenuto, non
        # sul nome banca.
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

        if self._looks_like_product(testo):
            return "PRODOTTO"

        if self._matches(testo, self.HEADER_PATTERNS):
            return "HEADER"

        if self._matches(testo, self.INFO_PATTERNS):
            return "INFO"

        return "UNKNOWN"

    def _looks_like_product(self, text):
        """Riconosce prodotti con evidenze multiple, senza layout banca-specifico."""

        signals = sum(1 for token in self.PRODUCT_SIGNALS if token in text)

        has_rate_type = "FISSO" in text or "VARIABILE" in text
        has_duration = (
            "DURATA" in text
            or "ANNI" in text
            or re.search(r"\b\d+\s*[-–]\s*\d+\b", text) is not None
        )
        has_percentage = re.search(r"\b\d+(?:[\.,]\d+)?\s*%", text) is not None
        has_ltv = "LTV" in text or "LTC" in text
        has_spread_or_rate = any(
            token in text
            for token in ("SPREAD", "TASSO", "TAN", "EURIBOR", "IRS")
        )
        has_purpose = "FINALITA" in text or "FINALITÀ" in text

        # Tabelle classiche con intestazioni esplicite.
        if has_ltv and has_spread_or_rate:
            return True

        if has_purpose and (has_rate_type or has_spread_or_rate):
            return True

        # Tabelle dove il PDF perde le intestazioni ma conserva righe
        # durata + tipo tasso + percentuali.
        if has_rate_type and has_duration and has_percentage:
            return True

        # Ultima rete: richiediamo almeno tre segnali finanziari distinti.
        return signals >= 3 and has_percentage

    def _normalize(self, blocco):

        if isinstance(blocco, list):
            text = " ".join(str(item) for item in blocco)
        else:
            text = str(blocco)

        return re.sub(r"\s+", " ", text.upper()).strip()

    def _matches(self, text, patterns):

        for pattern in patterns:
            if pattern in text:
                return True

        return False
