class TableBuilder:

    def __init__(self):
        pass

    def build_rows(self, words):

        righe = {}

        for word in words:

            y = round(word["top"])

            if y not in righe:

                righe[y] = []

            righe[y].append(word)

        risultato = []

        for y in sorted(righe.keys()):

            riga = sorted(

                righe[y],

                key=lambda x: x["x0"]

            )

            risultato.append(riga)

        return risultato