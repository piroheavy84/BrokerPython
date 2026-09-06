import re

import pdfplumber


class StructuredCommercialRulesParser:
    """Estrae regole commerciali non-prodotto da PDF strutturati."""

    def parse(self, pdf_path):
        by_page = {}
        with pdfplumber.open(pdf_path) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                tables = page.extract_tables() or []
                rules = []
                warnings = []
                if self._looks_like_discount_page(text):
                    discount_rules, discount_warnings = self._parse_discounts(text, page_number)
                    rules.extend(discount_rules)
                    warnings.extend(discount_warnings)
                if self._looks_like_retrocession_page(text):
                    rules.extend(self._parse_retrocession_tables(tables, text, page_number))
                    rules.extend(self._parse_cpi_commissions(text, page_number))
                    rules.extend(self._parse_broker_limit(text, page_number))
                    rules.extend(self._parse_fee_rules(tables, page_number))
                if rules or warnings:
                    by_page[page_number] = {"rules": rules, "warnings": warnings}
        return by_page

    def _looks_like_discount_page(self, text):
        upper = self._norm(text)
        return "SCONT" in upper and ("PROMOZ" in upper or "CONTO CORRENTE" in upper or "GREEN" in upper or "CCA" in upper)

    def _looks_like_retrocession_page(self, text):
        upper = self._norm(text)
        return "RETROCESSION" in upper and "SOGLIE DI EROGATO" in upper

    def _parse_discounts(self, text, page):
        normalized = re.sub(r"\s+", " ", text)
        rules = []
        warnings = []

        cca = re.search(
            r"Sconto\s*CCA\s*\(Conto Corrente Arancio\).*?su tutti i prodotti\s*-?\s*(\d+[,.]\d+)\s*%\s*per tutta la durata dell.?ammortamento",
            normalized,
            re.I,
        )
        if cca:
            cca_percent = self._pct(cca.group(1))
            rules.append({
                "rule_type": "DISCOUNT", "discount_type": "CCA_COMPLETO",
                "name": "Sconto CCA (Conto Corrente Arancio)", "percent": cca_percent,
                "scope": "TUTTI_I_PRODOTTI", "duration": "TUTTA_DURATA_AMMORTAMENTO",
                "application": "SCONTO_SU_QUOTA_INTERESSI_RATA_MENSILE",
                "requirements": [
                    {"code": "ACCREDITO_ENTRATA", "description": "Accredito stipendio/pensione o entrata di almeno 1.000 Euro mensili entro 6 mesi dall'erogazione", "minimum_monthly_euro": 1000, "within_months_from_disbursement": 6},
                    {"code": "ADDEBITO_RATA_CCA", "description": "Addebito rata mutuo su Conto Corrente Arancio"},
                    {"code": "MANTENIMENTO_REQUISITI", "description": "Mantenimento dei requisiti per tutta la durata del mutuo; in caso contrario si perde il diritto alla scontistica"},
                ],
                "calculation": {"formula": "CAPITALE_RESIDUO_X_0_002_X_ANNI_MUTUO_DIVISO_360", "note": "Il PDF specifica l'applicazione sulla quota interessi e riporta un esempio mensile."},
                "page": page, "source_text": cca.group(0),
            })

            # Il documento reale puo' riportare una percentuale diversa nell'esempio
            # rispetto al titolo della promozione. Non scegliamo in silenzio.
            example = re.search(
                r"Ogni\s+mese.*?sconto.*?rata.*?(\d+[,.]\d+)\s*(?:%|sul capitale residuo)",
                normalized,
                re.I,
            )
            if example:
                example_percent = self._pct(example.group(1))
                if abs(example_percent - cca_percent) > 0.0001:
                    warnings.append({
                        "type": "SOURCE_INCONSISTENCY",
                        "page": page,
                        "field": "CCA_PERCENT",
                        "headline_percent": cca_percent,
                        "example_percent": example_percent,
                        "message": "Il PDF riporta una percentuale CCA diversa tra titolo promozione ed esempio di calcolo; mantenuto il valore del titolo senza sovrascrivere l'incoerenza.",
                    })

        # White Label: pdfplumber nel file reale estrae anche forme come
        # "Scontosu" e "0,25%per". Per questo gli spazi sono tutti opzionali.
        white_label_context = re.search(
            r"Nuovi\s+richiedenti\s+mutuo\s+White\s*Label.*?MRI.*?>\s*([\d.]+)\s*Euro",
            normalized,
            re.I,
        )
        white_label_discount = re.search(
            r"Sconto\s*su\s*mutui\s+tasso\s+variabile,?\s*fisso,?\s*fisso\s+rinegoziabile\s*:\s*-?\s*(\d+[,.]\d+)\s*%\s*per\s+tutta\s+la\s+durata\s+dell.?ammortamento",
            normalized,
            re.I,
        )
        if white_label_context and white_label_discount:
            source_start = white_label_context.start()
            source_end = white_label_discount.end()
            rules.append({
                "rule_type": "DISCOUNT", "discount_type": "MRI_WHITE_LABEL",
                "name": "Promozione nuovi richiedenti mutuo White Label con MRI superiore alla soglia",
                "percent": self._pct(white_label_discount.group(1)),
                "mri_min_exclusive": self._money(white_label_context.group(1)),
                "customer_requirement": "NUOVO_RICHIEDENTE_MUTUO_WHITE_LABEL",
                "rate_types": ["VARIABILE", "FISSO", "FISSO_RINEGOZIABILE"],
                "scope": "TUTTI_TIPI_TASSO_E_FINALITA_INCLUSO_HLTV",
                "duration": "TUTTA_DURATA_AMMORTAMENTO", "cumulative": True,
                "cumulative_with": ["CCA_ADDEBITO_RATA_020"],
                "page": page,
                "source_text": normalized[source_start:source_end],
            })

        addebito = re.search(
            r"cumulabile con lo sconto di\s*(\d+[,.]\d+)\s*%\s*per addebito rate mutuo su Conto Corrente Arancio",
            normalized,
            re.I,
        )
        if addebito:
            rules.append({
                "rule_type": "DISCOUNT", "discount_type": "CCA_ADDEBITO_RATA_020",
                "name": "Sconto per addebito rate mutuo su Conto Corrente Arancio",
                "percent": self._pct(addebito.group(1)),
                "requirement": {"code": "ADDEBITO_RATA_CCA", "description": "Addebito rate mutuo su Conto Corrente Arancio"},
                "context": "SPECIFICA_PROMOZIONE_WHITE_LABEL", "cumulative": True,
                "cumulative_with": ["MRI_WHITE_LABEL"],
                "page": page, "source_text": addebito.group(0),
            })

        green = re.search(
            r"Sconto\s+green.*?mutuo\s+acquisto.*?classe\s+energetica\s+[\"“]?B[\"”]?,\s*[\"“]?A[\"”]?\s+o\s+superiore.*?sconto\s+di\s+(\d+)\s*bps",
            normalized,
            re.I,
        )
        if green:
            bps = int(green.group(1))
            rules.append({
                "rule_type": "DISCOUNT", "discount_type": "GREEN", "name": "Sconto Green",
                "basis_points": bps, "percent": bps / 100.0, "finalita": ["ACQUISTO"],
                "classi_energetiche": ["A_SUPERIORE", "A", "B"], "automatic": True,
                "page": page, "source_text": green.group(0),
            })
        return rules, warnings

    def _parse_retrocession_tables(self, tables, text, page):
        rules = []
        year_match = re.search(r"RETROCESSIONI\s+\w*\s*(20\d{2})", self._norm(text))
        year = int(year_match.group(1)) if year_match else None
        for table in tables:
            if not table or len(table) < 2:
                continue
            header = " | ".join(self._clean(c) for c in table[0])
            if "Soglie di erogato" not in header or "Retrocessioni" not in header:
                continue
            fixed_specials = self._special_fixed_retrocessions(table[1])
            for row in table[1:]:
                row = list(row)
                threshold = self._clean(row[0] if len(row) > 0 else "")
                general = self._clean(row[1] if len(row) > 1 else "")
                pct_match = re.search(r"(\d+[,.]\d+)\s*%", general)
                if not threshold or not pct_match:
                    continue
                minimum, maximum = self._parse_threshold(threshold)
                effective = self._parse_effective_rule(general)
                rules.append({
                    "rule_type": "RETROCESSION_TIER", "year": year,
                    "finalita_scope": "TUTTE_NO_SURROGA", "erogato_min": minimum,
                    "erogato_max": maximum, "percent": self._pct(pct_match.group(1)),
                    "effective_basis": effective.get("basis"), "effective_from": effective.get("date"),
                    "page": page, "source_text": " | ".join(self._clean(c) for c in row if c is not None),
                })
            for finalita, percent in fixed_specials.items():
                rules.append({
                    "rule_type": "RETROCESSION_FIXED", "year": year,
                    "finalita": finalita, "percent": percent, "page": page,
                    "source_text": header,
                })
        return rules

    def _special_fixed_retrocessions(self, first_data_row):
        result = {}
        if not first_data_row:
            return result
        for idx, value in enumerate(first_data_row[2:], start=2):
            pct = self._first_pct(value)
            if pct is None:
                continue
            if idx == 2:
                result["SURROGA"] = pct
            elif idx == 3:
                result["LIQUIDITA"] = pct
        return result

    def _parse_fee_rules(self, tables, page):
        rules = []
        for table in tables:
            if not table or len(table) < 2:
                continue
            header = " | ".join(self._clean(c) for c in table[0])
            if "Finalità" not in header or "Spese Istruttoria" not in header:
                continue
            for row in table[1:]:
                finalita = self._clean(row[0] if len(row) > 0 else "")
                fee = self._clean(row[1] if len(row) > 1 else "")
                amounts = [self._money(v) for v in re.findall(r"([\d.]+)\s*€", fee)]
                if not finalita or len(amounts) < 2:
                    continue
                rules.append({
                    "rule_type": "ISTRUTTORIA_RANGE",
                    "finalita_scope": "ACQUISTO_NO_SURROGA" if "Acquisto" in finalita else "ALTRE_FINALITA_NO_SURROGA",
                    "minimum_euro": amounts[0], "maximum_euro": amounts[1],
                    "retrocessione_formula": "ISTRUTTORIA_APPLICATA_MENO_MINIMO",
                    "page": page,
                    "source_text": " | ".join(self._clean(c) for c in row if c is not None),
                })
        return rules

    def _parse_cpi_commissions(self, text, page):
        normalized = re.sub(r"\s+", " ", text)
        rules = []
        for pct, date_from in re.findall(
            r"(\d+[,.]\d+)\s*%\s+del premio unico assicurativo netto\s*->\s*pratiche erogate dal\s*(\d{2}/\d{2}/\d{4})",
            normalized,
            re.I,
        ):
            rules.append({
                "rule_type": "INSURANCE_COMMISSION", "insurance": "CPI",
                "percent_of_net_single_premium": self._pct(pct), "valid_from": date_from,
                "page": page,
            })
        for pct, date_to in re.findall(
            r"(\d+[,.]\d+)\s*%\s+del premio unico assicurativo netto\s*->\s*pratiche erogate fino al\s*(\d{2}/\d{2}/\d{4})",
            normalized,
            re.I,
        ):
            rules.append({
                "rule_type": "INSURANCE_COMMISSION", "insurance": "CPI",
                "percent_of_net_single_premium": self._pct(pct), "valid_to": date_to,
                "page": page,
            })
        if not rules:
            simple = re.search(r"Provvigione polizza CPI:\s*(\d+[,.]\d+)\s*%", normalized, re.I)
            if simple:
                rules.append({
                    "rule_type": "INSURANCE_COMMISSION", "insurance": "CPI",
                    "percent_of_net_single_premium": self._pct(simple.group(1)), "page": page,
                })
        return rules

    def _parse_broker_limit(self, text, page):
        normalized = re.sub(r"\s+", " ", text)
        match = re.search(
            r"Provvigioni di mediazione al cliente massimo\s*(\d+[,.]\d+)\s*%\s*dell.importo di mutuo(?:,\s*massimo\s*([\d.]+)\s*€)?",
            normalized,
            re.I,
        )
        if not match:
            return []
        return [{
            "rule_type": "BROKER_FEE_LIMIT", "max_percent": self._pct(match.group(1)),
            "max_euro": self._money(match.group(2)) if match.group(2) else None,
            "includes_surroga": "surroga" in normalized[match.start():match.start() + 180].lower(),
            "page": page, "source_text": match.group(0),
        }]

    def _parse_threshold(self, text):
        nums = [self._money(v) for v in re.findall(r"\d[\d.]*", text)]
        lower = text.lower()
        if "fino a" in lower and nums:
            return 0.0, nums[0]
        if " da " in f" {lower} " and " a " in f" {lower} " and len(nums) >= 2:
            return nums[0], nums[1]
        if lower.startswith("da") and nums:
            return nums[0], None
        return None, None

    def _parse_effective_rule(self, text):
        match = re.search(r"Da applicare su\s+(caricato|erogato)\s+da\s+(\d{2}/\d{2}/\d{4})", text, re.I)
        return {"basis": match.group(1).upper(), "date": match.group(2)} if match else {"basis": None, "date": None}

    def _first_pct(self, value):
        match = re.search(r"(\d+[,.]\d+)\s*%", self._clean(value))
        return self._pct(match.group(1)) if match else None

    def _pct(self, value):
        return None if value is None else float(str(value).replace("%", "").replace(",", ".").strip())

    def _money(self, value):
        return None if value is None else float(str(value).replace(".", "").replace(",", ".").strip())

    def _clean(self, value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _norm(self, value):
        text = self._clean(value).upper()
        return text.replace("À", "A").replace("È", "E").replace("Ì", "I").replace("Ò", "O").replace("Ù", "U").replace("’", "'")
