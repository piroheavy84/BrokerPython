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

            "perizia_euro": 0.0,

            "imposta_sostitutiva_percentuale": 0.25,
            "costi_avviamento_percentuale": 0.25,
            "istruttoria_percentuale": None,
            "istruttoria_minimo": 0.0,
            "istruttoria_massimo": 0.0,

            "tasso_esplicito": False,

            # Parametri manuali specifici della banca.
            # Vengono richiesti ad ogni nuovo caricamento/sostituzione PDF.
            "calcolo_debito": None,

            "rapporto_rata_reddito_percentuale": None,

            "eta_massima_finanziabile": None,

            "anni_residenza_italia_straniero": None,

            # Tabella sussistenza normalizzata per area e componenti.
            # La banca non è completa finché non viene configurata.
            "sussistenza": {
                "configurata": False,
                "stato": "MANCANTE",
                "fonte": None,
                "file_nome": None,
                "file_path": None,
                "tipo_geografia": "AREA",
                "soglie": {"nord": {}, "centro": {}, "sud": {}},
                "incremento_oltre_5": {"nord": 0.0, "centro": 0.0, "sud": 0.0}
            },

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