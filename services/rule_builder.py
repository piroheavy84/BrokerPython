import re

from services.header_parser import HeaderParser


class RuleBuilder:

    def __init__(self):

        self.header_parser = HeaderParser()

        self.rule_id = 1

    def build(self, header, blocco):

        rules = []

        header_info = self.header_parser.parse(header)

        finalita = ""

        tasso = ""

        colonne_ltv = [50, 60, 70, 80]

        for riga in blocco:

            upper = riga.upper()

            if "FINALITA" in upper or "SURROGA" in upper:

                finalita = riga

                continue

            if upper == "FISSO":

                tasso = "FISSO"

                continue

            if "VARIABILE CON FLOOR" in upper:

                tasso = "VARIABILE CON FLOOR"

            elif "VARIABILE CON CAP" in upper:

                tasso = "VARIABILE CON CAP"

            elif upper.startswith("VARIABILE"):

                tasso = "VARIABILE"

            elif "RATA PROTETTA" in upper:

                tasso = "RATA PROTETTA"

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
        spread
    ):

        rule = {
            "id": self.rule_id,
            "tipo_listino": header_info.get(
                "tipo_listino",
                ""
            ),
            "canalizzazione_da": header_info.get(
                "canalizzazione_da",
                ""
            ),
            "canalizzazione_a": header_info.get(
                "canalizzazione_a",
                ""
            ),
            "stipula_entro": header_info.get(
                "stipula_entro",
                ""
            ),
            "finalita": finalita,
            "tasso": tasso,
            "durata_min": durata_min,
            "durata_max": durata_max,
            "ltv_max": ltv_max,
            "spread": spread
        }

        self.rule_id += 1

        return rule
