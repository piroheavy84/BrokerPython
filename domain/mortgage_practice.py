class MortgagePractice:

    def __init__(

        self,

        customer,

        property,

        mortgage

    ):

        self.customer = customer

        self.property = property

        self.mortgage = mortgage

    # ----------------------------------
    # Compatibilità BrokerEngine
    # ----------------------------------

    @property
    def finalita(self):

        return self.mortgage.finalita

    @property
    def tasso(self):

        return self.mortgage.tasso

    @property
    def durata(self):

        return self.mortgage.durata

    @property
    def importo(self):

        return self.mortgage.importo

    @property
    def valore(self):

        return self.property.valore

    @property
    def ltv(self):

        if self.property.valore == 0:

            return 0

        return (

            self.mortgage.importo

            /

            self.property.valore

        ) * 100

    # ----------------------------------

    def to_dict(self):

        return {

            "cliente": {

                "nome": self.customer.nome,

                "cognome": self.customer.cognome,

                "eta": self.customer.eta,

                "reddito": self.customer.reddito

            },

            "immobile": {

                "valore": self.property.valore,

                "regione": self.property.regione,

                "provincia": self.property.provincia

            },

            "mutuo": {

                "importo": self.mortgage.importo,

                "durata": self.mortgage.durata,

                "finalita": self.mortgage.finalita,

                "tasso": self.mortgage.tasso

            },

            "ltv": self.ltv

        }