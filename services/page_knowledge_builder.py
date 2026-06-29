from domain.page_knowledge import PageKnowledge
from services.header_parser import HeaderParser


class PageKnowledgeBuilder:

    def __init__(self):

        self.header_parser = HeaderParser()

    def build(
        self,
        page_number,
        header_blocks,
        product_rules,
        raw_text
    ):

        knowledge = PageKnowledge()

        knowledge.page = page_number

        knowledge.raw_text = raw_text

        if len(header_blocks) > 0:

            knowledge.header = self.header_parser.parse(
                header_blocks[0]
            )

        knowledge.products = product_rules

        knowledge.conditions = self._extract_conditions(
            raw_text
        )

        knowledge.costs = self._extract_costs(
            raw_text
        )

        knowledge.notes = self._extract_notes(
            raw_text
        )

        return knowledge

    def _extract_conditions(
        self,
        text
    ):

        conditions = []

        lower = text.lower()

        if "euribor 3 mesi" in lower:

            conditions.append(
                {
                    "type": "market_index",
                    "name": "EURIBOR",
                    "tenor": "3 mesi",
                    "source_text": "Euribor 3 mesi"
                }
            )

        if "irs" in lower:

            conditions.append(
                {
                    "type": "market_index",
                    "name": "IRS",
                    "source_text": "IRS"
                }
            )

        return conditions

    def _extract_costs(
        self,
        text
    ):

        costs = []

        lower = text.lower()

        if "spese di istruttoria" in lower:

            costs.append(
                {
                    "type": "istruttoria",
                    "description": "Spese di istruttoria presenti nella pagina",
                    "source_text": self._find_line(
                        text,
                        "Spese di istruttoria"
                    )
                }
            )

        if "perizia" in lower:

            costs.append(
                {
                    "type": "perizia",
                    "description": "Costo perizia presente nella pagina",
                    "source_text": self._find_line(
                        text,
                        "perizia"
                    )
                }
            )

        return costs

    def _extract_notes(
        self,
        text
    ):

        notes = []

        for line in text.split("\n"):

            clean = line.strip()

            if clean.startswith("*"):

                notes.append(
                    clean
                )

        return notes

    def _find_line(
        self,
        text,
        keyword
    ):

        for line in text.split("\n"):

            if keyword.lower() in line.lower():

                return line.strip()

        return ""
