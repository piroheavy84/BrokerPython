import re

from services.pdf_document_reader import PdfDocumentReader
from services.bank_memory_ai_service import BankMemoryAIService
from config.bank_memory_service import BankMemoryService


class PdfPreviewService:

    def __init__(self):

        self.bank_memory_service = BankMemoryService()

        self.ai_service = BankMemoryAIService()

    def _clean_text(
        self,
        text
    ):

        return re.sub(
            r"\s+",
            " ",
            text
        ).strip()

    def _extract_number_after_keywords(
        self,
        text,
        keywords
    ):

        for keyword in keywords:

            pattern = rf"{keyword}.{{0,40}}?(\d{{1,3}})"

            match = re.search(
                pattern,
                text,
                re.IGNORECASE
            )

            if match:

                return int(
                    match.group(1))

        return None

    def _extract_important_phrases(
        self,
        text
    ):

        phrases = []

        keywords = [
            "età",
            "eta",
            "scadenza",
            "ltv",
            "loan to value",
            "prima casa",
            "seconda casa",
            "surroga",
            "liquidità",
            "liquidita",
            "consolidamento",
            "classe energetica",
            "green",
            "abitazione principale",
            "autonomi",
            "redditi esteri",
            "garante",
            "polizza",
            "deroga"
        ]

        sentences = re.split(
            r"[.;\n]",
            text
        )

        for sentence in sentences:

            clean = self._clean_text(
                sentence
            )

            lower = clean.lower()

            if len(clean) < 12:

                continue

            for keyword in keywords:

                if keyword in lower:

                    phrases.append(
                        clean
                    )

                    break

        return phrases

    def classify_phrase(
        self,
        phrase
    ):

        lower = phrase.lower()

        if "autonom" in lower:
            return "autonomi"

        if "redditi esteri" in lower or "estero" in lower:
            return "redditi_esteri"

        if "garante" in lower:
            return "garanti"

        if "polizza" in lower:
            return "polizze"

        if "deroga" in lower:
            return "deroghe"

        if (
            "classe energetica" in lower
            or "green" in lower
            or "classe a" in lower
            or "classe b" in lower
        ):
            return "classe_energetica"

        return None
    def analyze_text(
        self,
        text
    ):

        clean = self._clean_text(
            text
        )

        lower = clean.lower()

        eta_massima = self._extract_number_after_keywords(
            lower,
            [
                "età massima",
                "eta massima",
                "a scadenza",
                "scadenza"
            ]
        )

        ltv_massimo = self._extract_number_after_keywords(
            lower,
            [
                "ltv",
                "loan to value",
                "finanziabile fino",
                "fino al"
            ]
        )

        phrases = self._extract_important_phrases(
            text
        )

        suggested_categories = {
            "autonomi": [],
            "redditi_esteri": [],
            "garanti": [],
            "polizze": [],
            "deroghe": [],
            "classe_energetica": []
        }

        for phrase in phrases:

            category = self.classify_phrase(
                phrase
            )

            if category is not None:

                suggested_categories[
                    category
                ].append(
                    phrase
                )

        return {
            "eta_massima": eta_massima,
            "ltv_massimo": ltv_massimo,
            "prima_casa":
                "prima casa" in lower
                or "abitazione principale" in lower,

            "seconda_casa":
                "seconda casa" in lower,

            "surroga":
                "surroga" in lower,

            "liquidita":
                "liquidità" in lower
                or "liquidita" in lower,

            "consolidamento":
                "consolidamento" in lower,

            "green":
                "green" in lower
                or "classe energetica" in lower,

            "phrases": phrases,

            "suggested_categories":
                suggested_categories
        }

    def preview_pdf(
        self,
        banca,
        pdf_path
    ):

        reader = PdfDocumentReader(
            pdf_path
        )

        documento = reader.read_document()

        memory = self.bank_memory_service.load_bank_memory(
            banca
        )

        pages = []

        detected = {
            "eta_massima": None,
            "ltv_massimo": None,
            "prima_casa": False,
            "seconda_casa": False,
            "surroga": False,
            "liquidita": False,
            "consolidamento": False,
            "green": False,
            "phrases": []
        }

        suggested_categories = {
            "autonomi": [],
            "redditi_esteri": [],
            "garanti": [],
            "polizze": [],
            "deroghe": [],
            "classe_energetica": []
        }

        confirmed_phrases = memory.get(
            "frasi_confermate",
            []
        )

        for pagina in documento:

            raw_text = ""

            for blocco in pagina.get(
                "blocchi",
                []
            ):

                raw_text += " " + str(
                    blocco
                )

            analysis = self.analyze_text(
                raw_text
            )

            for key in [
                "eta_massima",
                "ltv_massimo"
            ]:

                if (
                    detected[key] is None
                    and analysis[key] is not None
                ):

                    detected[key] = analysis[key]

            for key in [
                "prima_casa",
                "seconda_casa",
                "surroga",
                "liquidita",
                "consolidamento",
                "green"
            ]:

                if analysis[key]:

                    detected[key] = True

            for phrase in analysis["phrases"]:

                if phrase not in detected["phrases"]:

                    detected["phrases"].append(
                        phrase
                    )

            for category, rows in analysis[
                "suggested_categories"
            ].items():

                for row in rows:

                    if row not in suggested_categories[
                        category
                    ]:

                        suggested_categories[
                            category
                        ].append(
                            row
                        )

            unknown_phrases = [

                p

                for p in analysis["phrases"]

                if p not in confirmed_phrases
            ]

            pages.append(
                {
                    "pagina":
                        pagina.get(
                            "pagina"
                        ),

                    "text_preview":
                        self._clean_text(
                            raw_text
                        )[:1200],

                    "analysis":
                        analysis,

                    "unknown_phrases":
                        unknown_phrases
                }
            )

        changes = self.ai_service.compare_memory(
            memory,
            detected
        )

        new_phrases = self.ai_service.find_new_phrases(
            memory,
            detected
        )

        return {
            "success": True,

            "banca": banca,

            "memory": memory,

            "detected": detected,

            "changes": changes,

            "new_phrases": new_phrases,

            "suggested_categories":
                suggested_categories,

            "pages": pages
        }