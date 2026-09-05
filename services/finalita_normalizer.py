import re
import unicodedata


class FinalitaNormalizer:
    """
    Normalizza le finalità provenienti da Flutter e dai PDF in codici interni.

    Obiettivo:
    - non dipendere dalle diciture esatte della banca;
    - non confondere RISTRUTTURAZIONE con ACQUISTO + RISTRUTTURAZIONE;
    - mantenere Prima Casa / Seconda Casa fuori dalla finalità: quella è tipologia immobile.
    """

    ACQUISTO = "ACQUISTO"
    ACQUISTO_SOSTITUZIONE = "ACQUISTO_SOSTITUZIONE"
    RISTRUTTURAZIONE = "RISTRUTTURAZIONE"
    ACQUISTO_RISTRUTTURAZIONE = "ACQUISTO_RISTRUTTURAZIONE"
    SOSTITUZIONE = "SOSTITUZIONE"
    SOSTITUZIONE_RISTRUTTURAZIONE = "SOSTITUZIONE_RISTRUTTURAZIONE"
    SURROGA = "SURROGA"
    RIFINANZIAMENTO = "RIFINANZIAMENTO"
    LIQUIDITA = "LIQUIDITA"
    CONSOLIDAMENTO = "CONSOLIDAMENTO"
    COSTRUZIONE = "COSTRUZIONE"
    DISMISSIONI_ENASARCO = "DISMISSIONI_ENASARCO"

    def normalize_text(self, value):
        if value is None:
            return ""

        text = str(value).strip()
        text = text.replace("MortgagePurpose.", "")
        text = text.replace("MortgageRateType.", "")

        # camelCase Flutter -> parole separate
        text = re.sub(r"([a-z])([A-Z])", r"\1 \2", text)

        text = text.replace("+", " + ")
        text = text.replace("&", " + ")
        text = re.sub(r"\bPIU\b", "+", text, flags=re.IGNORECASE)
        text = re.sub(r"\bPIÙ\b", "+", text, flags=re.IGNORECASE)

        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = text.upper()
        text = text.replace("’", "'")
        text = text.replace("`", "'")
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def split_pdf_finalita(self, value):
        text = self.normalize_text(value)
        if not text:
            return []

        text = text.replace("FINALITA'", "")
        text = text.replace("FINALITA", "")
        text = re.sub(r"GRUPPO\s*\d+\s*:?", "", text)
        text = re.sub(r"\bFINALITA\b", "", text)
        text = text.replace("–", "-").replace("—", "-")

        # Separiamo solo i trattini/elenco, non il + delle finalità composte.
        parts = re.split(r"\s+-\s+|;|,|\n", text)

        cleaned = []
        for part in parts:
            part = re.sub(r"\s+", " ", part).strip(" -:")
            if not part:
                continue
            if part in {"DURATA", "TABELLA SPREAD"}:
                continue
            cleaned.append(part)

        return cleaned

    def code_for(self, value):
        text = self.normalize_text(value)
        if not text:
            return None

        # Ordine importante: prima le finalità composte, poi quelle semplici.
        if "ENASARCO" in text or "DISMISSION" in text:
            return self.DISMISSIONI_ENASARCO

        if "SURROGA" in text:
            return self.SURROGA

        if "RIFINANZI" in text:
            return self.RIFINANZIAMENTO

        if "LIQUID" in text:
            return self.LIQUIDITA

        if "CONSOLID" in text:
            return self.CONSOLIDAMENTO

        if "COSTRU" in text:
            return self.COSTRUZIONE

        has_acquisto = "ACQUIST" in text or "PRIMA CASA" in text or "SECONDA CASA" in text
        has_ristrutturazione = "RISTRUTT" in text
        has_sostituzione = "SOSTITUZ" in text

        if has_sostituzione and has_ristrutturazione:
            return self.SOSTITUZIONE_RISTRUTTURAZIONE

        if has_acquisto and has_ristrutturazione:
            return self.ACQUISTO_RISTRUTTURAZIONE

        if has_acquisto and has_sostituzione:
            return self.ACQUISTO_SOSTITUZIONE

        if has_ristrutturazione:
            return self.RISTRUTTURAZIONE

        if has_sostituzione:
            return self.SOSTITUZIONE

        if has_acquisto:
            return self.ACQUISTO

        return None

    def codes_for_pdf_value(self, value):
        codes = []
        for part in self.split_pdf_finalita(value):
            code = self.code_for(part)
            if code and code not in codes:
                codes.append(code)
        if not codes:
            code = self.code_for(value)
            if code:
                codes.append(code)
        return codes

    def codes_for_list(self, values):
        if values is None:
            return []

        if isinstance(values, (list, tuple, set)):
            raw_values = list(values)
        else:
            raw_values = [values]

        codes = []
        for value in raw_values:
            for code in self.codes_for_pdf_value(value):
                if code not in codes:
                    codes.append(code)
        return codes

    def request_code(self, value):
        return self.code_for(value)

    def match(self, requested, available_values):
        requested_code = self.request_code(requested)
        if not requested_code:
            return False
        return requested_code in self.codes_for_list(available_values)

    def is_simple_purchase(self, value):
        return self.request_code(value) == self.ACQUISTO

    def is_renovation_related(self, value):
        return self.request_code(value) in {
            self.RISTRUTTURAZIONE,
            self.ACQUISTO_RISTRUTTURAZIONE,
            self.SOSTITUZIONE_RISTRUTTURAZIONE,
        }
