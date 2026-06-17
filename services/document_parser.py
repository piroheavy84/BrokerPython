from services.pdf_document_reader import PdfDocumentReader
from services.page_analyzer import PageAnalyzer
from services.state_machine_v2 import StateMachineV2


class DocumentParser:

    def __init__(self, pdf):

        self.reader = PdfDocumentReader(pdf)

        self.analyzer = PageAnalyzer()

    def parse(self):

        documento = self.reader.read_document()

        tutte_le_regole = []

        for pagina in documento:

            model = self.analyzer.analyze(

                pagina["pagina"],

                pagina["blocchi"]

            )

            macchina = StateMachineV2()

            for blocco in model.products:

                rules = macchina.process(

                    blocco

                )

                tutte_le_regole.extend(

                    rules

                )

        return tutte_le_regole