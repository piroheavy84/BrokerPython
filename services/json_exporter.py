import json
from dataclasses import asdict


class JsonExporter:

    @staticmethod
    def esporta(lista_prodotti, file_output):

        dati = []

        for p in lista_prodotti:

            dati.append(asdict(p))

        with open(

            file_output,

            "w",

            encoding="utf8"

        ) as f:

            json.dump(

                dati,

                f,

                indent=4,

                ensure_ascii=False

            )

        return len(dati)