class BrokerResponse:

    def __init__(

        self,

        richiesta,

        risultati

    ):

        self.richiesta = richiesta

        self.risultati = risultati

        self.numero_prodotti = len(

            risultati

        )

        if len(risultati):

            self.migliore = risultati[0]

        else:

            self.migliore = None