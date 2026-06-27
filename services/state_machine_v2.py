import re


class StateMachineV2:

    def __init__(self):

        self.reset()

    def reset(self):

        self.finalita = []

        self.tasso = ""

        self.rules = []

        self.buffer = []

    def genera_buffer(self):

        colonne = [50, 60, 70, 80]

        if self.tasso == "":

            return

        for durata_min, durata_max, spread in self.buffer:

            for i in range(4):

                self.rules.append({

                    "finalita": self.finalita.copy(),

                    "tasso": self.tasso,

                    "durata_min": durata_min,

                    "durata_max": durata_max,

                    "ltv_max": colonne[i],

                    "spread": spread[i]

                })

        self.buffer = []

    def process(self, blocco):

        self.reset()

        for riga in blocco:

            testo = riga.upper()

            # --------------------
            # FINALITA
            # --------------------

            if "FINALITA" in testo:

                t = testo

                t = t.replace("GRUPPO 1:", "")
                t = t.replace("GRUPPO 2:", "")
                t = t.replace("FINALITA'", "")
                t = t.replace("FINALITA’", "")
                t = t.replace("FINALITA", "")

                self.finalita = []

                for p in t.split("-"):

                    p = p.strip()

                    if p:

                        self.finalita.append(p)

                continue

            # --------------------
            # TASSI
            # --------------------

            nuovo_tasso = None

            if testo == "FISSO":

                nuovo_tasso = "FISSO"

            elif "VARIABILE CON FLOOR" in testo:

                nuovo_tasso = "VARIABILE CON FLOOR"

            elif "VARIABILE CON CAP" in testo:

                nuovo_tasso = "VARIABILE CON CAP"

            elif testo.startswith("VARIABILE"):

                nuovo_tasso = "VARIABILE"

            elif "RATA PROTETTA" in testo:

                nuovo_tasso = "RATA PROTETTA"

            if nuovo_tasso:

                self.tasso = nuovo_tasso

                self.genera_buffer()

            # --------------------
            # DURATA
            # --------------------

            durata = re.search(

                r"(\d+)\s*[-–]\s*(\d+)",

                riga

            )

            spread = re.findall(

                r"\d+,\d+%",

                riga

            )

            if durata and len(spread) == 4:

                self.buffer.append(

                    (

                        int(durata.group(1)),

                        int(durata.group(2)),

                        spread

                    )

                )

                if self.tasso != "":

                    self.genera_buffer()

        self.genera_buffer()

        return self.rules