import json
import os

from services.practice_validator import PracticeValidator
from engines.broker_engine.broker_engine import BrokerEngine


class PracticeService:

    def __init__(
        self,
        repository
    ):
        self.repository = repository
        self.validator = PracticeValidator()
        self.engine = BrokerEngine()

    def search(
        self,
        practice
    ):
        errors = self.validator.validate(
            practice
        )

        if len(errors):
            return {
                "success": False,
                "errors": errors,
                "response": None
            }

        response = self.engine.search(
            self.repository.all(),
            practice,
            knowledge=self._load_all_knowledge()
        )

        return {
            "success": True,
            "errors": [],
            "response": response
        }

    def _load_all_knowledge(self):
        """
        Carica tutte le memorie banca generate dall'import PDF.

        Il BrokerEngine/RuleEngine filtrerà poi solo le regole compatibili
        con prodotto, listino, data e pratica.
        """
        output_dir = "output"

        if not os.path.isdir(output_dir):
            return []

        knowledge_pages = []

        for filename in os.listdir(output_dir):
            if not filename.endswith("_knowledge.json"):
                continue

            path = os.path.join(output_dir, filename)

            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue

            if isinstance(data, list):
                knowledge_pages.extend(data)
            elif isinstance(data, dict):
                pages = data.get("pages")
                if isinstance(pages, list):
                    knowledge_pages.extend(pages)
                else:
                    knowledge_pages.append(data)

        return knowledge_pages
