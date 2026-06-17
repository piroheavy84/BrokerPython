class TassoParser:

    def parse(self, testo):

        upper = testo.upper()

        risultato = {

            "tipo": "",

            "descrizione": ""

        }

        if "VARIABILE CON FLOOR" in upper:

            risultato["tipo"] = "VARIABILE CON FLOOR"

        elif "VARIABILE CON CAP" in upper:

            risultato["tipo"] = "VARIABILE CON CAP"

        elif "RATA PROTETTA" in upper:

            risultato["tipo"] = "RATA PROTETTA"

        elif "FISSO" in upper:

            risultato["tipo"] = "FISSO"

        elif "VARIABILE" in upper:

            risultato["tipo"] = "VARIABILE"

        else:

            risultato["tipo"] = upper

        risultato["descrizione"] = testo

        return risultato