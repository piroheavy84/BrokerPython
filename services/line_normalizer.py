import re


class LineNormalizer:

    def __init__(self):
        pass

    def normalize(self, riga):

        testo = riga.strip()

        # uniforma i trattini

        testo = testo.replace("–", "-")

        # elimina doppi spazi

        testo = re.sub(r"\s+", " ", testo)

        return testo