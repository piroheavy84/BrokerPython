import json
from datetime import datetime
from pathlib import Path

from services.pdf_document_reader import PdfDocumentReader
from services.page_analyzer import PageAnalyzer
from services.rule_builder import RuleBuilder
from services.rule_cleaner import RuleCleaner
from services.json_database import JsonDatabase
from services.rule_validator import RuleValidator
from services.error_database import ErrorDatabase


class PdfImportService:

    REGISTRY_PATH = Path("output/banks_registry.json")

    def __init__(self):

        self.analyzer = PageAnalyzer()
        self.builder = RuleBuilder()
        self.cleaner = RuleCleaner()
        self.database = JsonDatabase()
        self.validator = RuleValidator()
        self.error_db = ErrorDatabase()

        Path("output").mkdir(exist_ok=True)

    def _slug(self, value):

        return value.lower().replace(" ", "_")

    def _load_registry(self):

        if not self.REGISTRY_PATH.exists():

            return []

        return json.loads(
            self.REGISTRY_PATH.read_text(
                encoding="utf-8"
            )
        )

    def _save_registry(self, registry):

        self.REGISTRY_PATH.write_text(
            json.dumps(
                registry,
                indent=4,
                ensure_ascii=False
            ),
            encoding="utf-8"
        )

    def list_banks(self):

        return self._load_registry()

    def _update_registry(self, item):

        registry = self._load_registry()

        registry = [
            x for x in registry
            if x["banca"].lower() != item["banca"].lower()
        ]

        registry.append(item)

        registry = sorted(
            registry,
            key=lambda x: x["banca"].lower()
        )

        self._save_registry(registry)

    def import_pdf(
        self,
        banca,
        pdf_path,
        pdf_name,
        tasso_esplicito
    ):

        reader = PdfDocumentReader(pdf_path)
        documento = reader.read_document()

        rules_ok = []
        rules_error = []

        for pagina in documento:

            model = self.analyzer.analyze(
                pagina["pagina"],
                pagina["blocchi"]
            )

            header = model.header[0] if len(model.header) > 0 else []

            for blocco in model.products:

                rules = self.builder.build(
                    header,
                    blocco
                )

                for rule in rules:

                    rule = self.cleaner.clean(rule)

                    rule["banca"] = banca
                    rule["pdf"] = pdf_name
                    rule["pagina"] = model.page
                    rule["tasso_esplicito"] = tasso_esplicito
                    rule["indice_riferimento"] = None

                    if tasso_esplicito:
                        rule["tasso_finito_pdf"] = rule.get(
                            "spread",
                            None
                        )
                    else:
                        rule["tasso_finito_pdf"] = None

                    errori = self.validator.validate(rule)

                    if len(errori) == 0:
                        rules_ok.append(rule)
                    else:
                        rules_error.append(
                            {
                                "rule": rule,
                                "errori": errori
                            }
                        )

        nome_output = self._slug(banca)

        database_path = f"output/{nome_output}_index.json"
        errors_path = f"output/{nome_output}_errors.json"

        self.database.save(
            rules_ok,
            database_path
        )

        self.error_db.save(
            rules_error,
            errors_path
        )

        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        item = {
            "banca": banca,
            "pdf": pdf_name,
            "tasso_esplicito": tasso_esplicito,
            "regole_valide": len(rules_ok),
            "regole_errori": len(rules_error),
            "database": database_path,
            "errori": errors_path,
            "last_updated": now
        }

        self._update_registry(item)

        return {
            "success": True,
            **item
        }