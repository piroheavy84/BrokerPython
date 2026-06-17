class FinalitaParser:

    def parse(self, testo):

        testo = testo.upper()

        # elimina intestazioni

        testo = testo.replace(
            "GRUPPO 1:", ""
        )

        testo = testo.replace(
            "GRUPPO 2:", ""
        )

        testo = testo.replace(
            "FINALITA’", ""
        )

        testo = testo.replace(
            "FINALITA'",
            ""
        )

        testo = testo.replace(
            "FINALITA",
            ""
        )

        parti = testo.split("-")

        risultato = []

        for p in parti:

            p = p.strip()

            if p != "":

                risultato.append(p)

        return risultato