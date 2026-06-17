import re


class HeaderParser:

    def parse(self, header):

        result = {

            "tipo_listino": "",

            "canalizzazione_da": "",

            "canalizzazione_a": "",

            "stipula_entro": ""

        }

        testo = " ".join(header)

        upper = testo.upper()

        if "LISTINO IN CORSO" in upper:

            result["tipo_listino"] = "IN CORSO"

        elif "PRATICHE IN MAGAZZINO" in upper:

            result["tipo_listino"] = "MAGAZZINO"

        date = re.findall(r"\d{2}/\d{2}/\d{2,4}", testo)

        if len(date) >= 3:

            result["canalizzazione_da"] = date[0]

            result["canalizzazione_a"] = date[1]

            result["stipula_entro"] = date[2]

        return result