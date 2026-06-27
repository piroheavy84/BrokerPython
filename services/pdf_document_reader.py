from services.pdf_layout_reader import PdfLayoutReader
from services.table_builder import TableBuilder
from services.layout_cleaner import LayoutCleaner
from services.line_normalizer import LineNormalizer
from services.block_builder import BlockBuilder


class PdfDocumentReader:

    def __init__(self, pdf_path):

        self.pdf_path = pdf_path

        self.reader = PdfLayoutReader(pdf_path)

        self.builder = TableBuilder()

        self.cleaner = LayoutCleaner()

        self.normalizer = LineNormalizer()

        self.block_builder = BlockBuilder()

    def read_document(self):

        documento = []

        pagina = 1

        while True:

            try:

                parole = self.reader.leggi_pagina(pagina)

            except:

                break

            righe = self.builder.build_rows(parole)

            righe = self.cleaner.clean(righe)

            righe = [

                self.normalizer.normalize(r)

                for r in righe

            ]

            blocchi = self.block_builder.build(righe)

            documento.append({

                "pagina": pagina,

                "blocchi": blocchi

            })

            pagina += 1

        return documento