from services.pdf_document_reader import PdfDocumentReader
from services.page_analyzer import PageAnalyzer
from services.rule_builder import RuleBuilder
from services.rule_cleaner import RuleCleaner
from services.json_database import JsonDatabase
from services.rule_validator import RuleValidator
from services.error_database import ErrorDatabase

# =========================================

reader = PdfDocumentReader(

    "input/Chebanca!_06_2026.pdf"

)

analyzer = PageAnalyzer()

builder = RuleBuilder()

cleaner = RuleCleaner()

database = JsonDatabase()

validator = RuleValidator()

error_db = ErrorDatabase()

documento = reader.read_document()

rules_ok = []

rules_error = []

# =========================================

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

            rule = cleaner.clean(rule)

            rule["banca"] = "CheBanca"

            rule["pdf"] = "CheBanca!_06_2026.pdf"

            rule["pagina"] = model.page

            errori = validator.validate(rule)

            if len(errori) == 0:

                rules_ok.append(rule)

            else:

                rules_error.append({

                    "rule": rule,

                    "errori": errori

                })

# =========================================

database.save(

    rules_ok,

    "output/chebanca_index.json"

)

error_db.save(

    rules_error,

    "output/chebanca_errors.json"

)

print()

print("===================================")

print("KIRON PDF ENGINE")

print("===================================")

print()

print(

    "Regole valide:",

    len(rules_ok)

)

print(

    "Regole con errori:",

    len(rules_error)

)

print()

print(

    "Database:",

    "output/chebanca_index.json"

)

print(

    "Errori:",

    "output/chebanca_errors.json"

)

print()

print("===================================")