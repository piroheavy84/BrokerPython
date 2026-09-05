import re

from domain.page_knowledge import PageKnowledge
from services.header_parser import HeaderParser


class PageKnowledgeBuilder:
    """
    Costruisce knowledge generico dalle pagine non tabellari.

    Non contiene regole specifiche per una banca o per un numero pagina.
    L'obiettivo è normalizzare frasi del PDF in un linguaggio comune:

    - convention_ltc: LTC95, LTC90, LTC 80, ecc.
    - spread_modifier: +40 bps, -25 bps, ecc.
    - income_requirement: soglie importo mutuo / reddito minimo.
    - minimum_availability: disponibilità minima saldo prezzo + spese.
    - cost_rule: istruttoria, perizia, minimi/massimi.
    - market_index: Euribor, IRS/Eurirs.

    Il BrokerEngine poi decide se applicare o solo mostrare queste regole.
    """

    def __init__(self):
        self.header_parser = HeaderParser()

    def build(self, page_number, header_blocks, product_rules, raw_text):
        knowledge = PageKnowledge()

        knowledge.page = page_number
        knowledge.raw_text = raw_text

        if len(header_blocks) > 0:
            knowledge.header = self.header_parser.parse(header_blocks[0])

        knowledge.products = product_rules
        knowledge.conditions = self._extract_conditions(raw_text)
        knowledge.costs = self._extract_costs(raw_text)
        knowledge.market_indexes = self._extract_market_indexes(raw_text)
        knowledge.notes = self._extract_notes(raw_text)

        return knowledge

    # ------------------------------------------------------------------
    # CONDITIONS / UNIVERSAL RULES
    # ------------------------------------------------------------------

    def _extract_conditions(self, text):
        rules = []

        rules.extend(self._extract_ltc_conventions(text))
        rules.extend(self._extract_product_ltc_conditions(text))
        rules.extend(self._extract_spread_modifiers(text))
        rules.extend(self._extract_income_requirements(text))
        rules.extend(self._extract_minimum_availability(text))
        rules.extend(self._extract_platform_selection(text))
        rules.extend(self._extract_generic_availability_flags(text))
        rules.extend(self._extract_green_promotion(text))

        return self._dedupe_rules(rules)

    def _extract_ltc_conventions(self, text):
        rules = []
        seen = set()

        for line in self._lines(text):
            for match in re.finditer(r"\bLTC\s*([0-9]{1,3})\b", line, re.IGNORECASE):
                ltc = int(match.group(1))
                code = f"LTC{ltc}"

                if code in seen:
                    continue

                seen.add(code)
                rules.append({
                    "rule_type": "convention_ltc",
                    "code": code,
                    "ltc": ltc,
                    "trigger": {
                        "convention": "LTC",
                        "ltc": ltc,
                    },
                    "source_text": line.strip(),
                })

        return rules

    def _extract_product_ltc_conditions(self, text):
        rules = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            if "LTC" not in normalized:
                continue

            ltc_match = re.search(r"\bLTC\s*([0-9]{1,3})\b", line, re.IGNORECASE)
            if not ltc_match:
                continue

            product = self._extract_product_name_before_ltc(line)
            if not product:
                continue

            ltc = int(ltc_match.group(1))

            rules.append({
                "rule_type": "product_condition",
                "product": product,
                "trigger": {
                    "convention": "LTC",
                    "ltc": ltc,
                },
                "condition": {
                    "ltc": ltc,
                },
                "source_text": line.strip(),
            })

        return rules

    def _extract_spread_modifiers(self, text):
        rules = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            for match in re.finditer(
                r"([+-]?)\s*(\d+(?:[,.]\d+)?)\s*(BPS|BP|BASIS POINTS)",
                normalized,
                re.IGNORECASE,
            ):
                sign = -1 if match.group(1) == "-" else 1
                bps = self._number(match.group(2)) * sign
                spread_delta = bps / 100

                trigger = {}
                if "CANALE INDIRETTO" in normalized or "INDIRETTO" in normalized:
                    trigger["channel"] = "indiretto"
                elif "CANALE DIRETTO" in normalized or "DIRETTO" in normalized:
                    trigger["channel"] = "diretto"

                rules.append({
                    "rule_type": "spread_modifier",
                    "trigger": trigger,
                    "effect": {
                        "basis_points": bps,
                        "spread_delta": spread_delta,
                    },
                    "source_text": line.strip(),
                })

        return rules

    def _extract_income_requirements(self, text):
        rules = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            if "REDDITO" not in normalized:
                continue

            income_values = self._extract_numbers(line)
            if not income_values:
                continue

            threshold = self._extract_mutuo_threshold(line)
            minimum_income = income_values[-1]

            rule = {
                "rule_type": "income_requirement",
                "trigger": {},
                "requirement": {
                    "minimum_monthly_income": minimum_income,
                },
                "source_text": line.strip(),
            }

            if threshold is not None:
                rule["trigger"]["loan_amount"] = threshold

            rules.append(rule)

        return rules

    def _extract_minimum_availability(self, text):
        rules = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            if "DISPONIBIL" not in normalized:
                continue

            requirement = {}

            if "SALDO PREZZO" in normalized:
                requirement["balance_price"] = True

            if "SPESE" in normalized:
                requirement["expenses"] = True

            if "CC" in normalized or "CONTO" in normalized:
                requirement["on_bank_account"] = True

            rules.append({
                "rule_type": "minimum_availability",
                "requirement": requirement,
                "source_text": line.strip(),
            })

        return rules

    def _extract_platform_selection(self, text):
        rules = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            if "SELEZIONARE" not in normalized and "CONVENZIONE" not in normalized:
                continue

            convention = self._extract_quoted_or_ltc(line)
            if not convention:
                continue

            rule = {
                "rule_type": "platform_selection",
                "field": "convenzione",
                "value": convention,
                "source_text": line.strip(),
            }

            livello = self._extract_livello_provvigionale(line)
            if livello:
                rule["additional_field"] = "livello_provvigionale"
                rule["additional_value"] = livello

            rules.append(rule)

        return rules

    def _extract_generic_availability_flags(self, text):
        rules = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            if "NON DISPONIBILE" in normalized:
                rules.append({
                    "rule_type": "availability_exception",
                    "effect": {
                        "available": False,
                    },
                    "source_text": line.strip(),
                })

        return rules


    def _extract_green_promotion(self, text):
        """Estrae la Promozione Green in forma universale.

        Regola applicativa:
        - classe A/B: applicabile subito anche su ACQUISTO semplice;
        - classi inferiori: solo finalità con RISTRUTTURAZIONE, come promozione potenziale
          subordinata ad APE/fine lavori/requisiti successivi.
        """
        normalized = self._normalize(text)
        if "GREEN" not in normalized:
            return []

        discount = 0.30
        pct = re.search(r"RIDOTT[OA]\s+DI\s+(\d+(?:[,.]\d+)?)\s*%", normalized)
        if not pct:
            pct = re.search(r"SCONT\w*\s+DI\s+(\d+(?:[,.]\d+)?)\s*%", normalized)
        if pct:
            discount = self._number(pct.group(1))

        source = self._compact_source(text)
        common_effect = {
            "spread_delta": -float(discount),
            "basis_points": -int(round(float(discount) * 100)),
        }

        return [
            {
                "rule_type": "green_promotion",
                "name": "Promozione Green - applicazione immediata A/B",
                "application": "immediate",
                "trigger": {
                    "energy_class_in": ["A", "A1", "A2", "A3", "A4", "B"],
                    "finalita_in": [
                        "ACQUISTO",
                        "RISTRUTTURAZIONE",
                        "ACQUISTO + RISTRUTTURAZIONE",
                        "SOSTITUZIONE + RISTRUTTURAZIONE",
                    ],
                },
                "effect": common_effect,
                "requirements": {
                    "class_a_or_b_at_stipula": True,
                    "max_loan_amount": None,
                    "max_loan_amount_note": "Nessun limite importo per Acquisto semplice in classe A/B; limite 250.000 solo per finalità con ristrutturazione.",
                },
                "source_text": source,
            },
            {
                "rule_type": "green_promotion",
                "name": "Promozione Green - potenziale a fine lavori",
                "application": "potential_after_works",
                "trigger": {
                    "energy_class_not_in": ["A", "A1", "A2", "A3", "A4", "B"],
                    "finalita_in": [
                        "RISTRUTTURAZIONE",
                        "ACQUISTO + RISTRUTTURAZIONE",
                        "SOSTITUZIONE + RISTRUTTURAZIONE",
                    ],
                },
                "effect": common_effect,
                "requirements": {
                    "max_loan_amount": 250000,
                    "max_loan_amount_applies_to": "finalita_con_ristrutturazione",
                    "ape_required": True,
                    "new_ape_within_months": 30,
                    "accepted_outcomes": [
                        "classe energetica A o B",
                        "miglioramento di almeno 2 classi energetiche",
                        "EP gl,nren inferiore almeno del 30%",
                    ],
                    "no_unpaid_installments": True,
                },
                "source_text": source,
            },
        ]

    # ------------------------------------------------------------------
    # COSTS
    # ------------------------------------------------------------------

    def _extract_costs(self, text):
        costs = []

        costs.extend(self._extract_cost_by_keywords(text, "istruttoria", ["ISTRUTTORIA"]))
        costs.extend(self._extract_cost_by_keywords(text, "perizia", ["PERIZIA"]))
        costs.extend(self._extract_cost_by_keywords(text, "polizza", ["POLIZZA", "POLIZZE"]))

        return costs

    def _extract_cost_by_keywords(self, text, cost_name, keywords):
        costs = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            if not any(keyword in normalized for keyword in keywords):
                continue

            rule = {
                "rule_type": "cost_rule",
                "cost": cost_name,
                "source_text": line.strip(),
            }

            percent = self._extract_first_percent(line)
            if percent is not None:
                rule["calculation"] = {
                    "type": "percent_of_financed_amount",
                    "percent": percent,
                }

            euro_values = self._extract_numbers_with_euro(line)

            if "MIN" in normalized and len(euro_values) >= 1:
                rule["minimum_amount"] = euro_values[0]

            if "MAX" in normalized and len(euro_values) >= 2:
                rule["maximum_amount"] = euro_values[1]
            elif "MASSIMO" in normalized and len(euro_values) >= 2:
                rule["maximum_amount"] = euro_values[1]

            if "ZERO" in normalized or "GRATUIT" in normalized:
                rule["calculation"] = {
                    "type": "fixed_amount",
                    "amount": 0,
                }

            if "calculation" in rule or "minimum_amount" in rule or "maximum_amount" in rule:
                costs.append(rule)

        return costs

    # ------------------------------------------------------------------
    # MARKET INDEXES
    # ------------------------------------------------------------------

    def _extract_market_indexes(self, text):
        indexes = []

        for line in self._lines(text):
            normalized = self._normalize(line)

            euribor_match = re.search(r"\bEURIBOR\s*(\d+)?\s*(MESI|MESE)?", normalized)
            if euribor_match:
                index = {
                    "rule_type": "market_index",
                    "index": "EURIBOR",
                    "source_text": line.strip(),
                }

                if euribor_match.group(1):
                    index["tenor_months"] = int(euribor_match.group(1))

                if "360" in normalized:
                    index["day_count"] = "360"

                indexes.append(index)

            if re.search(r"\bIRS\b|\bEURIRS\b", normalized):
                indexes.append({
                    "rule_type": "market_index",
                    "index": "IRS",
                    "source_text": line.strip(),
                })

        return self._dedupe_rules(indexes)

    # ------------------------------------------------------------------
    # NOTES
    # ------------------------------------------------------------------

    def _extract_notes(self, text):
        notes = []

        for line in self._lines(text):
            clean = line.strip()
            if clean.startswith("*"):
                notes.append(clean)

        return notes

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _extract_product_name_before_ltc(self, line):
        text = str(line).strip()

        # Esempi: "Mutuo PLUS - LTC 95", "Prodotto X LTC90"
        match = re.search(r"(.{2,80}?)\s*[-–]?\s*LTC\s*[0-9]{1,3}", text, re.IGNORECASE)
        if not match:
            return ""

        product = match.group(1).strip(" -–:")

        # Evita titoli troppo generici.
        product = re.sub(r"^(LISTINO|PRATICHE|OFFERTA)\s+", "", product, flags=re.IGNORECASE).strip()

        return product

    def _extract_quoted_or_ltc(self, line):
        quoted = re.search(r"[«\"]([^»\"]+)[»\"]", str(line))
        if quoted:
            return quoted.group(1).strip()

        ltc = re.search(r"\bLTC\s*([0-9]{1,3})\b", str(line), re.IGNORECASE)
        if ltc:
            return f"LTC{int(ltc.group(1))}"

        return ""

    def _extract_livello_provvigionale(self, line):
        quoted = re.findall(r"[«\"]([^»\"]+)[»\"]", str(line))
        if len(quoted) >= 2:
            return quoted[1].strip()

        if "PROVVIGIONE STANDARD" in self._normalize(line):
            return "Provvigione Standard"

        return ""

    def _extract_mutuo_threshold(self, line):
        normalized = self._normalize(line)

        match = re.search(
            r"MUTUO\s*(<=|<|>=|>|=)\s*([0-9\.]+(?:,[0-9]+)?)\s*€?",
            normalized,
        )

        if not match:
            return None

        return {
            "operator": match.group(1),
            "value": self._number(match.group(2)),
        }

    def _extract_first_percent(self, text):
        match = re.search(r"(\d+(?:[,.]\d+)?)\s*%", str(text))
        if not match:
            return None

        return self._number(match.group(1))

    def _extract_numbers_with_euro(self, text):
        values = []
        source = str(text)

        for pattern in [
            r"€\s*([0-9\.]+(?:,[0-9]+)?)",
            r"([0-9\.]+(?:,[0-9]+)?)\s*€",
        ]:
            for match in re.finditer(pattern, source):
                values.append(self._number(match.group(1)))

        return values

    def _extract_numbers(self, text):
        values = []
        source = str(text)

        euro_values = self._extract_numbers_with_euro(source)
        if euro_values:
            return euro_values

        for match in re.finditer(
            r"([0-9]{1,3}(?:\.[0-9]{3})+(?:,[0-9]+)?|[0-9]+(?:,[0-9]+)?)",
            source,
        ):
            values.append(self._number(match.group(1)))

        return values

    def _compact_source(self, text):
        return re.sub(r"\s+", " ", str(text)).strip()

    def _dedupe_rules(self, rules):
        seen = set()
        unique = []

        for rule in rules:
            key = str(rule)
            if key in seen:
                continue
            seen.add(key)
            unique.append(rule)

        return unique

    def _lines(self, text):
        return [
            str(line).strip()
            for line in str(text).split("\n")
            if str(line).strip()
        ]

    def _normalize(self, text):
        return re.sub(
            r"\s+",
            " ",
            str(text)
            .replace("–", "-")
            .replace("—", "-")
            .replace("≤", "<=")
            .replace("≥", ">=")
            .replace("PIÙ", "PIU"),
        ).strip().upper()

    def _number(self, value):
        clean = str(value).strip()

        if "," in clean:
            clean = clean.replace(".", "").replace(",", ".")
        else:
            clean = clean.replace(".", "")

        number = float(clean)

        if number.is_integer():
            return int(number)

        return number
