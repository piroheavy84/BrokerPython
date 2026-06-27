from services.pdf_document_reader import PdfDocumentReader
from services.page_analyzer import PageAnalyzer
from services.rule_builder import RuleBuilder
from services.rule_cleaner import RuleCleaner
from services.json_database import JsonDatabase
from services.rule_validator import RuleValidator
from services.error_database import ErrorDatabase
from services.bank_memory_service import BankMemoryService

from models.pdf_import_options import PdfImportOptions


# ==========================================
# CONFIGURAZIONE IMPORT PDF
# ==========================================

print()
print("===================================")
print("KIRON PDF ENGINE - IMPORT PDF")
print("===================================")
print()

banca = input("Nome banca: ").strip()

pdf_file = input("Nome file PDF in input/: ").strip()

tasso_esplicito_input = input(
    "Il PDF contiene un tasso finito esplicito? (s/n): "
).strip().lower()

tasso_esplicito = tasso_esplicito_input == "s"

options = PdfImportOptions(
    banca=banca,
    pdf=pdf_file,
    tasso_esplicito=tasso_esplicito
)


# ==========================================
# AVVIO SERVIZI
# ==========================================

reader = PdfDocumentReader(
    f"input/{options.pdf}"
)

analyzer = PageAnalyzer()

builder = RuleBuilder()

cleaner = RuleCleaner()

database = JsonDatabase()

validator = RuleValidator()

error_db = ErrorDatabase()

bank_memory_service = BankMemoryService()


# ==========================================
# MEMORIA BANCA
# ==========================================

bank_memory = bank_memory_service.load_bank_memory(
    options.banca
)


# ==========================================
# LETTURA PDF
# ==========================================

documento = reader.read_document()

rules_ok = []

rules_error = []


# ==========================================
# ELABORAZIONE PAGINE
# ==========================================

for pagina in documento:

    model = analyzer.analyze(
        pagina["pagina"],
        pagina["blocchi"]
    )

    if len(model.header) > 0:

        header = model.header[0]

    else:

        header = []

    for blocco in model.products:

        rules = builder.build(
            header,
            blocco
        )

        for rule in rules:

            rule = cleaner.clean(
                rule
            )

            rule["banca"] = options.banca

            rule["pdf"] = options.pdf

            rule["pagina"] = model.page

            rule["tasso_esplicito"] = options.tasso_esplicito

            rule["indice_riferimento"] = None

            rule["bank_memory"] = bank_memory

            if options.tasso_esplicito:

                rule["tasso_finito_pdf"] = rule.get(
                    "spread",
                    None
                )

            else:

                rule["tasso_finito_pdf"] = None

            errori = validator.validate(
                rule
            )

            if len(errori) == 0:

                rules_ok.append(
                    rule
                )

            else:

                rules_error.append(
                    {
                        "rule": rule,
                        "errori": errori
                    }
                )


# ==========================================
# SALVATAGGIO
# ==========================================

nome_output = options.banca.lower().replace(
    " ",
    "_"
)

database_path = f"output/{nome_output}_index.json"

errors_path = f"output/{nome_output}_errors.json"

database.save(
    rules_ok,
    database_path
)

error_db.save(
    rules_error,
    errors_path
)

bank_memory_service.save_bank_memory(
    options.banca,
    bank_memory
)


# ==========================================
# REPORT
# ==========================================

print()

print("===================================")

print("KIRON PDF ENGINE")

print("===================================")

print()

print("Banca:", options.banca)

print("PDF:", options.pdf)

print("Tasso esplicito:", options.tasso_esplicito)

print()

print("Memoria banca caricata:", options.banca)

print()

print("Regole valide:", len(rules_ok))

print("Regole con errori:", len(rules_error))

print()

print("Database:", database_path)

print("Errori:", errors_path)

print()

print("===================================")