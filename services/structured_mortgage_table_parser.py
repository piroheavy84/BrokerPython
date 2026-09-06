import re

import pdfplumber


class StructuredMortgageTableParser:
    """Fallback per listini mutuo espressi come vere tabelle PDF.

    Il parser non conosce nomi banca. Si attiva solo su tabelle che espongono
    almeno le colonne "Tipo tasso" e "Durata" e una o più colonne LTV/LTC.
    È pensato come fallback quando il parser legacy non produce alcuna regola.
    """

    FINALITY_KEYWORDS = [
        "ACQUISTO",
        "SURROGA",
        "SOSTITUZIONE",
        "RISTRUTTURAZIONE",
        "RIFINANZIAMENTO",
        "LIQUIDITA",
        "CONSOLIDAMENTO",
    ]

    def parse(self, pdf_path):
        rules = []
        next_id = 1

        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                header_info = self._parse_page_header(page_text)

                for table in page.extract_tables() or []:
                    parsed = self._parse_table(
                        table=table,
                        page_number=page_number,
                        header_info=header_info,
                        start_id=next_id,
                    )
                    if parsed:
                        rules.extend(parsed)
                        next_id = max(r["id"] for r in rules) + 1

        return rules

    def _parse_table(self, table, page_number, header_info, start_id):
        if not table or len(table) < 3:
            return []

        header_index = self._find_column_header_row(table)
        if header_index is None or header_index == 0:
            return []

        column_header = [self._clean(cell) for cell in table[header_index]]
        type_col = self._find_column(column_header, "TIPO TASSO")
        duration_col = self._find_column(column_header, "DURATA")

        if type_col is None or duration_col is None:
            return []

        rate_columns = []
        for index, value in enumerate(column_header):
            if index in (type_col, duration_col):
                continue
            upper = value.upper()
            if "LTV" in upper or "LTC" in upper or "HLTV" in upper:
                rate_columns.append(index)

        if not rate_columns:
            return []

        group_row = [self._clean(cell) for cell in table[header_index - 1]]
        groups = self._forward_fill_groups(group_row, rate_columns)

        # Se la riga sopra non contiene finalità utili, la tabella non è un
        # listino prodotto compatibile con questo fallback.
        if not any(self._extract_finalities(groups.get(c, "")) for c in rate_columns):
            return []

        rules = []
        current_tasso = ""
        last_spreads = {}
        rule_id = start_id

        for row in table[header_index + 1:]:
            if not row:
                continue

            row = list(row) + [None] * max(0, len(column_header) - len(row))
            raw_tasso = self._clean(row[type_col])
            if raw_tasso:
                current_tasso = self._normalize_rate_type(raw_tasso)
                last_spreads = {}

            if not current_tasso:
                continue

            duration = self._parse_duration(self._clean(row[duration_col]))
            if duration is None:
                continue

            durata_min, durata_max = duration

            # Le celle verticalmente unite nel PDF diventano None nelle righe
            # successive: in quel caso ereditiamo lo spread della riga sopra.
            for col in rate_columns:
                cell = self._clean(row[col]) if col < len(row) else ""
                spread = self._extract_percentage(cell)
                if spread:
                    last_spreads[col] = spread
                else:
                    spread = last_spreads.get(col)

                if not spread:
                    continue

                group = groups.get(col, "")
                finalities = self._extract_finalities(group)
                if not finalities:
                    continue

                ltv_info = self._parse_ltv_header(column_header[col])
                if ltv_info is None:
                    continue

                for finalita in finalities:
                    condition = ltv_info.get("condition")
                    source_text = " | ".join(
                        part for part in (
                            group,
                            column_header[col],
                            raw_tasso or current_tasso,
                            self._clean(row[duration_col]),
                            spread,
                        ) if part
                    )

                    rule = {
                        "id": rule_id,
                        "tipo_listino": header_info.get("tipo_listino", ""),
                        "canalizzazione_da": header_info.get("canalizzazione_da", ""),
                        "canalizzazione_a": header_info.get("canalizzazione_a", ""),
                        "stipula_entro": header_info.get("stipula_entro", ""),
                        "finalita": finalita,
                        "tasso": current_tasso,
                        "durata_min": durata_min,
                        "durata_max": durata_max,
                        "ltv_max": ltv_info["ltv_max"],
                        "spread": spread,
                        "source_text": source_text,
                        "pagina": page_number,
                    }
                    if condition:
                        rule["condition"] = condition

                    rules.append(rule)
                    rule_id += 1

        return rules

    def _find_column_header_row(self, table):
        for index, row in enumerate(table[:5]):
            text = " ".join(self._clean(cell).upper() for cell in row if cell is not None)
            if "TIPO TASSO" in text and "DURATA" in text:
                return index
        return None

    def _find_column(self, row, needle):
        needle = needle.upper()
        for index, value in enumerate(row):
            if needle in value.upper():
                return index
        return None

    def _forward_fill_groups(self, row, columns):
        result = {}
        current = ""
        for col in sorted(columns):
            value = row[col] if col < len(row) else ""
            if value:
                current = value
            result[col] = current
        return result

    def _extract_finalities(self, value):
        normalized = self._normalize_text(value)
        found = []
        for keyword in self.FINALITY_KEYWORDS:
            if keyword in normalized and keyword not in found:
                found.append(keyword)
        return found

    def _normalize_rate_type(self, value):
        text = self._normalize_text(value)
        text = re.sub(r"\s+", " ", text).strip()

        if "VARIABILE" in text:
            if "NO FLOOR" in text:
                return "VARIABILE EURIBOR 3M NO FLOOR"
            return "VARIABILE"

        if "FISSO" in text and "RINEGOZIABILE" in text:
            years = re.search(r"FISSO\s*(\d+)", text)
            if years:
                return f"FISSO {years.group(1)} RINEGOZIABILE"
            return "FISSO RINEGOZIABILE"

        if "FISSO" in text:
            return "FISSO"

        return text

    def _parse_duration(self, value):
        if not value:
            return None

        value = value.replace("–", "-").replace("—", "-")
        interval = re.search(r"(\d+)\s*-\s*(\d+)", value)
        if interval:
            return int(interval.group(1)), int(interval.group(2))

        single = re.search(r"\b(\d{1,2})\b", value)
        if single:
            years = int(single.group(1))
            return years, years

        return None

    def _parse_ltv_header(self, value):
        text = self._normalize_text(value)
        numbers = [int(n) for n in re.findall(r"(\d+)\s*%", text)]
        if not numbers:
            return None

        ltv_max = max(numbers)
        condition = None

        if "HLTV" in text:
            condition = {
                "type": "HLTV",
                "max_percent": ltv_max,
                "source_text": value,
            }
        elif "LTC" in text:
            condition = {
                "type": "LTC",
                "max_percent": ltv_max,
                "source_text": value,
            }

        return {
            "ltv_max": ltv_max,
            "condition": condition,
        }

    def _extract_percentage(self, value):
        match = re.search(r"\d+(?:[\.,]\d+)?\s*%", value or "")
        if not match:
            return None
        return match.group(0).replace(" ", "")

    def _parse_page_header(self, text):
        upper = self._normalize_text(text)
        tipo_listino = ""
        if "IN VIGORE" in upper:
            tipo_listino = "IN VIGORE"
        elif "MAGAZZINO" in upper:
            tipo_listino = "MAGAZZINO"

        dates = re.findall(r"\b\d{2}/\d{2}/\d{4}\b", text)
        canalizzazione_da = ""
        canalizzazione_a = ""
        stipula_entro = ""

        dal = re.search(r"\bdal\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        al = re.search(r"\bal\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        stipula = re.search(r"stipul\w*\s+entro\s+(?:il\s+)?(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)

        if dal:
            canalizzazione_da = dal.group(1)
        elif dates:
            canalizzazione_da = dates[0]

        if al:
            canalizzazione_a = al.group(1)

        if stipula:
            stipula_entro = stipula.group(1)
        elif dates:
            stipula_entro = dates[-1]

        return {
            "tipo_listino": tipo_listino,
            "canalizzazione_da": canalizzazione_da,
            "canalizzazione_a": canalizzazione_a,
            "stipula_entro": stipula_entro,
        }

    def _clean(self, value):
        if value is None:
            return ""
        return re.sub(r"\s+", " ", str(value)).strip()

    def _normalize_text(self, value):
        text = self._clean(value).upper()
        return (
            text.replace("À", "A")
            .replace("È", "E")
            .replace("Ì", "I")
            .replace("Ò", "O")
            .replace("Ù", "U")
            .replace("’", "'")
        )
