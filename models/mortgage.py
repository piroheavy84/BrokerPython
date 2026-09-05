class Mortgage:

    def __init__(
        self,
        importo,
        durata,
        finalita,
        tasso,
        data_rogito=None,
        valore_perizia=None,
        classe_energetica="",
        reddito_mensile=0,
    ):

        self.importo = importo
        self.durata = durata
        self.finalita = finalita
        self.tasso = tasso
        self.data_rogito = data_rogito
        self.valore_perizia = valore_perizia
        self.classe_energetica = classe_energetica or ""
        self.reddito_mensile = reddito_mensile or 0
