from services.pdf_document_reader import PdfDocumentReader
from services.page_analyzer import PageAnalyzer
from services.state_machine_v2 import StateMachineV2

# ======================================

reader = PdfDocumentReader(

    "input/Chebanca!_06_2026.pdf"

)

analyzer = PageAnalyzer()

documento = reader.read_document()

# ======================================

for pagina in documento:

    if pagina["pagina"] != 4:

        continue

    model = analyzer.analyze(

        pagina["pagina"],

        pagina["blocchi"]

    )

    print()

    print("======================================")

    print("PAGINA", pagina["pagina"])

    print("======================================")

    print()

    for numero, blocco in enumerate(

        model.products,

        start=1

    ):

        print("----------------------------------")

        print(

            "BLOCCO",

            numero

        )

        print("----------------------------------")

        macchina = StateMachineV2()

        rules = macchina.process(

            blocco

        )

        print()

        print(

            "Regole generate:",

            len(rules)

        )

        print()

        for r in rules:

            print(r)
