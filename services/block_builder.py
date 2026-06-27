class BlockBuilder:

    def __init__(self):
        pass

    def build(self, righe):

        blocchi = []

        corrente = []

        for riga in righe:

            if "FINALITA" in riga.upper():

                if corrente:

                    blocchi.append(corrente)

                    corrente = []

            corrente.append(riga)

        if corrente:

            blocchi.append(corrente)

        return blocchi