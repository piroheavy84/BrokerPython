import re

import pdfplumber


class StructuredCommercialRulesParser:
    """Estrae regole commerciali non-prodotto da PDF strutturati.

    Non usa il nome banca. Riconosce per contenuto:
    - scontistiche/promozioni;
    - retrocessioni per scaglioni;
    - spese istruttoria e retrocessione sulle spese;
    - provvigioni CPI;
    - limiti di mediazione al cliente.

    Le regole restano separate dai prodotti mutuo e vengono salvate nel
    knowledge.json sotto `commercial_rules`.
    """

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
                    by_page[page_number] = {
                        "rules": rules,
                        "warnings": warnings,
                    }
        return by_page

    def _looks_like_discount_page(self, text):
        upper = self._norm(text)
        return "SCONT" in upper and ("PROMOZ" in upper or "CONTO CORRENTE" in upper or "GREEN" in upper)

    def _looks_like_retrocession_page(self, text):
        upper = self._norm(text)
        return "RETROCESSION" in upper and "SOGLIE DI EROGATO" in upper

    def _parse_discounts(self, text, page):
        normalized = re.sub(r"\s+", " ", text)
        rules = []
        warnings = []

        # Sconto conto corrente / accredito.
        cca = re.search(
            r"Sconto\s*CCA.*?su tutti i prodotti\s*-?\s*(\d+[,.]\d+)\s*%",
            normalized,
            re.IGNORECASE,
        )
        if cca:
            pct = self._pct(cca.group(1))
            rules.append({
                "rule_type": "DISCOUNT",
                "discount_type": "CONTO_CORRENTE",
                "percent": pct,
                "scope": "TUTTI_I_PRODOTTI",
                "duration": "TUTTA_DURATA_AMMORTAMENTO",
                "requirements": [
                    "ACCREDITO_STIPENDIO_PENSIONE_O_ENTRATA_1000_ENTRO_6_MESI",
                    "ADDEBITO_RATA_SU_CONTO",
                    "MANTENIMENTO_REQUISITI_PER_TUTTA_DURATA",
                ],
                "page": page,
                "source_text": cca.group(0),
            })

            # Nel documento può esserci una percentuale diversa nella formula/esempio.
            example_values = [self._pct(v) for v in re.findall(r"sconto[^.]{0,100}?(\d+[,.]\d+)\s*%", normalized, re.IGNORECASE)]
            differing = sorted({v for v in example_values if v is not None and abs(v - pct) > 1e-9})
            if differing:
                warnings.append({
                    "type": "DISCOUNT_PERCENT_CONFLICT",
                    "page": page,
                    "headline_percent": pct,
                    "other_percentages": differing,
                    "message": "Il PDF riporta percentuali diverse per lo stesso sconto; nessun valore viene corretto automaticamente.",
                })

        # Promozione soglia di sussistenza / MRI.
        mri = re.search(
            r"MRI\s*\(.*?\)\s*>\s*([\d.]+)\s*Euro.*?Sconto.*?-?\s*(\d+[,.]\d+)\s*%",
            normalized,
            re.IGNORECASE,
        )
        if mri:
            rules.append({
                "rule_type": "DISCOUNT",
                "discount_type": "MRI_WHITE_LABEL",
                "percent": self._pct(mri.group(2)),
                "mri_min_exclusive": self._money(mri.group(1)),
                "scope": "TUTTI_TIPI_TASSO_E_FINALITA_INCLUSO_HLTV",
                "duration": "TUTTA_DURATA_AMMORTAMENTO",
                "cumulative": True,
                "page": page,
                "source_text": mri.group(0),
            })

        green = re.search(
            r"Sconto\s+green.*?mutuo\s+acquisto.*?classe\s+energetica\s+[\"“]?B[\"”]?,\s*[\"“]?A[\"”]?\s+o\s+superiore.*?sconto\s+di\s+(\d+)\s*bps",
            normalized,
            re.IGNORECASE,
        )
        if green:
            bps = int(green.group(1))
            rules.append({
                "rule_type": "DISCOUNT",
                "discount_type": "GREEN",
                "basis_points": bps,
                "percent": bps / 100.0,
                "finalita": ["ACQUISTO"],
                "classi_energetiche": ["A_SUPERIORE", "A", "B"],
                "automatic": True,
                "page": page,
                "source_text": green.group(0),
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
                    "rule_type": "RETROCESSION_TIER",
                    "year": year,
                    "finalita_scope": "TUTTE_NO_SURROGA",
                    "erogato_min": minimum,
                    "erogato_max": maximum,
                    "percent": self._pct(pct_match.group(1)),
                    "effective_basis": effective.get("basis"),
                    "effective_from": effective.get("date"),
                    "page": page,
                    "source_text": " | ".join(self._clean(c) for c in row if c is not None),
                })

            for finalita, percent in fixed_specials.items():
                rules.append({
                    "rule_type": "RETROCESSION_FIXED",
                    "year": year,
                    "finalita": finalita,
                    "percent": percent,
                    "page": page,
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
                    "minimum_euro": amounts[0],
                    "maximum_euro": amounts[1],
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
            re.IGNORECASE,
        ):
            rules.append({
                "rule_type": "INSURANCE_COMMISSION",
                "insurance": "CPI",
                "percent_of_net_single_premium": self._pct(pct),
                "valid_from": date_from,
                "page": page,
            })
        for pct, date_to in re.findall(
            r"(\d+[,.]\d+)\s*%\s+del premio unico assicurativo netto\s*->\s*pratiche erogate fino al\s*(\d{2}/\d{2}/\d{4})",
            normalized,
            re.IGNORECASE,
        ):
            rules.append({
                "rule_type": "INSURANCE_COMMISSION",
                "insurance": "CPI",
                "percent_of_net_single_premium": self._pct(pct),
                "valid_to": date_to,
                "page": page,
            })
        if not rules:
            simple = re.search(r"Provvigione polizza CPI:\s*(\d+[,.]\d+)\s*%", normalized, re.IGNORECASE)
            if simple:
                rules.append({
                    "rule_type": "INSURANCE_COMMISSION",
                    "insurance": "CPI",
                    "percent_of_net_single_premium": self._pct(simple.group(1)),
                    "page": page,
                })
        return rules

    def _parse_broker_limit(self, text, page):
        normalized = re.sub(r"\s+", " ", text)
        match = re.search(
            r"Provvigioni di mediazione al cliente massimo\s*(\d+[,.]\d+)\s*%\s*dell.importo di mutuo(?:,\s*massimo\s*([\d.]+)\s*€)?",
            normalized,
            re.IGNORECASE,
        )
        if not match:
            return []
        return [{
            "rule_type": "BROKER_FEE_LIMIT",
            "max_percent": self._pct(match.group(1)),
            "max_euro": self._money(match.group(2)) if match.group(2) else None,
            "includes_surroga": "surroga" in normalized[match.start():match.start() + 180].lower(),
            "page": page,
            "source_text": match.group(0),
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
        match = re.search(r"Da applicare su\s+(caricato|erogato)\s+da\s+(\d{2}/\d{2}/\d{4})", text, re.IGNORECASE)
        if not match:
            return {"basis": None, "date": None}
        return {"basis": match.group(1).upper(), "date": match.group(2)}

    def _first_pct(self, value):
        match = re.search(r"(\d+[,.]\d+)\s*%", self._clean(value))
        return self._pct(match.group(1)) if match else None

    def _pct(self, value):
        if value is None:
            return None
        return float(str(value).replace("%", "").replace(",", ".").strip())

    def _money(self, value):
        if value is None:
            return None
        return float(str(value).replace(".", "").replace(",", ".").strip())

    def _clean(self, value):
        return re.sub(r"\s+", " ", str(value or "")).strip()

    def _norm(self, value):
        text = self._clean(value).upper()
        return (text.replace("À", "A").replace("È", "E").replace("Ì", "I")
                .replace("Ò", "O").replace("Ù", "U").replace("’", "'"))
