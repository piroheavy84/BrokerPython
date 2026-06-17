from models.page_model import PageModel
from services.block_classifier import BlockClassifier


class PageAnalyzer:

    def __init__(self):

        self.classifier = BlockClassifier()

    def analyze(self, numero_pagina, blocchi):

        pagina = PageModel()

        pagina.page = numero_pagina

        for blocco in blocchi:

            tipo = self.classifier.classify(blocco)

            if tipo == "HEADER":

                pagina.header.append(blocco)

            elif tipo == "PRODOTTO":

                pagina.products.append(blocco)

            elif tipo == "INFO":

                pagina.info.append(blocco)

            else:

                pagina.unknown.append(blocco)

        return pagina