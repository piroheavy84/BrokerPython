class LayoutCleaner:

    def __init__(self):
        pass

    def clean(self, righe):

        risultato = []

        for riga in righe:

            testo = ""

            for parola in riga:

                testo += parola["text"] + " "

            testo = testo.strip()

            # elimina righe vuote

            if testo == "":
                continue

            # elimina punti isolati

            if testo == ".":
                continue

            # elimina lettere isolate

            if len(testo) == 1 and testo.isalpha():
                continue

            # elimina frammenti verticali

            if len(testo) <= 2 and "%" not in testo and "€" not in testo:

                continue

            risultato.append(testo)

        return risultato