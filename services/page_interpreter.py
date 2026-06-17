import re


class PageInterpreter:

    def __init__(self):

        self.finalita = ""

        self.tipo_tasso = ""

        self.durata = None

    def interpreta(self, righe):

        prodotti = []

        print()
        print("======================================")
        print("DEBUG PAGE INTERPRETER")
        print("======================================")
        print()

        for riga in righe:

            testo = riga["testo"]

            tipo = riga["tipo"]

            print("----------------------------------")
            print("TESTO :", testo)
            print("TIPO  :", tipo)

            # -------------------------
            # FINALITA
            # -------------------------

            if tipo == "FINALITA":

                self.finalita = testo

                print("FINALITA ATTIVA:", self.finalita)

                continue

            # -------------------------
            # TASSO
            # -------------------------

            if tipo == "TASSO":

                self.tipo_tasso = testo

                print("TASSO ATTIVO:", self.tipo_tasso)

                continue

            # -------------------------
            # DURATA
            # -------------------------

            if tipo == "DURATA":

                m = re.search(r"(\d+)-(\d+)", testo)

                if m:

                    self.durata = (

                        int(m.group(1)),

                        int(m.group(2))

                    )

                    print("DURATA:", self.durata)

                else:

                    print("DURATA NON RICONOSCIUTA")

                continue

            # -------------------------
            # SPREAD
            # -------------------------

            if tipo == "SPREAD":

                spread = re.findall(

                    r"\d,\d+%",

                    testo

                )

                print()

                print("SPREAD TROVATI:")

                print(spread)

                print()

                print("NUMERO:", len(spread))

                print()

                print("FINALITA:", self.finalita)

                print("TASSO:", self.tipo_tasso)

                print("DURATA:", self.durata)

        print()

        print("======================================")
        print("FINE DEBUG")
        print("======================================")

        return prodotti