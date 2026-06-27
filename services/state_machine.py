import re


class StateMachine:

    def __init__(self):

        self.finalita = ""

        self.tasso = ""

        self.durata = None

    def process(self, riga):

        risultato = None

        testo = riga.upper()

        # -------------------------

        if "FINALITA" in testo:

            self.finalita = riga

            return None

        # -------------------------

        if "FISSO" == testo:

            self.tasso = "FISSO"

            return None

        # -------------------------

        if "VARIABILE" in testo:

            self.tasso = riga

            return None

        # -------------------------

        m = re.search(r"(\d+)\s*[-–]\s*(\d+)", riga)

        if m:

            self.durata = (

                int(m.group(1)),

                int(m.group(2))

            )

        # -------------------------

        spread = re.findall(

            r"\d,\d+%",

            riga

        )

        if self.durata and len(spread) == 4:

            risultato = {

                "finalita": self.finalita,

                "tasso": self.tasso,

                "durata": self.durata,

                "spread": spread

            }

        return risultato