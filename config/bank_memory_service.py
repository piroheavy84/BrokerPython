import json
import os


class BankMemoryService:

    MEMORY_DIR = "memory"

    def __init__(self):

        os.makedirs(
            self.MEMORY_DIR,
            exist_ok=True
        )

    def _default_memory(self):

        return {

            "eta_massima": None,

            "ltv_massimo": None,

            "prima_casa": False,

            "seconda_casa": False,

            "surroga": False,

            "liquidita": False,

            "consolidamento": False,

            "green": False,

            "autonomi": [],

            "redditi_esteri": [],

            "garanti": [],

            "polizze": [],

            "deroghe": [],

            "classe_energetica": [],

            "frasi_confermate": []
        }

    def _path(
        self,
        banca
    ):

        nome = banca.lower().replace(
            " ",
            "_"
        )

        return os.path.join(
            self.MEMORY_DIR,
            f"{nome}.json"
        )

    def load_bank_memory(
        self,
        banca
    ):

        path = self._path(
            banca
        )

        if not os.path.exists(
            path
        ):

            memory = self._default_memory()

            self.save_bank_memory(
                banca,
                memory
            )

            return memory

        with open(
            path,
            "r",
            encoding="utf-8"
        ) as f:

            memory = json.load(
                f
            )

        default = self._default_memory()

        for key, value in default.items():

            if key not in memory:

                memory[key] = value

        return memory

    def save_bank_memory(
        self,
        banca,
        memory
    ):

        with open(
            self._path(
                banca
            ),
            "w",
            encoding="utf-8"
        ) as f:

            json.dump(
                memory,
                f,
                indent=4,
                ensure_ascii=False
            )