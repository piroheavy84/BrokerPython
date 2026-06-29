import re

from services.header_parser import HeaderParser


class RuleBuilder:

    def __init__(self):

        self.header_parser = HeaderParser()
        self.rule_id = 1

    def build(self, header, blocco):

        rules = []
        pending_rows = []
        pending_cap = None

        header_info = self.header_parser.parse(header)

        finalita = ""
        tasso = ""
        last_durata_max = None

        colonne_ltv = [50, 60, 70, 80]

        for riga in blocco:

            upper = riga.upper().strip()

            if self._is_finalita_row(upper):

                finalita = riga
                tasso = ""
                last_durata_max = None
                pending_rows = []
                pending_cap = None
                continue

            if pending_cap is not None:

                spread_only = re.findall(
                    r"\d+,\d+%",
                    riga
                )

                if len(spread_only) == 1:

                    rules.append(
                        self._build_rule(
                            header_info=header_info,
                            finalita=finalita,
                            tasso="VARIABILE CON CAP",
                            durata_min=10,
                            durata_max=30,
                            ltv_max=80,
                            spread=spread_only[0],
                            condition=pending_cap
                        )
                    )

                    pending_cap = None
                    continue

            nuovo_tasso = self._detect_tasso(upper)

            if nuovo_tasso:

                tasso = nuovo_tasso
                last_durata_max = None

                if tasso == "VARIABILE CON CAP":

                    cap_rule = self._extract_cap_rule(
                        riga
                    )

                    if cap_rule["spread"] is not None:

                        rules.append(
                            self._build_rule(
                                header_info=header_info,
                                finalita=finalita,
                                tasso="VARIABILE CON CAP",
                                durata_min=10,
                                durata_max=30,
                                ltv_max=80,
                                spread=cap_rule["spread"],
                                condition=cap_rule["condition"]
                            )
                        )

                    else:

                        pending_cap = cap_rule["condition"]

                    continue

                if len(pending_rows) > 0:

                    for pending in pending_rows:

                        rules.extend(
                            self._build_rules_from_row(
                                header_info=header_info,
                                finalita=finalita,
                                tasso=tasso,
                                durata_min=pending["durata_min"],
                                durata_max=pending["durata_max"],
                                spread=pending["spread"],
                                colonne_ltv=colonne_ltv
                            )
                        )

                    pending_rows = []

                continue

            durata = re.search(
                r"(\d+)\s*[-–]\s*(\d+)",
                riga
            )

            spread = re.findall(
                r"\d+,\d+%",
                riga
            )

            if not durata or len(spread) == 0:

                continue

            durata_min = int(
                durata.group(1)
            )

            durata_max = int(
                durata.group(2)
            )

            tasso = self._infer_tasso_from_table_restart(
                current_tasso=tasso,
                last_durata_max=last_durata_max,
                durata_min=durata_min,
                durata_max=durata_max
            )

            last_durata_max = durata_max

            if tasso == "":

                pending_rows.append(
                    {
                        "durata_min": durata_min,
                        "durata_max": durata_max,
                        "spread": spread
                    }
                )

                continue

            rules.extend(
                self._build_rules_from_row(
                    header_info=header_info,
                    finalita=finalita,
                    tasso=tasso,
                    durata_min=durata_min,
                    durata_max=durata_max,
                    spread=spread,
                    colonne_ltv=colonne_ltv
                )
            )

        return rules

    def _infer_tasso_from_table_restart(
        self,
        current_tasso,
        last_durata_max,
        durata_min,
        durata_max
    ):

        if current_tasso == "FISSO":

            if last_durata_max is not None:

                if last_durata_max >= 30 and durata_min <= 10:

                    return "VARIABILE CON FLOOR"

        return current_tasso

    def _is_finalita_row(self, upper):

        if upper.startswith("FINALITA"):
            return True

        if upper.startswith("FINALITÀ"):
            return True

        if upper.startswith("GRUPPO") and "FINALITA" in upper:
            return True

        if upper.startswith("GRUPPO") and "FINALITÀ" in upper:
            return True

        if upper.startswith("SURROGA"):
            return True

        return False

    def _detect_tasso(self, upper):

        if upper == "FISSO":
            return "FISSO"

        if "VARIABILE CON FLOOR" in upper:
            return "VARIABILE CON FLOOR"

        if "VARIABILE CON CAP" in upper:
            return "VARIABILE CON CAP"

        if upper.startswith("VARIABILE"):
            return "VARIABILE"

        if "RATA PROTETTA" in upper:
            return "RATA PROTETTA"

        return None

    def _extract_cap_rule(self, riga):

        percentages = re.findall(
            r"\d+,\d+%",
            riga
        )

        condition = {
            "type": "CAP",
            "source_text": riga
        }

        if len(percentages) >= 1:

            condition["cap"] = percentages[0]

        spread = None

        if len(percentages) >= 2:

            spread = percentages[-1]

        return {
            "condition": condition,
            "spread": spread
        }

    def _build_rules_from_row(
        self,
        header_info,
        finalita,
        tasso,
        durata_min,
        durata_max,
        spread,
        colonne_ltv
    ):

        rules = []

        if len(spread) == 4:

            for i in range(4):

                rules.append(
                    self._build_rule(
                        header_info=header_info,
                        finalita=finalita,
                        tasso=tasso,
                        durata_min=durata_min,
                        durata_max=durata_max,
                        ltv_max=colonne_ltv[i],
                        spread=spread[i]
                    )
                )

        elif len(spread) == 1:

            rules.append(
                self._build_rule(
                    header_info=header_info,
                    finalita=finalita,
                    tasso=tasso,
                    durata_min=durata_min,
                    durata_max=durata_max,
                    ltv_max=80,
                    spread=spread[0]
                )
            )

        return rules

    def _build_rule(
        self,
        header_info,
        finalita,
        tasso,
        durata_min,
        durata_max,
        ltv_max,
        spread,
        condition=None
    ):

        rule = {
            "id": self.rule_id,
            "tipo_listino": header_info.get("tipo_listino", ""),
            "canalizzazione_da": header_info.get("canalizzazione_da", ""),
            "canalizzazione_a": header_info.get("canalizzazione_a", ""),
            "stipula_entro": header_info.get("stipula_entro", ""),
            "finalita": finalita,
            "tasso": tasso,
            "durata_min": durata_min,
            "durata_max": durata_max,
            "ltv_max": ltv_max,
            "spread": spread
        }

        if condition is not None:

            rule["condition"] = condition

        self.rule_id += 1

        return rule
