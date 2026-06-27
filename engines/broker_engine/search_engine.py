class SearchEngine:

    def search(

        self,

        rules,

        richiesta

    ):

        risultati = []

        for rule in rules:

            # ------------------------
            # FINALITA
            # ------------------------

            trovata = False

            for f in rule["finalita"]:

                if richiesta["finalita"] in f:

                    trovata = True

                    break

            if not trovata:

                continue

            # ------------------------
            # TASSO
            # ------------------------

            if richiesta["tasso"] != rule["tasso"]:

                continue

            # ------------------------
            # DURATA
            # ------------------------

            if richiesta["durata"] < rule["durata_min"]:

                continue

            if richiesta["durata"] > rule["durata_max"]:

                continue

            # ------------------------
            # LTV
            # ------------------------

            if richiesta["ltv"] > rule["ltv_max"]:

                continue

            risultati.append(

                rule

            )

        return risultati