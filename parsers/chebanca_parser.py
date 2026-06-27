import pdfplumber
import re


class CheBancaParser:

    def __init__(self, pdf_path):

        self.pdf_path = pdf_path

        self.righe = []

    # ===================================
    # LETTURA COMPLETA PDF
    # ===================================

    def leggi_pdf(self):

        id_riga = 1

        with pdfplumber.open(self.pdf_path) as pdf:

            for numero_pagina, pagina in enumerate(pdf.pages, start=1):

                testo = pagina.extract_text()

                if testo:

                    for numero_riga, riga in enumerate(
                        testo.split("\n"),
                        start=1
                    ):

                        self.righe.append({

                            "id": id_riga,

                            "pagina": numero_pagina,

                            "riga": numero_riga,

                            "testo": riga.strip()

                        })

                        id_riga += 1

        return self.righe

    # ===================================
    # LETTURA SINGOLA PAGINA
    # ===================================

    def leggi_pagina(self, numero_pagina):

        with pdfplumber.open(self.pdf_path) as pdf:

            if numero_pagina > len(pdf.pages):

                return []

            pagina = pdf.pages[numero_pagina - 1]

            testo = pagina.extract_text()

            if testo:

                return testo.split("\n")

            return []

    # ===================================
    # CLASSIFICAZIONE RIGA
    # ===================================

    def classifica_riga(self, testo):

        r = testo.upper()

        if "FINALITA" in r:

            return "FINALITA"

        if r == "FISSO":

            return "TASSO"

        if r == "VARIABILE":

            return "TASSO"

        if "RATA PROTETTA" in r:

            return "TASSO"

        if re.search(r"\d+\-\d+\s*ANNI", r):

            return "DURATA"

        if "LTV" in r:

            return "LTV"

        if re.search(r"\d,\d+%", r):

            return "SPREAD"

        return "ALTRO"