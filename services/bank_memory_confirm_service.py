from config.bank_memory_service import BankMemoryService


class BankMemoryConfirmService:

    def __init__(self):

        self.memory_service = BankMemoryService()

    def confirm_phrases(
        self,
        banca,
        phrases
    ):

        memory = self.memory_service.load_bank_memory(
            banca
        )

        current = memory.get(
            "frasi_confermate",
            []
        )

        for phrase in phrases:

            if phrase not in current:

                current.append(
                    phrase
                )

        memory["frasi_confermate"] = current

        self.memory_service.save_bank_memory(
            banca,
            memory
        )

        return {
            "success": True,
            "count": len(current),
            "memory": memory
        }

    def confirm_fields(
        self,
        banca,
        fields
    ):

        memory = self.memory_service.load_bank_memory(
            banca
        )

        for key, value in fields.items():

            memory[key] = value

        self.memory_service.save_bank_memory(
            banca,
            memory
        )

        return {
            "success": True,
            "memory": memory
        }

    def confirm_category(
        self,
        banca,
        category,
        phrases
    ):

        memory = self.memory_service.load_bank_memory(
            banca
        )

        if category not in memory:

            memory[category] = []

        rows = memory.get(
            category,
            []
        )

        for phrase in phrases:

            if phrase not in rows:

                rows.append(
                    phrase
                )

        memory[category] = rows

        self.memory_service.save_bank_memory(
            banca,
            memory
        )

        return {
            "success": True,
            "category": category,
            "count": len(rows),
            "memory": memory
        }

    def add_autonomi(
        self,
        banca,
        phrase
    ):

        return self._append_category(
            banca,
            "autonomi",
            phrase
        )

    def add_redditi_esteri(
        self,
        banca,
        phrase
    ):

        return self._append_category(
            banca,
            "redditi_esteri",
            phrase
        )

    def add_garanti(
        self,
        banca,
        phrase
    ):

        return self._append_category(
            banca,
            "garanti",
            phrase
        )

    def add_polizze(
        self,
        banca,
        phrase
    ):

        return self._append_category(
            banca,
            "polizze",
            phrase
        )

    def add_deroghe(
        self,
        banca,
        phrase
    ):

        return self._append_category(
            banca,
            "deroghe",
            phrase
        )

    def add_classe_energetica(
        self,
        banca,
        phrase
    ):

        return self._append_category(
            banca,
            "classe_energetica",
            phrase
        )

    def _append_category(
        self,
        banca,
        category,
        phrase
    ):

        memory = self.memory_service.load_bank_memory(
            banca
        )

        rows = memory.get(
            category,
            []
        )

        if phrase not in rows:

            rows.append(
                phrase
            )

        memory[category] = rows

        self.memory_service.save_bank_memory(
            banca,
            memory
        )

        return {
            "success": True,
            "category": category,
            "memory": memory
        }