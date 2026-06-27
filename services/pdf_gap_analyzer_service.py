import re


class PdfGapAnalyzerService:

    def _clean_text(self, text):

        return re.sub(
            r"\s+",
            " ",
            str(text)
        ).strip()

    def _split_sentences(self, text):

        rows = re.split(
            r"[.;\n]",
            text
        )

        return [
            self._clean_text(row)
            for row in rows
            if len(self._clean_text(row)) >= 12
        ]

    def _match_category(self, sentence):

        lower = sentence.lower()

        categories = {
            "autonomi": [
                "autonom",
                "partita iva",
                "libero professionista",
                "modello unico",
                "redditi d'impresa"
            ],
            "dipendenti": [
                "dipendente",
                "tempo indeterminato",
                "tempo determinato",
                "busta paga"
            ],
            "pensionati": [
                "pensionato",
                "pensione"
            ],
            "redditi_esteri": [
                "redditi esteri",
                "estero",
                "frontalieri",
                "frontaliere"
            ],
            "garanti": [
                "garante",
                "garanzia personale"
            ],
            "coobbligati": [
                "coobbligato",
                "coobbligati",
                "cointestatario",
                "cointestatari"
            ],
            "classe_energetica": [
                "classe energetica",
                "ape",
                "classe a",
                "classe b",
                "green"
            ],
            "polizze": [
                "polizza",
                "incendio",
                "scoppio",
                "cpi",
                "assicurazione"
            ],
            "deroghe": [
                "deroga",
                "eccezione",
                "valutazione caso per caso"
            ],
            "istruttoria": [
                "istruttoria",
                "spese di istruttoria"
            ],
            "perizia": [
                "perizia",
                "perito",
                "valutazione immobile"
            ],
            "durata": [
                "durata massima",
                "durata minima",
                "anni"
            ],
            "ltv": [
                "ltv",
                "loan to value",
                "finanziabile",
                "fino al"
            ],
            "eta": [
                "età",
                "eta",
                "scadenza",
                "anni a scadenza"
            ],
            "finalita": [
                "prima casa",
                "seconda casa",
                "surroga",
                "liquidità",
                "liquidita",
                "consolidamento",
                "ristrutturazione"
            ]
        }

        matches = []

        for category, keywords in categories.items():

            for keyword in keywords:

                if keyword in lower:

                    matches.append(
                        category
                    )

                    break

        return matches

    def analyze_pages(self, pages):

        all_sentences = []

        classified = {}

        unclassified = []

        for page in pages:

            pagina = page.get(
                "pagina"
            )

            raw_text = page.get(
                "raw_text",
                ""
            )

            sentences = self._split_sentences(
                raw_text
            )

            for sentence in sentences:

                categories = self._match_category(
                    sentence
                )

                row = {
                    "pagina": pagina,
                    "sentence": sentence,
                    "categories": categories
                }

                all_sentences.append(
                    row
                )

                if len(categories) == 0:

                    unclassified.append(
                        row
                    )

                else:

                    for category in categories:

                        if category not in classified:

                            classified[category] = []

                        classified[category].append(
                            row
                        )

        return {
            "success": True,
            "totale_frasi": len(all_sentences),
            "totale_classificate": len(all_sentences) - len(unclassified),
            "totale_non_classificate": len(unclassified),
            "classified": classified,
            "unclassified": unclassified,
            "all_sentences": all_sentences
        }