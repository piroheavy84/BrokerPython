class Mortgage:

    def __init__(
        self,
        importo,
        durata,
        finalita,
        tasso,
        data_rogito=None
    ):

        self.importo = importo
        self.durata = durata
        self.finalita = finalita
        self.tasso = tasso
        self.data_rogito = data_rogito
