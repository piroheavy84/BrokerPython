from services.finalita_normalizer import FinalitaNormalizer


class FinalitaParser:

    def __init__(self):
        self.normalizer = FinalitaNormalizer()

    def parse(self, testo):
        # Manteniamo la lista testuale leggibile nel JSON, ma la estraiamo
        # con un parser più robusto rispetto alle diciture PDF.
        return self.normalizer.split_pdf_finalita(testo)
