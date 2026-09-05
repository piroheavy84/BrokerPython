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
    # Compatibilita BrokerEngine / RuleEngine
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
    def data_rogito(self):
        return getattr(
            self.mortgage,
            "data_rogito",
            None
        )

    @property
    def valore_perizia(self):
        return getattr(
            self.mortgage,
            "valore_perizia",
            None
        )

    @property
    def classe_energetica(self):
        return getattr(
            self.mortgage,
            "classe_energetica",
            ""
        )

    @property
    def reddito_mensile(self):
        # Il reddito arriva sia sul Customer sia, per comodità, sul Mortgage.
        # Preferisco Customer perché rappresenta la pratica aggregata.
        return getattr(
            self.customer,
            "reddito",
            getattr(self.mortgage, "reddito_mensile", 0)
        )

    @property
    def reddito(self):
        return self.reddito_mensile

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
                "valore_perizia": self.valore_perizia,
                "classe_energetica": self.classe_energetica,
                "regione": self.property.regione,
                "provincia": self.property.provincia
            },
            "mutuo": {
                "importo": self.mortgage.importo,
                "durata": self.mortgage.durata,
                "finalita": self.mortgage.finalita,
                "tasso": self.mortgage.tasso,
                "data_rogito": self.data_rogito,
                "valore_perizia": self.valore_perizia,
                "classe_energetica": self.classe_energetica,
                "reddito_mensile": self.reddito_mensile
            },
            "ltv": self.ltv
        }
