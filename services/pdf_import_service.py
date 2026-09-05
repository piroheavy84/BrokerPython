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
from services.page_knowledge_builder import PageKnowledgeBuilder
from services.structured_mortgage_table_parser import StructuredMortgageTableParser
from services.structured_commercial_rules_parser import StructuredCommercialRulesParser
from services.commercial_ai_fallback import CommercialAiFallback


class PdfImportService:

    REGISTRY_PATH = Path("output/banks_registry.json")

    def __init__(self):
        self.analyzer = PageAnalyzer()
        self.builder = RuleBuilder()
        self.cleaner = RuleCleaner()
        self.database = JsonDatabase()
        self.validator = RuleValidator()
        self.error_db = ErrorDatabase()
        self.knowledge_builder = PageKnowledgeBuilder()
        self.structured_table_parser = StructuredMortgageTableParser()
        self.commercial_rules_parser = StructuredCommercialRulesParser()
        self.commercial_ai_fallback = CommercialAiFallback()
        Path("output").mkdir(exist_ok=True)

    def _slug(self, value):
        return value.lower().replace(" ", "_")

    def _load_registry(self):
        if not self.REGISTRY_PATH.exists():
            return []
        return json.loads(self.REGISTRY_PATH.read_text(encoding="utf-8"))

    def _save_registry(self, registry):
        self.REGISTRY_PATH.write_text(
            json.dumps(registry, indent=4, ensure_ascii=False),
            encoding="utf-8"
        )

    def list_banks(self):
        return self._load_registry()

    def _update_registry(self, item):
        registry = self._load_registry()
        registry = [x for x in registry if x["banca"].lower() != item["banca"].lower()]
        registry.append(item)
        registry = sorted(registry, key=lambda x: x["banca"].lower())
        self._save_registry(registry)

    def _blocks_to_text(self, blocchi):
        rows = []
        for blocco in blocchi:
            if isinstance(blocco, list):
                rows.append("\n".join(str(row) for row in blocco))
            else:
                rows.append(str(blocco))
        return "\n".join(rows)

    def _decorate_and_validate_rule(self, rule, banca, pdf_name, tasso_esplicito, default_page=None):
        rule = self.cleaner.clean(rule)
        rule["banca"] = banca
        rule["pdf"] = pdf_name
        rule["pagina"] = rule.get("pagina") or default_page
        rule["tasso_esplicito"] = tasso_esplicito
        rule["indice_riferimento"] = None
        if tasso_esplicito:
            rule["tasso_finito_pdf"] = rule.get("spread", None)
        else:
            rule["tasso_finito_pdf"] = None
        return rule, self.validator.validate(rule)

    def _build_page_knowledge(self, documento, rules_ok):
        rules_by_page = {}
        for rule in rules_ok:
            rules_by_page.setdefault(rule.get("pagina"), []).append(rule)

        page_knowledge = []
        for pagina in documento:
            model = self.analyzer.analyze(pagina["pagina"], pagina["blocchi"])
            raw_text = self._blocks_to_text(pagina.get("blocchi", []))
            knowledge = self.knowledge_builder.build(
                page_number=model.page,
                header_blocks=model.header,
                product_rules=rules_by_page.get(model.page, []),
                raw_text=raw_text
            )
            page_knowledge.append(knowledge.to_dict())
        return page_knowledge

    def _attach_commercial_rules(self, page_knowledge, commercial_by_page):
        """Aggiunge regole commerciali senza mescolarle ai prodotti."""
        for page in page_knowledge:
            page_number = page.get("page")
            commercial = commercial_by_page.get(page_number)
            if commercial:
                page["commercial_rules"] = commercial.get("rules", [])
                page["commercial_warnings"] = commercial.get("warnings", [])
            else:
                page["commercial_rules"] = []
                page["commercial_warnings"] = []
        return page_knowledge

    def import_pdf(self, banca, pdf_path, pdf_name, tasso_esplicito):
        reader = PdfDocumentReader(pdf_path)
        documento = reader.read_document()
        rules_ok = []
        rules_error = []

        # Parser legacy per documenti senza tabelle prodotto strutturate.
        for pagina in documento:
            model = self.analyzer.analyze(pagina["pagina"], pagina["blocchi"])
            header = model.header[0] if len(model.header) > 0 else []
            for blocco in model.products:
                rules = self.builder.build(header, blocco)
                for rule in rules:
                    rule, errori = self._decorate_and_validate_rule(
                        rule=rule,
                        banca=banca,
                        pdf_name=pdf_name,
                        tasso_esplicito=tasso_esplicito,
                        default_page=model.page,
                    )
                    if len(errori) == 0:
                        rules_ok.append(rule)
                    else:
                        rules_error.append({"rule": rule, "errori": errori})

        # Tabelle mutuo strutturate: fonte autorevole quando presenti.
        structured_rules = self.structured_table_parser.parse(pdf_path)
        if structured_rules:
            structured_ok = []
            structured_errors = []
            for rule in structured_rules:
                rule, errori = self._decorate_and_validate_rule(
                    rule=rule,
                    banca=banca,
                    pdf_name=pdf_name,
                    tasso_esplicito=tasso_esplicito,
                    default_page=rule.get("pagina"),
                )
                if len(errori) == 0:
                    structured_ok.append(rule)
                else:
                    structured_errors.append({"rule": rule, "errori": errori})
            if structured_ok:
                rules_ok = structured_ok
                rules_error = structured_errors

        page_knowledge = self._build_page_knowledge(documento, rules_ok)

        # Secondo canale strutturato: promozioni, retrocessioni, CPI e limiti
        # commerciali. Queste informazioni NON entrano nell'index prodotti.
        commercial_by_page = self.commercial_rules_parser.parse(pdf_path)

        # Se il parser deterministico lascia una percentuale promozionale non
        # coperta e la chiave AI e' configurata, l'AI prova a completare SOLO
        # quella parte. Le regole AI vengono validate, marcate e deduplicate.
        commercial_by_page = self.commercial_ai_fallback.enrich(
            pdf_path,
            commercial_by_page,
        )
        page_knowledge = self._attach_commercial_rules(page_knowledge, commercial_by_page)

        nome_output = self._slug(banca)
        database_path = f"output/{nome_output}_index.json"
        errors_path = f"output/{nome_output}_errors.json"
        knowledge_path = f"output/{nome_output}_knowledge.json"

        self.database.save(rules_ok, database_path)
        self.error_db.save(rules_error, errors_path)
        self.database.save(page_knowledge, knowledge_path)

        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        commercial_count = sum(len(v.get("rules", [])) for v in commercial_by_page.values())
        commercial_warning_count = sum(len(v.get("warnings", [])) for v in commercial_by_page.values())
        ai_commercial_count = sum(
            1
            for payload in commercial_by_page.values()
            for rule in payload.get("rules", [])
            if rule.get("origin") == "AI_FALLBACK"
        )

        item = {
            "banca": banca,
            "pdf": pdf_name,
            "tasso_esplicito": tasso_esplicito,
            "regole_valide": len(rules_ok),
            "regole_errori": len(rules_error),
            "regole_commerciali": commercial_count,
            "regole_commerciali_ai": ai_commercial_count,
            "warning_commerciali": commercial_warning_count,
            "database": database_path,
            "errori": errors_path,
            "knowledge": knowledge_path,
            "last_updated": now
        }
        self._update_registry(item)
        return {"success": True, **item}
