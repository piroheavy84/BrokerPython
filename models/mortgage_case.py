class MortgageCase:

    def __init__(

        self,

        nome,

        eta,

        reddito,

        importo_mutuo,

        valore_immobile,

        finalita,

        tasso,

        durata,

        regione="",

        provincia="",

        prima_casa=True,

        consap=False,

        under36=False

    ):

        self.nome = nome

        self.eta = eta

        self.reddito = reddito

        self.importo_mutuo = importo_mutuo

        self.valore_immobile = valore_immobile

        self.finalita = finalita

        self.tasso = tasso

        self.durata = durata

        self.regione = regione

        self.provincia = provincia

        self.prima_casa = prima_casa

        self.consap = consap

        self.under36 = under36

        self.filters = SearchFilters()

        # ----------------------

        if valore_immobile > 0:

            self.ltv = (

                importo_mutuo /

                valore_immobile

            ) * 100

        else:

            self.ltv = 0