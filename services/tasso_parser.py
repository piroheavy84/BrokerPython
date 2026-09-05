class TassoParser:

    def parse(self, testo):

        upper = str(testo or "").upper()

        risultato = {
            "tipo": "",
            "descrizione": str(testo or ""),
        }

        if "ENASARCO" in upper and ("FISSO" in upper or "TF" in upper):
            risultato["tipo"] = "FISSO ENASARCO"

        elif "ENASARCO" in upper and ("VARIABILE" in upper or "TV" in upper):
            risultato["tipo"] = "VARIABILE ENASARCO"

        elif "VARIABILE CON FLOOR" in upper:
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

        return risultato
