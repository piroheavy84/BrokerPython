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

            # -----------------------------
            # FINALITA
            # -----------------------------

            if "FINALITA" in upper or "SURROGA" in upper:

                finalita = riga

                continue

            # -----------------------------
            # TASSI
            # -----------------------------

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

            # -----------------------------
            # DURATA
            # -----------------------------

            durata = re.search(

                r"(\d+)\s*-\s*(\d+)",

                riga

            )

            spread = re.findall(

                r"\d+,\d+%",

                riga

            )

            if durata and len(spread) == 4:

                durata_min = int(

                    durata.group(1)

                )

                durata_max = int(

                    durata.group(2)

                )

                for i in range(4):

                    rules.append({

                        "id": self.rule_id,

                        "tipo_listino":

                            header_info.get(

                                "tipo_listino",

                                ""

                            ),

                        "canalizzazione_da":

                            header_info.get(

                                "canalizzazione_da",

                                ""

                            ),

                        "canalizzazione_a":

                            header_info.get(

                                "canalizzazione_a",

                                ""

                            ),

                        "stipula_entro":

                            header_info.get(

                                "stipula_entro",

                                ""

                            ),

                        "finalita": finalita,

                        "tasso": tasso,

                        "durata_min": durata_min,

                        "durata_max": durata_max,

                        "ltv_max": colonne_ltv[i],

                        "spread": spread[i]

                    })

                    self.rule_id += 1

        return rules