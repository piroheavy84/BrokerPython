class BankMemoryAIService:

    def compare_memory(
        self,
        memory,
        detected
    ):

        changes = []

        fields = [
            "eta_massima",
            "ltv_massimo",
            "prima_casa",
            "seconda_casa",
            "surroga",
            "liquidita",
            "consolidamento",
            "green"
        ]

        for field in fields:

            old_value = memory.get(
                field
            )

            new_value = detected.get(
                field
            )

            if new_value is None:
                continue

            if old_value is None:
                continue

            if old_value != new_value:

                changes.append(
                    {
                        "field": field,
                        "old": old_value,
                        "new": new_value
                    }
                )

        return changes

    def find_new_phrases(
        self,
        memory,
        detected
    ):

        known = set(
            memory.get(
                "frasi_confermate",
                []
            )
        )

        new_phrases = []

        for phrase in detected.get(
            "phrases",
            []
        ):

            if phrase not in known:

                new_phrases.append(
                    phrase
                )

        return new_phrases