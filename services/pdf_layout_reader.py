import pdfplumber


class PdfLayoutReader:

    def __init__(self, pdf_path):

        self.pdf_path = pdf_path

    def leggi_pagina(self, numero_pagina):

        risultato = []

        with pdfplumber.open(self.pdf_path) as pdf:

            pagina = pdf.pages[numero_pagina - 1]

            parole = pagina.extract_words()

            for parola in parole:

                risultato.append({

                    "text": parola["text"],

                    "x0": parola["x0"],

                    "x1": parola["x1"],

                    "top": parola["top"],

                    "bottom": parola["bottom"]

                })

        return risultato